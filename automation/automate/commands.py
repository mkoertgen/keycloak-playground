"""automate/commands.py — business workflows orchestrating kc + gl."""

import sys

import click
from context import console, gitlab, keycloak, load_usernames


@click.group()
def user():
    """User lifecycle workflows (orchestrating Keycloak + GitLab)."""


# ---------------------------------------------------------------------------
# onboard
# ---------------------------------------------------------------------------

@user.command()
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--actions", "-a", multiple=True, default=["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
              show_default=True, help="Required actions to set (repeatable)")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def onboard(username: str | None, input_file: str | None, actions: tuple[str], dry_run: bool):
    """Onboard users by setting required actions.

    Forces users to complete the specified actions on next login.
    Merges with any already-set actions.

    \b
    Common actions:
    - UPDATE_PASSWORD  Force password change (default)
    - CONFIGURE_TOTP   Force 2FA setup (default)
    - VERIFY_EMAIL     Force email verification
    - UPDATE_PROFILE   Force profile update

    \b
    Examples:
        ./cli.py user onboard --user john.doe
        ./cli.py user onboard --user john.doe -a UPDATE_PASSWORD -a VERIFY_EMAIL
        ./cli.py user onboard --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Onboarding {len(usernames)} user(s)[/bold]")
    console.print(f"Actions: {', '.join(actions)}\n", style="dim")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        kc_user = kc.get_user_by_username(uname)
        if not kc_user:
            console.print(f"  ❌ {uname}: not found", style="red")
            err += 1
            continue

        current = kc_user.get("requiredActions", [])
        merged  = list(set(current + list(actions)))

        if merged == current:
            console.print(f"  ✓ {uname}: already has required actions", style="dim")
            ok += 1
            continue

        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would set {', '.join(merged)}", style="yellow")
            ok += 1
        else:
            try:
                kc.admin.update_user(kc_user["id"], {"requiredActions": merged})
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            except Exception as e:
                console.print(f"  ✗ {uname}: {e}", style="red")
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")


# ---------------------------------------------------------------------------
# offboard
# ---------------------------------------------------------------------------

@user.command()
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--skip-gitlab", is_flag=True, help="Skip GitLab logout")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def offboard(username: str | None, input_file: str | None, skip_gitlab: bool, dry_run: bool, yes: bool):
    """Offboard users: disable in Keycloak and logout from GitLab.

    \b
    Steps per user:
    1. Disable in Keycloak (enabled=false)
    2. Revoke all Keycloak sessions
    3. Logout from GitLab (unless --skip-gitlab)

    \b
    Examples:
        ./cli.py user offboard --user john.doe
        ./cli.py user offboard --file users.json --dry-run
        ./cli.py user offboard --user jane.doe --skip-gitlab --yes
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc = keycloak()
    usernames = load_usernames(username, input_file)

    if not yes and not dry_run:
        click.confirm(
            f"This will disable {len(usernames)} user(s) and terminate all sessions. Continue?",
            abort=True,
        )

    console.print(f"\n[bold]Offboarding {len(usernames)} user(s)[/bold]\n")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        console.print(f"[cyan]Processing: {uname}[/cyan]")

        kc_user = kc.get_user_by_username(uname)
        if not kc_user:
            console.print("  ❌ Not found in Keycloak", style="red")
            err += 1
            continue

        user_id = kc_user["id"]

        if kc_user.get("enabled"):
            if dry_run:
                console.print("  [DRY-RUN] Would disable in Keycloak", style="yellow")
            elif not kc.disable_user(user_id):
                err += 1
                continue
        else:
            console.print("  ✓ Already disabled in Keycloak", style="dim")

        if dry_run:
            console.print("  [DRY-RUN] Would revoke all sessions", style="yellow")
        else:
            kc.revoke_user_sessions(user_id)

        if not skip_gitlab:
            gl_user = gitlab().get_user_by_username(uname)
            if gl_user:
                if dry_run:
                    console.print("  [DRY-RUN] Would logout from GitLab", style="yellow")
                else:
                    gitlab().logout_user(gl_user["id"])
            else:
                console.print("  ⚠️  Not found in GitLab", style="yellow")

        ok += 1

    console.print(f"\n✓ {ok}  ✗ {err}")
