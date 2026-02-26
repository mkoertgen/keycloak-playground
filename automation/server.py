#!/usr/bin/env python3
"""
FastAPI webhook server for GitLab events.

Automatically handles user lifecycle events from GitLab.
Includes scheduled group synchronization from Keycloak to GitLab.
"""

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from clients import GitLabClient, KeycloakClient
from config import Settings
from fastapi import FastAPI, Header, HTTPException, Request
from group_sync import GroupSync
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

# Initialize clients
kc = KeycloakClient(
    settings.keycloak_url,
    settings.keycloak_admin_user,
    settings.keycloak_admin_password,
    settings.keycloak_realm,
)
gl = GitLabClient(settings.gitlab_url, settings.gitlab_admin_token)

# Initialize group sync
group_sync = GroupSync(kc, gl)

# Scheduler for background tasks
scheduler = AsyncIOScheduler()


def sync_groups_job():
    """Background job for group synchronization."""
    try:
        logger.info("Running scheduled group sync...")
        result = group_sync.sync_all_groups()
        logger.info(f"Group sync completed: {result}")
    except Exception as e:
        logger.error(f"Group sync failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Startup
    logger.info("Starting automation server...")

    if settings.group_sync_enabled:
        # Parse cron expression
        cron_parts = settings.group_sync_cron.split()
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron expression: {settings.group_sync_cron}")
        else:
            minute, hour, day, month, day_of_week = cron_parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
            )

            scheduler.add_job(
                sync_groups_job,
                trigger=trigger,
                id="group_sync",
                name="Keycloak → GitLab Group Sync",
                replace_existing=True,
            )

            logger.info(f"Scheduled group sync with cron: {settings.group_sync_cron}")

        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Group sync disabled")

    yield

    # Shutdown
    logger.info("Shutting down automation server...")
    if settings.group_sync_enabled:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title="Keycloak-GitLab Automation Webhook Server",
    description="Handles GitLab webhooks for automated user lifecycle management",
    version="0.1.0",
    lifespan=lifespan,
)


class GitLabUserEvent(BaseModel):
    """GitLab User event payload (simplified)."""

    event_name: str
    created_at: str
    username: str
    user_id: int
    email: str | None = None


