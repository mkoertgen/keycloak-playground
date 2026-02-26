#!/usr/bin/env python3
"""
CLI tool for Keycloak-GitLab automation operations.

Handles user offboarding and other administrative tasks.
"""

import sys
from pathlib import Path

import click
from clients import GitLabClient, KeycloakClient
from config import Settings
from rich.console import Console
from rich.table import Table

console = Console()

# Check if .env exists
env_file = Path(__file__).parent / ".env"

if not env_file.exists():
    console.print("⚠️  No .env file found", style="yellow")
    if click.confirm("   Create .env interactively?", default=True):
        console.print("\n[bold]Enter credentials:[/bold]\n")

        keycloak_url = click.prompt(
            "Keycloak URL", default="http://localhost:8080"
        )
        keycloak_admin_user = click.prompt("Keycloak Admin User", default="admin")
        keycloak_admin_password = click.prompt(
            "Keycloak Admin Password", hide_input=True
        )
        keycloak_realm = click.prompt("Keycloak Realm", default="demo")

        gitlab_url = click.prompt(
            "GitLab URL", default="http://localhost:8929"
        )
        gitlab_admin_token = click.prompt("GitLab Admin Token", hide_input=True)

        with open(env_file, "w") as f:
            f.write("# Keycloak\n")
            f.write(f"KEYCLOAK_URL={keycloak_url}\n")
            f.write(f"KEYCLOAK_ADMIN_USER={keycloak_admin_user}\n")
            f.write(f"KEYCLOAK_ADMIN_PASSWORD={keycloak_admin_password}\n")
            f.write(f"KEYCLOAK_REALM={keycloak_realm}\n")
            f.write("\n# GitLab\n")
            f.write(f"GITLAB_URL={gitlab_url}\n")
            f.write(f"GITLAB_ADMIN_TOKEN={gitlab_admin_token}\n")
            f.write("\n# GitLab Webhook (optional, for server mode)\n")
            f.write("# GITLAB_WEBHOOK_SECRET=your-webhook-secret\n")

        console.print(f"\n✓ Created {env_file}", style="green")
    else:
        console.print("   Create a .env file with required credentials", style="yellow")
        sys.exit(1)

# Load settings
try:
    settings = Settings()
except Exception as e:
    console.print(f"❌ Configuration error: {e}", style="red")
    sys.exit(1)

# Initialize clients
try:
    kc = KeycloakClient(
        settings.keycloak_url,
        settings.keycloak_admin_user,
        settings.keycloak_admin_password,
        settings.keycloak_realm,
    )
    gl = GitLabClient(settings.gitlab_url, settings.gitlab_admin_token)
except Exception as e:
    console.print(f"❌ Connection failed: {e}", style="red")
    sys.exit(1)


@click.group(context_settings={"show_default": True})
@click.version_option(version="0.1.0")
def cli():
    """Keycloak-GitLab Automation CLI

    Automate user lifecycle operations between Keycloak and GitLab.
    """
    pass


