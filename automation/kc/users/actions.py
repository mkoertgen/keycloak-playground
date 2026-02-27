"""kc/users/actions.py — User required actions and email commands."""

import sys

import click
from context import console, keycloak, load_usernames

# ---------------------------------------------------------------------------
# set-actions
# ---------------------------------------------------------------------------

@click.command("set-actions")
@click.argument("actions", nargs=-1, required=True)
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def set_actions(actions: tuple[str], username: str | None, input_file: str | None, dry_run: bool):
    """Overwrite required actions for one or multiple users.

    Unlike 'user onboard', this *replaces* the current action list entirely.

    \b
    Examples:
        ./cli.py kc user set-actions --user john.doe UPDATE_PASSWORD CONFIGURE_TOTP
        ./cli.py kc user set-actions --file users.json UPDATE_PASSWORD --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Setting required actions for {len(usernames)} user(s)[/bold]")
    console.print(f"Actions: {', '.join(actions)}\n", style="dim")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        u = kc_client.get_user_by_username(uname)
        if not u:
            console.print(f"  ✗ {uname}: not found", style="red")
            err += 1
            continue
        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would set {', '.join(actions)}", style="yellow")
            ok += 1
        else:
            try:
                kc_client.admin.update_user(u["id"], {"requiredActions": list(actions)})
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            except Exception as e:
                console.print(f"  ✗ {uname}: {e}", style="red")
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")


# ---------------------------------------------------------------------------
# send-email
# ---------------------------------------------------------------------------

@click.command("send-email")
@click.argument("actions", nargs=-1, required=True)
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--lifespan", default=86400, show_default=True,
              help="Email link validity in seconds (default 24 h)")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without sending emails")
def send_email(actions: tuple[str], username: str | None, input_file: str | None, lifespan: int, dry_run: bool):
    """Send an action email to one or multiple users.

    \b
    Common actions:
    - UPDATE_PASSWORD  Password reset link
    - CONFIGURE_TOTP   2FA setup link
    - VERIFY_EMAIL     Email verification link

    \b
    Examples:
        ./cli.py kc user send-email --user john.doe UPDATE_PASSWORD
        ./cli.py kc user send-email --file users.json CONFIGURE_TOTP
        ./cli.py kc user send-email --file users.json UPDATE_PASSWORD --lifespan 172800
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Sending action email to {len(usernames)} user(s)[/bold]")
    console.print(f"Actions: {', '.join(actions)}  |  Link valid: {lifespan}s\n", style="dim")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        u = kc_client.get_user_by_username(uname)
        if not u:
            console.print(f"  ✗ {uname}: not found", style="red")
            err += 1
            continue
        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would send {', '.join(actions)}", style="yellow")
            ok += 1
        else:
            try:
                kc_client.admin.send_update_account(
                    user_id=u["id"],
                    payload=list(actions),
                    lifespan=lifespan,
                )
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            except Exception as e:
                console.print(f"  ✗ {uname}: {e}", style="red")
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")
