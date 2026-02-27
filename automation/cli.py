#!/usr/bin/env python3
"""Keycloak-GitLab automation tool — entry point."""

import click

# context is imported first so settings are loaded before any command module
# registers its decorators.
import context  # noqa: F401 (side-effects: settings load, lazy clients)
from automate.commands import user
from context import console, gitlab, keycloak
from gl.commands import gl as gitlab_cmd
from kc.commands import kc as kc_cmd


@click.group(context_settings={"show_default": True})
@click.version_option(version="0.2.0")
def cli():
    """Keycloak-GitLab Automation CLI

    \b
    Quick start:
        cli.py validate
        cli.py user onboard --user john.doe
        cli.py user offboard --user john.doe --dry-run
        cli.py kc user enable --user john.doe
        cli.py kc user disable --user john.doe
        cli.py kc user revoke-sessions --user john.doe
        cli.py kc user export --user john.doe --output user.json
        cli.py kc user import users.json --update
        cli.py kc user check-sessions --user john.doe
        cli.py kc user list-status
        cli.py kc user monitor
        cli.py kc user set-actions --user john.doe UPDATE_PASSWORD
        cli.py kc user send-email --user john.doe UPDATE_PASSWORD
        cli.py kc group list
        cli.py kc group members gitlab-admins
        cli.py kc group add gitlab-admins --user john.doe
        cli.py kc group remove gitlab-admins --user john.doe
        cli.py gl logout --user john.doe
        cli.py gitlab group-sync --dry-run
        cli.py serve
    """


@cli.command()
def validate():
    """Check connectivity to Keycloak and GitLab.

    Verifies that the credentials in .env are valid and both services
    are reachable. Run this after setting up .env for the first time.

    \b
    Examples:
        ./cli.py validate
    """
    console.print("\n[bold]Validating connections…[/bold]\n")

    ok = True

    # Keycloak
    try:
        kc = keycloak()
        kc.admin.get_users({"max": 1})
        console.print("✓ Keycloak reachable and authenticated", style="green")
    except Exception as e:
        console.print(f"✗ Keycloak: {e}", style="red")
        ok = False

    # GitLab
    try:
        gitlab()  # connection is verified in __init__
        console.print("✓ GitLab reachable and authenticated", style="green")
    except Exception as e:
        console.print(f"✗ GitLab: {e}", style="red")
        ok = False

    if ok:
        console.print("\n✓ All connections OK", style="bold green")
    else:
        console.print("\n✗ Some connections failed — check .env", style="bold red")
        raise SystemExit(1)


@cli.command()
@click.option("--reload", is_flag=True, default=False, help="Auto-reload on code changes")
def serve(reload: bool):
    """Start the webhook + group-sync server.

    Host/port/cron are read from .env (API_HOST, API_PORT, GROUP_SYNC_CRON).
    """
    import uvicorn
    from context import settings

    uvicorn.run(
        "server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=reload or settings.api_reload,
        log_level="info",
    )


cli.add_command(user)
cli.add_command(kc_cmd, name="kc")
cli.add_command(gitlab_cmd, name="gitlab")

if __name__ == "__main__":
    cli()
