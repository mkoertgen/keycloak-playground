#!/usr/bin/env python3
"""
OIDC Test Client for Keycloak (FastAPI)

Demonstrates OpenID Connect authentication flow with Keycloak,
including OIDC Back-Channel Logout support and Admin API.

Interactive API docs: http://localhost:3000/docs
"""

import secrets
from datetime import datetime
from typing import Dict
import json
import base64

from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt
from fastapi import FastAPI, Form, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.sessions import SessionMiddleware


# Configuration
class Settings(BaseSettings):
    """Application settings with dotenv support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OIDC Configuration
    oidc_client_id: str = Field(default="demo-app", alias="OIDC_CLIENT_ID")
    oidc_client_secret: str = Field(default="", alias="OIDC_CLIENT_SECRET")
    oidc_issuer: str = Field(
        default="http://localhost:8080/realms/demo", alias="OIDC_ISSUER"
    )
    oidc_redirect_uri: str = Field(
        default="http://localhost:3000/callback", alias="OIDC_REDIRECT_URI"
    )

    # Security
    app_secret_key: str = Field(
        default_factory=lambda: secrets.token_hex(32), alias="APP_SECRET_KEY"
    )
    admin_api_token: str = Field(default="dev-admin-secret", alias="ADMIN_API_TOKEN")


settings = Settings()

# FastAPI app
app = FastAPI(
    title="Keycloak Test Client",
    description="""
    OIDC demo client demonstrating:
    - Authorization Code Flow with PKCE
    - **OIDC Back-Channel Logout** (what GitLab is missing)
    - **Admin API** for manual session termination
    - Session tracking and management
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)

# Templates
templates = Jinja2Templates(directory="templates")

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# OAuth/OIDC setup
oauth = OAuth()
oauth.register(
    name="keycloak",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "code_challenge_method": "S256",  # Enable PKCE (required by Keycloak client config)
    },
)

# In-memory session store for backchannel logout
# Maps session_id -> {"sub": "user-id", "sid": "session-id", "created_at": timestamp}
# Production: use Redis/database to share across instances
active_sessions: Dict[str, dict] = {}


# ===== Helper Functions =====


def decode_jwt_unverified(token: str) -> dict:
    """Decode JWT without signature verification (for demo purposes only)"""
    try:
        # Split JWT into parts
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)  # Add padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return {}


# ===== Pydantic Models =====


class UserInfo(BaseModel):
    """User information"""

    sub: str
    email: str | None = None
    name: str | None = None
    email_verified: bool = False


class SessionInfo(BaseModel):
    """Active session information"""

    sub: str
    sid: str | None = None
    created_at: str


class SessionsResponse(BaseModel):
    """List of active sessions"""

    total: int
    sessions: Dict[str, SessionInfo]


class AdminLogoutResponse(BaseModel):
    """Admin logout response"""

    success: bool
    username: str | None = None
    sub: str | None = None
    sessions_terminated: int


class HealthResponse(BaseModel):
    """Health check response"""

    status: str