def verify_gitlab_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify GitLab webhook signature."""
    if not signature:
        return False

    expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "keycloak-gitlab-automation",
        "status": "healthy",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    # Check Keycloak connection
    kc_healthy = False
    try:
        kc.admin.get_server_info()
        kc_healthy = True
    except Exception as e:
        logger.error(f"Keycloak unhealthy: {e}")

    # Check GitLab connection
    gl_healthy = False
    try:
        gl.client.version()
        gl_healthy = True
    except Exception as e:
        logger.error(f"GitLab unhealthy: {e}")

    # Scheduler status
    scheduler_status = "enabled" if settings.group_sync_enabled else "disabled"
    next_run = None
    if settings.group_sync_enabled and scheduler.running:
        job = scheduler.get_job("group_sync")
        if job:
            next_run = job.next_run_time.isoformat() if job.next_run_time else None

    return {
        "keycloak": "healthy" if kc_healthy else "unhealthy",
        "gitlab": "healthy" if gl_healthy else "unhealthy",
        "scheduler": {
            "status": scheduler_status,
            "running": scheduler.running if settings.group_sync_enabled else False,
            "cron": settings.group_sync_cron if settings.group_sync_enabled else None,
            "next_run": next_run,
        },
        "overall": "healthy" if (kc_healthy and gl_healthy) else "degraded",
    }


@app.post("/api/sync-groups")
async def trigger_group_sync():
    """Manually trigger group synchronization."""
    if not settings.group_sync_enabled:
        raise HTTPException(status_code=400, detail="Group sync is disabled")

    try:
        logger.info("Manual group sync triggered via API")
        result = group_sync.sync_all_groups()
        return {
            "status": "success",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Manual group sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync-status")
async def get_sync_status():
    """Get current sync status and configuration."""
    if not settings.group_sync_enabled:
        return {
            "enabled": False,
            "message": "Group sync is disabled",
        }

    job = scheduler.get_job("group_sync")
    if not job:
        return {
            "enabled": True,
            "running": False,
            "message": "Scheduler job not found",
        }

    return {
        "enabled": True,
        "running": scheduler.running,
        "cron": settings.group_sync_cron,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        "managed_groups": group_sync.managed_groups,
    }


@app.post("/webhook/gitlab/user")
async def handle_gitlab_user_event(
    request: Request,
    x_gitlab_token: str | None = Header(None),
):
    """Handle GitLab user system hooks.

    Supported events:
    - user_destroy: User deleted (offboard user)
    - user_block: User blocked (offboard user)
    - user_failed_login: Failed login attempts (future: could trigger alerts)

    To configure in GitLab:
    1. Admin Area > System Hooks
    2. URL: http://your-server:8000/webhook/gitlab/user
    3. Secret Token: (same as GITLAB_WEBHOOK_SECRET)
    4. Enable "User events"
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if secret is configured
    if settings.gitlab_webhook_secret:
        if not verify_gitlab_signature(
            body, x_gitlab_token, settings.gitlab_webhook_secret
        ):
            logger.warning("Invalid GitLab webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_name = payload.get("event_name")
    username = payload.get("username")

    logger.info(f"Received GitLab event: {event_name} for user: {username}")

    # Handle user destroy/block events (offboarding)
    if event_name in ["user_destroy", "user_block"]:
        return await offboard_user_handler(username, event_name)

    # Handle user create events (onboarding)
    if event_name == "user_create":
        return await onboard_user_handler(username, payload.get("email"), event_name)

    # Log other events but don't process
    logger.info(f"Event '{event_name}' not configured for automatic processing")
    return {
        "status": "received",
        "message": f"Event '{event_name}' logged but not processed",
    }


async def onboard_user_handler(
    username: str, email: str | None, event_type: str
) -> dict[str, Any]:
    """Handle user onboarding - set required actions for new users.

    Integrates with Keycloak Workflows (UserCreatedWorkflowEvent) to automate
    user onboarding by setting required actions like password setup and 2FA.
    """
    logger.info(
        f"Starting onboarding process for user: {username} (trigger: {event_type})"
    )

    try:
        # Get Keycloak user
        kc_user = kc.get_user_by_username(username)
        if not kc_user:
            logger.warning(f"User '{username}' not found in Keycloak")
            return {
                "status": "warning",
                "message": f"User '{username}' not found in Keycloak",
                "action": "none",
            }

        user_id = kc_user["id"]
        actions_taken = []

        # Get current required actions
        current_actions = kc_user.get("requiredActions", [])
        logger.info(f"User '{username}' current required actions: {current_actions}")

        # Define default onboarding required actions
        # These align with Keycloak Workflows AddRequiredActionStepProvider
        default_actions = ["UPDATE_PASSWORD", "CONFIGURE_TOTP"]

        # Only add actions that aren't already set
        new_actions = list(set(current_actions + default_actions))

        if new_actions != current_actions:
            kc.admin.update_user(user_id, {"requiredActions": new_actions})
            actions_taken.append("set_required_actions")
            logger.info(f"Set required actions for user '{username}': {new_actions}")
        else:
            logger.info(f"User '{username}' already has required actions set")

        # Optionally: Send welcome email (if email verification not already required)
        if email and "VERIFY_EMAIL" not in new_actions:
            # Could trigger email here or rely on Keycloak's email settings
            logger.info(f"Welcome email would be sent to: {email}")
            actions_taken.append("welcome_email_queued")

        logger.info(f"Successfully onboarded user: {username}")
        return {
            "status": "success",
            "message": f"User '{username}' onboarded",
            "actions": actions_taken,
            "required_actions": new_actions,
            "trigger": event_type,
        }

    except Exception as e:
        logger.error(f"Error onboarding user '{username}': {e}")
        return {"status": "error", "message": str(e), "user": username}


async def offboard_user_handler(username: str, event_type: str) -> dict[str, Any]:
    """Handle user offboarding from GitLab events."""
    logger.info(
        f"Starting offboarding process for user: {username} (trigger: {event_type})"
    )

    try:
        # Get Keycloak user
        kc_user = kc.get_user_by_username(username)
        if not kc_user:
            logger.warning(f"User '{username}' not found in Keycloak")
            return {
                "status": "warning",
                "message": f"User '{username}' not found in Keycloak",
                "action": "none",
            }

        user_id = kc_user["id"]
        actions_taken = []

        # Disable user in Keycloak
        if kc_user.get("enabled"):
            if kc.disable_user(user_id):
                actions_taken.append("disabled_in_keycloak")
                logger.info(f"Disabled user '{username}' in Keycloak")
            else:
                logger.error(f"Failed to disable user '{username}' in Keycloak")
                return {
                    "status": "error",
                    "message": "Failed to disable user in Keycloak",
                    "user": username,
                }
        else:
            logger.info(f"User '{username}' already disabled in Keycloak")

        # Revoke all Keycloak sessions
        kc.revoke_user_sessions(user_id)
        actions_taken.append("revoked_keycloak_sessions")

        logger.info(f"Successfully offboarded user: {username}")
        return {
            "status": "success",
            "message": f"User '{username}' offboarded",
            "actions": actions_taken,
            "trigger": event_type,
        }

    except Exception as e:
        logger.error(f"Error offboarding user '{username}': {e}")
        return {"status": "error", "message": str(e), "user": username}


@app.post("/webhook/gitlab/test")
async def test_webhook(request: Request):
    """Test webhook endpoint (no signature verification)."""
    payload = await request.json()
    logger.info(f"Test webhook received: {payload}")
    return {"status": "ok", "received": payload}


@app.post("/webhook/keycloak/user-created")
async def handle_keycloak_user_created(
    request: Request,
    authorization: str | None = Header(None),
):
    """Handle Keycloak UserCreatedWorkflowEvent webhook.

    This endpoint integrates with Keycloak Workflows to automatically onboard
    new users when they are created (via admin API or self-registration).

    Expected payload:
    {
        "eventType": "USER_CREATED",
        "realmId": "factory",
        "userId": "user-uuid",
        "username": "john.doe",
        "email": "john.doe@example.com"
    }

    To configure in Keycloak Workflow:
    1. Create Workflow with UserCreatedWorkflowEvent trigger
    2. Add HTTP Step to call this webhook
    3. URL: http://your-server:8000/webhook/keycloak/user-created
    4. Authorization: Bearer <token> (optional)
    """
    # Verify authorization if configured
    if settings.gitlab_webhook_secret:  # Reuse same secret for simplicity
        expected_auth = f"Bearer {settings.gitlab_webhook_secret}"
        if authorization != expected_auth:
            logger.warning("Invalid authorization header")
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("eventType")
    username = payload.get("username")
    email = payload.get("email")

    logger.info(f"Received Keycloak event: {event_type} for user: {username}")

    if event_type == "USER_CREATED":
        return await onboard_user_handler(username, email, event_type)

    logger.info(f"Event '{event_type}' not configured for automatic processing")
    return {
        "status": "received",
        "message": f"Event '{event_type}' logged but not processed",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info",
    )
