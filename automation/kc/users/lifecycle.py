"""kc/users/lifecycle.py — User lifecycle commands (enable, disable, revoke-sessions)."""

import sys

import click
from context import console, keycloak, load_usernames

# ---------------------------------------------------------------------------
# enable
# ---------------------------------------------------------------------------

@click.command()
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def enable(username: str | None, input_file: str | None, dry_run: bool):
    """Enable (activate) user(s) in Keycloak.

    \b
    Examples:
        ./cli.py kc user enable --user john.doe
        ./cli.py kc user enable --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Enabling {len(usernames)} user(s)[/bold]\n")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        kc_user = kc_client.get_user_by_username(uname)
        if not kc_user:
            console.print(f"  ✗ {uname}: not found", style="red")
            err += 1
            continue

        if kc_user.get("enabled"):
            console.print(f"  ⊘ {uname}: already enabled", style="dim")
            ok += 1
            continue

        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would enable", style="yellow")
            ok += 1
        else:
            if kc_client.enable_user(kc_user["id"]):
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            else:
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")


# ---------------------------------------------------------------------------
# disable
# ---------------------------------------------------------------------------

@click.command()
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def disable(username: str | None, input_file: str | None, dry_run: bool):
    """Disable (deactivate) user(s) in Keycloak.

    \b
    Examples:
        ./cli.py kc user disable --user john.doe
        ./cli.py kc user disable --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Disabling {len(usernames)} user(s)[/bold]\n")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        kc_user = kc_client.get_user_by_username(uname)
        if not kc_user:
            console.print(f"  ✗ {uname}: not found", style="red")
            err += 1
            continue

        if not kc_user.get("enabled"):
            console.print(f"  ⊘ {uname}: already disabled", style="dim")
            ok += 1
            continue

        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would disable", style="yellow")
            ok += 1
        else:
            if kc_client.disable_user(kc_user["id"]):
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            else:
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")


# ---------------------------------------------------------------------------
# revoke-sessions
# ---------------------------------------------------------------------------

@click.command("revoke-sessions")
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def revoke_sessions(username: str | None, input_file: str | None, dry_run: bool):
    """Revoke all active sessions for user(s).

    \b
    Examples:
        ./cli.py kc user revoke-sessions --user john.doe
        ./cli.py kc user revoke-sessions --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Revoking sessions for {len(usernames)} user(s)[/bold]\n")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        kc_user = kc_client.get_user_by_username(uname)
        if not kc_user:
            console.print(f"  ✗ {uname}: not found", style="red")
            err += 1
            continue

        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would revoke sessions", style="yellow")
            ok += 1
        else:
            if kc_client.revoke_user_sessions(kc_user["id"]):
                ok += 1
            else:
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")
