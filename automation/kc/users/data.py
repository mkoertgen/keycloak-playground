"""kc/users/data.py — User data import/export commands."""

import json
import sys

import click
from context import console, keycloak, load_usernames

# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@click.command()
@click.option("--user", "-u", "username", default=None, help="Single username")
@click.option("--file", "-f", "input_file", type=click.Path(exists=True), default=None,
              help="JSON file with usernames")
@click.option("--output", "-o", "output_file", required=True, type=click.Path(),
              help="Output JSON file")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output")
def export(username: str | None, input_file: str | None, output_file: str, pretty: bool):
    """Export user(s) data from Keycloak to JSON.

    Exports username, email, name, enabled status, required actions,
    attributes, and group memberships.

    \b
    Examples:
        ./cli.py kc user export --user john.doe --output john.json
        ./cli.py kc user export --file users.json --output export.json --pretty
    """
    if not username and not input_file:
        console.print("❌ Provide --user or --file", style="red")
        sys.exit(1)

    kc_client = keycloak()
    usernames = load_usernames(username, input_file)

    console.print(f"\n[bold]Exporting {len(usernames)} user(s)[/bold]\n")

    exported = []
    ok = err = 0

    for uname in usernames:
        kc_user = kc_client.get_user_by_username(uname)
        if not kc_user:
            console.print(f"  ✗ {uname}: not found", style="red")
            err += 1
            continue

        # Get groups
        try:
            user_groups = kc_client.admin.get_user_groups(kc_user["id"])
            group_names = [g["name"] for g in user_groups]
        except Exception:
            group_names = []

        user_data = {
            "username": kc_user.get("username"),
            "email": kc_user.get("email"),
            "firstName": kc_user.get("firstName"),
            "lastName": kc_user.get("lastName"),
            "enabled": kc_user.get("enabled", False),
            "emailVerified": kc_user.get("emailVerified", False),
            "requiredActions": kc_user.get("requiredActions", []),
            "attributes": kc_user.get("attributes", {}),
            "groups": group_names,
        }

        exported.append(user_data)
        console.print(f"  ✓ {uname}", style="green")
        ok += 1

    # Write to file
    try:
        with open(output_file, "w") as f:
            json.dump(exported, f, indent=2 if pretty else None)
        console.print(f"\n✓ Exported {ok} user(s) to {output_file}", style="green")
        if err:
            console.print(f"✗ {err} user(s) failed", style="red")
    except Exception as e:
        console.print(f"\n✗ Failed to write to {output_file}: {e}", style="red")
        sys.exit(1)


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

@click.command("import")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--update", is_flag=True, help="Update existing users instead of skipping")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would happen without making changes")
def import_users(input_file: str, update: bool, dry_run: bool):
    """Import user(s) from JSON to Keycloak.

    Creates new users or updates existing ones (with --update).
    Does not import passwords or credentials.

    \b
    Examples:
        ./cli.py kc user import users.json
        ./cli.py kc user import users.json --update --dry-run
    """
    try:
        with open(input_file) as f:
            users = json.load(f)
    except Exception as e:
        console.print(f"❌ Failed to read {input_file}: {e}", style="red")
        sys.exit(1)

    if not isinstance(users, list):
        console.print("❌ JSON file must contain an array of user objects", style="red")
        sys.exit(1)

    console.print(f"\n[bold]Importing {len(users)} user(s)[/bold]\n")
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE[/bold yellow]\n")

    kc_client = keycloak()
    created = updated = skipped = err = 0

    for user_data in users:
        username = user_data.get("username")
        if not username:
            console.print("  ✗ Missing username in user data", style="red")
            err += 1
            continue

        existing = kc_client.get_user_by_username(username)

        if existing:
            if not update:
                console.print(f"  ⊘ {username}: already exists (use --update)", style="dim")
                skipped += 1
                continue

            if dry_run:
                console.print(f"  [DRY-RUN] {username}: would update", style="yellow")
                updated += 1
            else:
                try:
                    update_payload = {
                        "email": user_data.get("email"),
                        "firstName": user_data.get("firstName"),
                        "lastName": user_data.get("lastName"),
                        "enabled": user_data.get("enabled", True),
                        "emailVerified": user_data.get("emailVerified", False),
                        "requiredActions": user_data.get("requiredActions", []),
                        "attributes": user_data.get("attributes", {}),
                    }
                    kc_client.admin.update_user(existing["id"], update_payload)
                    console.print(f"  ✓ {username}: updated", style="green")
                    updated += 1
                except Exception as e:
                    console.print(f"  ✗ {username}: {e}", style="red")
                    err += 1
        else:
            if dry_run:
                console.print(f"  [DRY-RUN] {username}: would create", style="yellow")
                created += 1
            else:
                try:
                    create_payload = {
                        "username": username,
                        "email": user_data.get("email"),
                        "firstName": user_data.get("firstName"),
                        "lastName": user_data.get("lastName"),
                        "enabled": user_data.get("enabled", True),
                        "emailVerified": user_data.get("emailVerified", False),
                        "requiredActions": user_data.get("requiredActions", []),
                        "attributes": user_data.get("attributes", {}),
                    }
                    kc_client.admin.create_user(create_payload)
                    console.print(f"  ✓ {username}: created", style="green")
                    created += 1
                except Exception as e:
                    console.print(f"  ✗ {username}: {e}", style="red")
                    err += 1

    console.print(
        f"\n✓ Created: {created}  Updated: {updated}  Skipped: {skipped}  ✗ Errors: {err}",
        style="cyan" if not err else "yellow"
    )