# ===== HTML Endpoints =====


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Home page - shows login status"""
    user = request.session.get("user")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/login", include_in_schema=False)
async def login(request: Request):
    """Initiate OIDC login flow"""
    # Use configured redirect_uri to match Keycloak client registration
    return await oauth.keycloak.authorize_redirect(request, settings.oidc_redirect_uri)


@app.get("/callback", include_in_schema=False)
async def callback(request: Request):
    """OIDC callback endpoint"""
    try:
        token = await oauth.keycloak.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            raise ValueError("No userinfo in token response")

        # Decode ID token to extract session ID (sid)
        id_token = token.get("id_token")
        if not id_token:
            raise ValueError("No id_token in response")
            
        # Decode without signature verification (for demo only)
        # In production: fetch JWKS and verify signature properly
        id_token_claims = decode_jwt_unverified(id_token)

        session_id = request.session.get("session_id") or secrets.token_hex(16)
        request.session["session_id"] = session_id
        request.session["user"] = {
            "sub": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name", user_info.get("preferred_username")),
            "email_verified": user_info.get("email_verified", False),
        }
        request.session["token"] = {
            "access_token": token.get("access_token"),
            "id_token": id_token,
            "token_type": token.get("token_type"),
            "expires_in": token.get("expires_in"),
        }

        # Register session for backchannel logout
        sid = id_token_claims.get("sid")
        active_sessions[session_id] = {
            "sub": user_info.get("sub"),
            "sid": sid,
            "created_at": datetime.utcnow().isoformat(),
        }

        print(
            f"[SESSION] Created: {session_id} for user {user_info.get('sub')} (sid: {sid})"
        )

    except Exception as e:
        print(f"Error during callback: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": str(e)}, status_code=400
        )

    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/logout", include_in_schema=False)
async def logout(request: Request):
    """Logout - clear session (frontchannel)"""
    session_id = request.session.get("session_id")
    if session_id and session_id in active_sessions:
        del active_sessions[session_id]
        print(f"[SESSION] Removed (frontchannel logout): {session_id}")

    request.session.clear()
    # Redirect to Keycloak logout endpoint (frontchannel logout)
    keycloak_logout = f"{settings.oidc_issuer}/protocol/openid-connect/logout"
    return RedirectResponse(url=keycloak_logout, status_code=status.HTTP_302_FOUND)


@app.get("/profile", response_class=HTMLResponse, include_in_schema=False)
async def profile(request: Request):
    """Show user profile (requires authentication)"""
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    token = request.session.get("token")
    return templates.TemplateResponse(
        "profile.html", {"request": request, "user": user, "token": token}
    )


# ===== OIDC Back-Channel Logout =====


@app.post(
    "/backchannel-logout",
    status_code=200,
    tags=["OIDC"],
    summary="OIDC Back-Channel Logout Endpoint",
    description="""
    Keycloak sends a logout_token (JWT) when user logs out.
    
    **OIDC Spec Requirements:**
    - Must contain 'sid' (session ID) or 'sub' (user ID)
    - Must NOT contain 'nonce'
    - Signature verification is skipped in demo (use JWKS in production)
    
    This demonstrates what GitLab is missing ([gitlab#449119](https://gitlab.com/gitlab-org/gitlab/-/issues/449119)).
    """,
)
async def backchannel_logout(logout_token: str = Form(...)):
    """Process OIDC backchannel logout token from Keycloak"""
    try:
        # Decode without signature verification (for demo only)
        # Production: verify signature with Keycloak's JWKS
        claims = decode_jwt_unverified(logout_token)

        # Validate logout token (OIDC Back-Channel Logout spec)
        if "nonce" in claims:
            print("[BACKCHANNEL] Invalid: logout_token must not contain nonce")
            raise HTTPException(status_code=400, detail="Invalid logout_token")

        if (
            "events" not in claims
            or "http://schemas.openid.net/event/backchannel-logout"
            not in claims["events"]
        ):
            print("[BACKCHANNEL] Invalid: missing backchannel-logout event")
            raise HTTPException(status_code=400, detail="Invalid logout_token")

        # Find and invalidate matching sessions
        sid = claims.get("sid")  # Keycloak session ID
        sub = claims.get("sub")  # User ID

        removed_sessions = []
        for session_id, session_data in list(active_sessions.items()):
            # Match by session ID (sid) or user ID (sub)
            if (sid and session_data.get("sid") == sid) or (
                sub and session_data.get("sub") == sub
            ):
                del active_sessions[session_id]
                removed_sessions.append(session_id)

        print(f"[BACKCHANNEL] Logout received - sid: {sid}, sub: {sub}")
        print(
            f"[BACKCHANNEL] Removed {len(removed_sessions)} sessions: {removed_sessions}"
        )

        return {}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[BACKCHANNEL] Error processing logout: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ===== API Endpoints =====


@app.get("/api/userinfo", tags=["API"], summary="Get current user information")
async def api_userinfo(request: Request) -> Dict:
    """Get authenticated user information"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {"authenticated": True, "user": user}


@app.get(
    "/api/sessions",
    response_model=SessionsResponse,
    tags=["API"],
    summary="List active sessions (debug)",
)
async def api_sessions() -> SessionsResponse:
    """Debug endpoint: List all active sessions"""
    sessions = {sid: SessionInfo(**data) for sid, data in active_sessions.items()}
    return SessionsResponse(total=len(sessions), sessions=sessions)


# ===== Admin API =====


def verify_admin_token(authorization: str | None = Header(None)):
    """Verify admin API token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "")
    if token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@app.post(
    "/admin/logout/{username}",
    response_model=AdminLogoutResponse,
    tags=["Admin API"],
    summary="Force logout user by username",
    description="""
    Similar to GitLab's admin API (POST /users/:id/logout).
    
    This demonstrates manual session termination when backchannel logout
    is not available (like in GitLab).
    
    **Authorization:** Bearer token required in header.
    """,
)
async def admin_logout(
    username: str, authorization: str | None = Header(None)
) -> AdminLogoutResponse:
    """Force logout a user by username (simplified demo version)"""
    verify_admin_token(authorization)

    # Simplified: remove all sessions (in real app, lookup user by username)
    removed_count = len(active_sessions)
    active_sessions.clear()

    print(
        f"[ADMIN] Force logout for user '{username}' - removed {removed_count} sessions"
    )

    return AdminLogoutResponse(
        success=True, username=username, sessions_terminated=removed_count
    )


@app.post(
    "/admin/logout/sub/{sub}",
    response_model=AdminLogoutResponse,
    tags=["Admin API"],
    summary="Force logout user by subject ID",
    description="""
    More precise than username-based logout since 'sub' is stored in sessions.
    
    **Authorization:** Bearer token required in header.
    """,
)
async def admin_logout_by_sub(
    sub: str, authorization: str | None = Header(None)
) -> AdminLogoutResponse:
    """Force logout a user by subject ID (sub)"""
    verify_admin_token(authorization)

    # Find and remove sessions by subject ID
    removed_sessions = []
    for session_id, session_data in list(active_sessions.items()):
        if session_data.get("sub") == sub:
            del active_sessions[session_id]
            removed_sessions.append(session_id)

    print(
        f"[ADMIN] Force logout for sub '{sub}' - removed {len(removed_sessions)} sessions"
    )

    return AdminLogoutResponse(
        success=True, sub=sub, sessions_terminated=len(removed_sessions)
    )


# ===== Health Check =====


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(status="ok")


if __name__ == "__main__":
    print("OIDC Configuration:")
    print(f"  Issuer: {settings.oidc_issuer}")
    print(f"  Client: {settings.oidc_client_id}")
    print(f"  Redirect: {settings.oidc_redirect_uri}")
    print("\nBack-Channel Logout:")
    print("  Endpoint: http://localhost:3000/backchannel-logout")
    print("  Note: Configure in Keycloak client settings")
    print("\nAdmin API:")
    print("  POST /admin/logout/<username>")
    print("  POST /admin/logout/sub/<sub>")
    print(f"  Authorization: Bearer {settings.admin_api_token}")
    print("\nInteractive API docs:")
    print("  Swagger UI: http://localhost:3000/docs")
    print("  ReDoc: http://localhost:3000/redoc")
    print("\nRun with: uv run fastapi dev app.py --port 3000")