@cli.command()
@click.argument("username")
@click.option(
    "--skip-gitlab", is_flag=True, help="Skip GitLab logout (only disable in Keycloak)"
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.confirmation_option(
    prompt="This will disable the user and terminate all sessions. Continue?"
)
def offboard_user(username: str, skip_gitlab: bool, dry_run: bool):
    """Offboard a user: disable in Keycloak and logout from GitLab.

    This performs the following steps:
    1. Disable user in Keycloak (set enabled=false)
    2. Revoke all Keycloak sessions
    3. Logout user from all GitLab sessions (unless --skip-gitlab)

    Example:
        ./automate.py offboard-user marcel.koertgen
    """
    console.print(f"\n[bold]Offboarding user: {username}[/bold]\n")

    # Get Keycloak user
    kc_user = kc.get_user_by_username(username)
    if not kc_user:
        console.print(f"❌ User '{username}' not found in Keycloak", style="red")
        sys.exit(1)

    user_id = kc_user["id"]
    console.print(f"✓ Found Keycloak user: {username} (ID: {user_id})", style="green")

    # Get GitLab user
    gl_user = None
    if not skip_gitlab:
        gl_user = gl.get_user_by_username(username)
        if gl_user:
            console.print(
                f"✓ Found GitLab user: {username} (ID: {gl_user['id']})", style="green"
            )
        else:
            console.print(f"⚠️  User '{username}' not found in GitLab", style="yellow")

    # Show current state
    table = Table(title="User Information")
    table.add_column("System", style="cyan")
    table.add_column("Status", style="magenta")

    table.add_row("Keycloak", "Enabled" if kc_user.get("enabled") else "Disabled")
    if gl_user:
        table.add_row(
            "GitLab",
            "Active"
            if gl_user.get("state") == "active"
            else gl_user.get("state", "unknown"),
        )

    console.print(table)

    if dry_run:
        console.print(
            "\n[bold yellow]DRY-RUN MODE - No changes will be made[/bold yellow]\n"
        )

    # Step 1: Disable in Keycloak
    if kc_user.get("enabled"):
        if dry_run:
            console.print("  [DRY-RUN] Would disable user in Keycloak", style="yellow")
        else:
            if not kc.disable_user(user_id):
                console.print("❌ Failed to disable user in Keycloak", style="red")
                sys.exit(1)
    else:
        console.print("  ✓ User already disabled in Keycloak", style="dim")

    # Step 2: Revoke Keycloak sessions
    if dry_run:
        console.print("  [DRY-RUN] Would revoke all Keycloak sessions", style="yellow")
    else:
        kc.revoke_user_sessions(user_id)

    # Step 3: Logout from GitLab
    if not skip_gitlab and gl_user:
        if dry_run:
            console.print("  [DRY-RUN] Would logout user from GitLab", style="yellow")
        else:
            if not gl.logout_user(gl_user["id"]):
                console.print("⚠️  Failed to logout user from GitLab", style="yellow")
                console.print(
                    "   User won't be able to login via OIDC anymore, but existing sessions remain",
                    style="dim",
                )

    if dry_run:
        console.print(
            "\n[DRY-RUN] Offboarding completed (no changes made)", style="bold yellow"
        )
    else:
        console.print(
            f"\n✓ User '{username}' offboarded successfully", style="bold green"
        )
        console.print("  • Disabled in Keycloak", style="dim")
        console.print("  • Keycloak sessions revoked", style="dim")
        if not skip_gitlab and gl_user:
            console.print("  • Logged out from GitLab", style="dim")


@cli.command()
@click.argument("usernames", nargs=-1, required=True)
@click.option(
    "--skip-gitlab", is_flag=True, help="Skip GitLab logout (only disable in Keycloak)"
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.confirmation_option(prompt="This will offboard multiple users. Continue?")
def offboard_users(usernames: tuple[str], skip_gitlab: bool, dry_run: bool):
    """Offboard multiple users at once.

    Example:
        ./automate.py offboard-users user1 user2 user3
    """
    console.print(f"\n[bold]Offboarding {len(usernames)} users[/bold]\n")

    if dry_run:
        console.print(
            "[bold yellow]DRY-RUN MODE - No changes will be made[/bold yellow]\n"
        )

    success_count = 0
    error_count = 0

    for username in usernames:
        console.print(f"\n[cyan]Processing: {username}[/cyan]")

        # Get Keycloak user
        kc_user = kc.get_user_by_username(username)
        if not kc_user:
            console.print("  ❌ Not found in Keycloak", style="red")
            error_count += 1
            continue

        user_id = kc_user["id"]

        # Get GitLab user
        gl_user = None
        if not skip_gitlab:
            gl_user = gl.get_user_by_username(username)

        # Disable in Keycloak
        if kc_user.get("enabled"):
            if not dry_run:
                if not kc.disable_user(user_id):
                    error_count += 1
                    continue

        # Revoke sessions
        if not dry_run:
            kc.revoke_user_sessions(user_id)

        # Logout from GitLab
        if not skip_gitlab and gl_user:
            if not dry_run:
                gl.logout_user(gl_user["id"])

        success_count += 1

    # Summary
    console.print("\n[bold]Summary[/bold]")
    console.print(f"  ✓ Success: {success_count}", style="green")
    console.print(f"  ✗ Errors: {error_count}", style="red" if error_count else "dim")


@cli.command()
@click.argument("username")
def check_sessions(username: str):
    """Check active sessions for a user in Keycloak.

    Shows all active sessions and their details.
    """
    console.print(f"\n[bold]Checking sessions for: {username}[/bold]\n")

    # Get Keycloak user
    kc_user = kc.get_user_by_username(username)
    if not kc_user:
        console.print(f"❌ User '{username}' not found in Keycloak", style="red")
        sys.exit(1)

    user_id = kc_user["id"]
    sessions = kc.get_user_sessions(user_id)

    if not sessions:
        console.print("✓ No active sessions", style="green")
        return

    console.print(f"Found {len(sessions)} active session(s):", style="cyan")

    for session in sessions:
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="dim")
        table.add_column("Value")

        table.add_row("Session ID", session.get("id", "N/A"))
        table.add_row("IP Address", session.get("ipAddress", "N/A"))
        table.add_row("Started", session.get("start", "N/A"))
        table.add_row("Last Access", session.get("lastAccess", "N/A"))

        clients = session.get("clients", {})
        if clients:
            table.add_row("Clients", ", ".join(clients.keys()))

        console.print(table)
        console.print()


@cli.command()
@click.argument("username")
@click.option(
    "--actions",
    "-a",
    multiple=True,
    default=["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
    help="Required actions to set (can specify multiple times)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would happen without making changes",
)
def onboard_user(username: str, actions: tuple[str], dry_run: bool):
    """Onboard a new user by setting required actions.

    Sets required actions that force the user to complete onboarding steps
    on their next login (password setup, 2FA enrollment, etc.).

    This integrates with Keycloak Workflows (AddRequiredActionStepProvider)
    to automate user onboarding.

    Common required actions:
    - UPDATE_PASSWORD: Force password change (default)
    - CONFIGURE_TOTP: Force 2FA setup (default)
    - VERIFY_EMAIL: Force email verification
    - UPDATE_PROFILE: Force profile update

    Example:
        ./automate.py onboard-user john.doe
        ./automate.py onboard-user john.doe -a UPDATE_PASSWORD -a VERIFY_EMAIL
    """
    console.print(f"\n[bold]Onboarding user: {username}[/bold]\n")

    # Get Keycloak user
    kc_user = kc.get_user_by_username(username)
    if not kc_user:
        console.print(f"❌ User '{username}' not found in Keycloak", style="red")
        sys.exit(1)

    user_id = kc_user["id"]
    console.print(f"✓ Found user: {username} (ID: {user_id})", style="green")
    console.print(f"  Email: {kc_user.get('email', 'N/A')}", style="dim")
    console.print(f"  Enabled: {kc_user.get('enabled', False)}", style="dim")

    # Show current required actions
    current_actions = kc_user.get("requiredActions", [])
    if current_actions:
        console.print(
            f"  Current required actions: {', '.join(current_actions)}", style="dim"
        )
    else:
        console.print("  No current required actions", style="dim")

    # Merge new actions with existing ones
    new_actions = list(set(current_actions + list(actions)))

    if new_actions == current_actions:
        console.print(
            "\n✓ User already has all specified required actions set", style="green"
        )
        return

    console.print(f"\n[cyan]Required actions to set:[/cyan]")
    for action in actions:
        if action in current_actions:
            console.print(f"  • {action} (already set)", style="dim")
        else:
            console.print(f"  • {action}", style="green")

    if dry_run:
        console.print(
            "\n[DRY-RUN] Onboarding completed (no changes made)", style="bold yellow"
        )
        return

    # Set required actions
    try:
        kc.admin.update_user(user_id, {"requiredActions": new_actions})
        console.print(f"\n✓ Onboarding configured for '{username}'", style="bold green")
        console.print(
            "  User will be prompted to complete these on next login.", style="dim"
        )
    except Exception as e:
        console.print(f"\n❌ Failed to set required actions: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.argument("usernames", nargs=-1, required=True)
@click.option(
    "--actions",
    "-a",
    multiple=True,
    default=["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
    help="Required actions to set (can specify multiple times)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.confirmation_option(prompt="Onboard multiple users with required actions?")
def onboard_users(usernames: tuple[str], actions: tuple[str], dry_run: bool):
    """Onboard multiple users at once.

    Example:
        ./automate.py onboard-users user1 user2 user3
        ./automate.py onboard-users user1 user2 -a UPDATE_PASSWORD -a VERIFY_EMAIL
    """
    console.print(f"\n[bold]Onboarding {len(usernames)} users[/bold]")
    console.print(f"Required actions: {', '.join(actions)}\n", style="dim")

    if dry_run:
        console.print(
            "[bold yellow]DRY-RUN MODE - No changes will be made[/bold yellow]\n"
        )

    success_count = 0
    error_count = 0

    for username in usernames:
        console.print(f"[cyan]Processing: {username}[/cyan]")

        # Get Keycloak user
        kc_user = kc.get_user_by_username(username)
        if not kc_user:
            console.print("  ❌ Not found in Keycloak", style="red")
            error_count += 1
            continue

        user_id = kc_user["id"]
        current_actions = kc_user.get("requiredActions", [])
        new_actions = list(set(current_actions + list(actions)))

        if new_actions == current_actions:
            console.print("  ✓ Already has required actions", style="dim")
            success_count += 1
            continue

        if dry_run:
            console.print(
                f"  [DRY-RUN] Would set: {', '.join(actions)}", style="yellow"
            )
            success_count += 1
        else:
            try:
                kc.admin.update_user(user_id, {"requiredActions": new_actions})
                console.print("  ✓ Onboarding configured", style="green")
                success_count += 1
            except Exception as e:
                console.print(f"  ✗ Failed: {e}", style="red")
                error_count += 1

    # Summary
    console.print("\n[bold]Summary[/bold]")
    console.print(f"  ✓ Success: {success_count}", style="green")
    console.print(f"  ✗ Errors: {error_count}", style="red" if error_count else "dim")


@cli.command()
@click.option(
    "--filter",
    type=click.Choice(["all", "incomplete", "complete"]),
    default="incomplete",
    help="Filter users by onboarding status",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def list_onboarding_status(filter: str, format: str):
    """List users and their onboarding status.

    Shows which users still need to complete onboarding (required actions).
    Useful for tracking post-provisioning user onboarding progress.

    Example:
        ./automate.py list-onboarding-status
        ./automate.py list-onboarding-status --filter all
        ./automate.py list-onboarding-status --format json
    """
    console.print("\n[bold]User Onboarding Status[/bold]\n")

    # Fetch all users from Keycloak
    console.print("📊 Fetching users from Keycloak...", style="dim")
    all_users = kc.admin.get_users()

    # Analyze onboarding status
    users_by_status = {"incomplete": [], "complete": []}

    for user in all_users:
        username = user.get("username", "N/A")
        email = user.get("email", "N/A")
        enabled = user.get("enabled", False)
        required_actions = user.get("requiredActions", [])

        status = "incomplete" if required_actions else "complete"
        users_by_status[status].append(
            {
                "username": username,
                "email": email,
                "enabled": enabled,
                "required_actions": required_actions,
            }
        )

    # Filter users
    if filter == "incomplete":
        filtered_users = users_by_status["incomplete"]
    elif filter == "complete":
        filtered_users = users_by_status["complete"]
    else:  # all
        filtered_users = users_by_status["incomplete"] + users_by_status["complete"]

    # Display results
    if format == "table":
        table = Table(title=f"Users ({filter})")
        table.add_column("Username", style="cyan")
        table.add_column("Email", style="dim")
        table.add_column("Enabled", style="magenta")
        table.add_column("Required Actions", style="yellow")

        for user_data in filtered_users:
            table.add_row(
                user_data["username"],
                user_data["email"],
                "✓" if user_data["enabled"] else "✗",
                ", ".join(user_data["required_actions"])
                if user_data["required_actions"]
                else "—",
            )

        console.print(table)

        # Summary stats
        console.print(f"\n[bold]Summary[/bold]")
        console.print(f"  Total users: {len(all_users)}", style="cyan")
        console.print(
            f"  Onboarding complete: {len(users_by_status['complete'])}", style="green"
        )
        console.print(
            f"  Onboarding incomplete: {len(users_by_status['incomplete'])}",
            style="yellow",
        )

    elif format == "json":
        import json

        output = {
            "total_users": len(all_users),
            "complete": len(users_by_status["complete"]),
            "incomplete": len(users_by_status["incomplete"]),
            "users": filtered_users,
        }
        console.print(json.dumps(output, indent=2))


if __name__ == "__main__":
    cli()
