"""kc/users/monitoring.py — User monitoring and status commands."""

import json
import sys

import click
from context import console, keycloak, load_usernames
from rich.table import Table

# ---------------------------------------------------------------------------
# check-sessions
# ---------------------------------------------------------------------------

@click.command("check-sessions")
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
def check_sessions(username: str | None, input_file: str | None):
    """Show active Keycloak sessions for user(s).

    \b
    Examples:
        ./cli.py kc user check-sessions --user john.doe
        ./cli.py kc user check-sessions --file users.json
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    for uname in usernames:
        console.print(f"\n[bold]Active sessions: {uname}[/bold]\n")

        kc_user = kc_client.get_user_by_username(uname)
        if not kc_user:
            console.print(f"❌ User '{uname}' not found in Keycloak", style="red")
            continue

        sessions = kc_client.get_user_sessions(kc_user["id"])
        if not sessions:
            console.print("✓ No active sessions", style="green")
            continue

        console.print(f"Found {len(sessions)} active session(s):", style="cyan")
        for session in sessions:
            t = Table(show_header=False, box=None)
            t.add_column("Property", style="dim")
            t.add_column("Value")
            t.add_row("Session ID",  session.get("id",         "N/A"))
            t.add_row("IP Address",  session.get("ipAddress",  "N/A"))
            t.add_row("Started",     session.get("start",      "N/A"))
            t.add_row("Last Access", session.get("lastAccess", "N/A"))
            clients = session.get("clients", {})
            if clients:
                t.add_row("Clients", ", ".join(clients.keys()))
            console.print(t)
            console.print()


# ---------------------------------------------------------------------------
# list-status
# ---------------------------------------------------------------------------

@click.command("list-status")
@click.option("--filter", "filt",
              type=click.Choice(["all", "incomplete", "complete"]),
              default="incomplete", show_default=True)
@click.option("--format", "-f", "fmt",
              type=click.Choice(["table", "json"]),
              default="table", show_default=True)
def list_status(filt: str, fmt: str):
    """List users and their onboarding status (pending required actions).

    \b
    Examples:
        ./cli.py kc user list-status
        ./cli.py kc user list-status --filter all --format json
    """
    console.print("\n[bold]User Onboarding Status[/bold]\n")
    console.print("📊 Fetching users…", style="dim")

    kc_client = keycloak()
    all_users = kc_client.admin.get_users()
    by_status: dict[str, list] = {"incomplete": [], "complete": []}

    for u in all_users:
        actions = u.get("requiredActions", [])
        by_status["incomplete" if actions else "complete"].append({
            "username":         u.get("username", "N/A"),
            "email":            u.get("email",    "N/A"),
            "enabled":          u.get("enabled",  False),
            "required_actions": actions,
        })

    filtered = (
        by_status["incomplete"] if filt == "incomplete"
        else by_status["complete"] if filt == "complete"
        else by_status["incomplete"] + by_status["complete"]
    )

    if fmt == "table":
        t = Table(title=f"Users ({filt})")
        t.add_column("Username",         style="cyan")
        t.add_column("Email",            style="dim")
        t.add_column("Enabled",          style="magenta")
        t.add_column("Required Actions", style="yellow")
        for row in filtered:
            t.add_row(
                row["username"], row["email"],
                "✓" if row["enabled"] else "✗",
                ", ".join(row["required_actions"]) or "—",
            )
        console.print(t)
        console.print("\n[bold]Summary[/bold]")
        console.print(f"  Total:      {len(all_users)}",               style="cyan")
        console.print(f"  Complete:   {len(by_status['complete'])}",   style="green")
        console.print(f"  Incomplete: {len(by_status['incomplete'])}", style="yellow")
    else:
        console.print(json.dumps({
            "total_users": len(all_users),
            "complete":    len(by_status["complete"]),
            "incomplete":  len(by_status["incomplete"]),
            "users":       filtered,
        }, indent=2))


# ---------------------------------------------------------------------------
# monitor
# ---------------------------------------------------------------------------

@click.command()
@click.option("--filter", "filt",
              type=click.Choice(["all", "no-password", "no-2fa", "incomplete"]),
              default="all", show_default=True,
              help="Filter: all | no-password | no-2fa | incomplete (missing pw OR 2FA)")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["table", "json"]),
              default="table", show_default=True)
def monitor(filt: str, fmt: str):
    """Monitor password and 2FA credential status across all users.

    \b
    Examples:
        ./cli.py kc user monitor
        ./cli.py kc user monitor --filter no-2fa
        ./cli.py kc user monitor --filter incomplete --format json
    """
    console.print("\n[bold]User Password & 2FA Status[/bold]\n")
    console.print("📊 Fetching users…", style="dim")

    kc_client = keycloak()
    all_users = kc_client.admin.get_users()
    total = len(all_users)
    n_pw = n_2fa = 0
    rows = []

    for u in all_users:
        creds   = kc_client.get_credentials(u["id"])
        has_pw  = any(c.get("type") == "password" for c in creds)
        has_2fa = any(c.get("type") == "otp"      for c in creds)

        if has_pw:  n_pw  += 1
        if has_2fa: n_2fa += 1

        include = (
            filt == "all"
            or (filt == "no-password" and not has_pw)
            or (filt == "no-2fa"      and not has_2fa)
            or (filt == "incomplete"  and (not has_pw or not has_2fa))
        )
        if include:
            rows.append({
                "username":     u.get("username", "N/A"),
                "email":        u.get("email",    "N/A"),
                "has_password": has_pw,
                "has_2fa":      has_2fa,
                "enabled":      u.get("enabled",  False),
            })

    pw_pct = n_pw  / total * 100 if total else 0
    fa_pct = n_2fa / total * 100 if total else 0

    if fmt == "table":
        t = Table(title="Statistics")
        t.add_column("Metric",      style="cyan")
        t.add_column("Count",       justify="right", style="magenta")
        t.add_column("%",           justify="right", style="green")
        t.add_row("Total",           str(total),         "100%")
        t.add_row("With password",   str(n_pw),          f"{pw_pct:.1f}%")
        t.add_row("With 2FA",        str(n_2fa),         f"{fa_pct:.1f}%")
        t.add_row("No password",     str(total - n_pw),  f"{100 - pw_pct:.1f}%")
        t.add_row("No 2FA",          str(total - n_2fa), f"{100 - fa_pct:.1f}%")
        console.print(t)

        if rows:
            console.print(f"\n[bold]Users ({filt}):[/bold]\n")
            ut = Table()
            ut.add_column("Username", style="cyan")
            ut.add_column("Email",    style="dim")
            ut.add_column("Password", style="green")
            ut.add_column("2FA",      style="yellow")
            ut.add_column("Enabled",  style="magenta")
            for r in rows:
                ut.add_row(
                    r["username"], r["email"],
                    "✓" if r["has_password"] else "✗",
                    "✓" if r["has_2fa"]      else "✗",
                    "✓" if r["enabled"]      else "✗",
                )
            console.print(ut)
            console.print(f"\nTotal: {len(rows)} users", style="dim")
    else:
        console.print(json.dumps({
            "total":         total,
            "with_password": n_pw,
            "with_2fa":      n_2fa,
            "password_pct":  round(pw_pct, 2),
            "twofa_pct":     round(fa_pct, 2),
            "users":         rows,
        }, indent=2))
