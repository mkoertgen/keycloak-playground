"""gitlab/commands.py — GitLab command group."""

import json
import sys

import click
from context import console, gitlab, load_usernames
from rich.table import Table


@click.group()
def gl():
    """GitLab operations (logout, group sync)."""


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

@gl.command()
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def logout(username: str | None, input_file: str | None, dry_run: bool):
    """Logout user(s) from GitLab (terminate all sessions).

    \b
    Examples:
        ./cli.py gl logout --user john.doe
        ./cli.py gl logout --file users.json --dry-run
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    gl_client = gitlab()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Logging out {len(usernames)} user(s) from GitLab[/bold]\n")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    ok = err = 0
    for uname in usernames:
        gl_user = gl_client.get_user_by_username(uname)
        if not gl_user:
            console.print(f"  ⚠️  {uname}: not found in GitLab", style="yellow")
            err += 1
            continue

        if dry_run:
            console.print(f"  [DRY-RUN] {uname}: would logout", style="yellow")
            ok += 1
        else:
            if gl_client.logout_user(gl_user["id"]):
                ok += 1
            else:
                err += 1

    console.print(f"\n✓ {ok}  ✗ {err}")


# ---------------------------------------------------------------------------
# group-sync
# ---------------------------------------------------------------------------

@gl.command("group-sync")
@click.option("--group", "-g", "groups", multiple=True, default=None,
              help="Sync only these group(s); defaults to all managed groups (repeatable)")
@click.option("--dry-run", "-n", is_flag=True,
              help="Show what would happen without making changes")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["table", "json"]), default="table", show_default=True)
def group_sync(groups: tuple[str], dry_run: bool, fmt: str):
    """Sync Keycloak group membership → GitLab (one-shot).

    Mirrors every managed Keycloak group to the matching GitLab group:
    adds members missing in GitLab, removes members no longer in Keycloak.

    Use 'serve' to run this on a schedule via the webhook server.

    \b
    Examples:
        ./cli.py gitlab group-sync
        ./cli.py gitlab group-sync --dry-run
        ./cli.py gitlab group-sync -g gitlab-admins -g gitlab-developers
        ./cli.py gitlab group-sync --format json
    """
    from gl.group_sync import GroupSync

    syncer = GroupSync(keycloak(), gitlab())
    if groups:
        syncer.managed_groups = list(groups)

    console.print("\n[bold]Group Sync: Keycloak → GitLab[/bold]")
    console.print(f"Groups: {', '.join(syncer.managed_groups)}\n", style="dim")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE — no changes will be made[/bold yellow]\n")

    results: dict[str, dict] = {}

    for group_name in syncer.managed_groups:
        kc_members = syncer._get_keycloak_group_members(group_name)
        gl_members = syncer._get_gitlab_group_members(group_name)
        to_add    = kc_members - gl_members
        to_remove = gl_members - kc_members

        if dry_run:
            results[group_name] = {
                "keycloak_members": len(kc_members),
                "gitlab_members":   len(gl_members),
                "would_add":        sorted(to_add),
                "would_remove":     sorted(to_remove),
            }
        else:
            added, removed, errors = [], [], []
            for u in to_add:
                try:
                    syncer._add_user_to_gitlab_group(u, group_name)
                    added.append(u)
                except Exception as e:
                    errors.append(f"+{u}: {e}")
            for u in to_remove:
                try:
                    syncer._remove_user_from_gitlab_group(u, group_name)
                    removed.append(u)
                except Exception as e:
                    errors.append(f"-{u}: {e}")
            results[group_name] = {
                "keycloak_members": len(kc_members),
                "gitlab_members":   len(gl_members),
                "added":   added,
                "removed": removed,
                "errors":  errors,
            }

    if fmt == "json":
        console.print(json.dumps(results, indent=2))
        return

    t = Table(title="Group Sync Results")
    t.add_column("Group",      style="cyan")
    t.add_column("KC members", justify="right", style="dim")
    t.add_column("GL members", justify="right", style="dim")
    t.add_column("Would add" if dry_run else "Added",   style="green")
    t.add_column("Would remove" if dry_run else "Removed", style="yellow")
    if not dry_run:
        t.add_column("Errors", style="red")

    total_add = total_rem = total_err = 0
    for name, r in results.items():
        adds = r.get("would_add", r.get("added", []))
        rems = r.get("would_remove", r.get("removed", []))
        errs = r.get("errors", [])
        total_add += len(adds)
        total_rem += len(rems)
        total_err += len(errs)
        row = [name, str(r["keycloak_members"]), str(r["gitlab_members"]),
               ", ".join(adds) or "—", ", ".join(rems) or "—"]
        if not dry_run:
            row.append(", ".join(errs) or "—")
        t.add_row(*row)

    console.print(t)
    console.print(
        f"\n{'Would add' if dry_run else 'Added'}: {total_add}  "
        f"{'Would remove' if dry_run else 'Removed'}: {total_rem}"
        + (f"  Errors: {total_err}" if total_err else ""),
        style="dim",
    )
    if total_err:
        sys.exit(1)
