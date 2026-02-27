"""kc/groups.py — Group management commands."""

import json
import sys

import click
from context import console, keycloak, load_usernames
from rich.table import Table


@click.group()
def group():
    """Group management commands."""


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@group.command("list")
@click.option("--search", "-s", default=None, help="Filter groups by name")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["table", "json"]),
              default="table", show_default=True)
def list_groups(search: str | None, fmt: str):
    """List all Keycloak groups.

    \b
    Examples:
        ./cli.py kc group list
        ./cli.py kc group list --search admin
        ./cli.py kc group list --format json
    """
    kc_client = keycloak()
    groups = kc_client.get_groups(search=search)

    if fmt == "json":
        console.print(json.dumps(groups, indent=2))
        return

    if not groups:
        console.print("\n✓ No groups found", style="dim")
        return

    console.print(f"\n[bold]Groups ({len(groups)})[/bold]\n")
    t = Table()
    t.add_column("Name", style="cyan")
    t.add_column("Path", style="dim")
    t.add_column("ID", style="yellow")

    for g in groups:
        t.add_row(g.get("name", "N/A"), g.get("path", "N/A"), g.get("id", "N/A"))

    console.print(t)


# ---------------------------------------------------------------------------
# members
# ---------------------------------------------------------------------------

@group.command("members")
@click.argument("group_name")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["table", "json"]),
              default="table", show_default=True)
def list_members(group_name: str, fmt: str):
    """List members of a group.

    \b
    Examples:
        ./cli.py kc group members gitlab-admins
        ./cli.py kc group members gitlab-admins --format json
    """
    kc_client = keycloak()
    group = kc_client.get_group_by_name(group_name)

    if not group:
        console.print(f"❌ Group '{group_name}' not found", style="red")
        sys.exit(1)

    members = kc_client.get_group_members(group["id"])

    if fmt == "json":
        console.print(json.dumps(members, indent=2))
        return

    console.print(f"\n[bold]Members of '{group_name}' ({len(members)})[/bold]\n")

    if not members:
        console.print("✓ No members", style="dim")
        return

    t = Table()
    t.add_column("Username", style="cyan")
    t.add_column("Email", style="dim")
    t.add_column("Enabled", style="magenta")

    for m in members:
        t.add_row(
            m.get("username", "N/A"),
            m.get("email", "N/A"),
            "✓" if m.get("enabled") else "✗",
        )

    console.print(t)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

@group.command("add")
@click.argument("group_name")
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def add_to_group(group_name: str, username: str | None, input_file: str | None, dry_run: bool):
    """Add user(s) to a group.

    \b
    Examples:
        ./cli.py kc group add gitlab-admins --user john.doe
        ./cli.py kc group add gitlab-developers --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    group = kc_client.get_group_by_name(group_name)

    if not group:
        console.print(f"❌ Group '{group_name}' not found", style="red")
        sys.exit(1)

    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Adding {len(usernames)} user(s) to '{group_name}'[/bold]\n")
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
            console.print(f"  [DRY-RUN] {uname}: would add to group", style="yellow")
            ok += 1
        else:
            if kc_client.add_user_to_group(kc_user["id"], group["id"]):
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            else:
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

@group.command("remove")
@click.argument("group_name")
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def remove_from_group(group_name: str, username: str | None, input_file: str | None, dry_run: bool):
    """Remove user(s) from a group.

    \b
    Examples:
        ./cli.py kc group remove gitlab-admins --user john.doe
        ./cli.py kc group remove gitlab-developers --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    group = kc_client.get_group_by_name(group_name)

    if not group:
        console.print(f"❌ Group '{group_name}' not found", style="red")
        sys.exit(1)

    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Removing {len(usernames)} user(s) from '{group_name}'[/bold]\n")
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
            console.print(f"  [DRY-RUN] {uname}: would remove from group", style="yellow")
            ok += 1
        else:
            if kc_client.remove_user_from_group(kc_user["id"], group["id"]):
                console.print(f"  ✓ {uname}", style="green")
                ok += 1
            else:
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")
