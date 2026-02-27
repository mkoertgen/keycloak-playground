"""Shared application context: settings, lazy client singletons, helpers.

Imported by every command module. Module-level code here runs once at startup
because cli.py imports the command packages, which each import this module.
"""

import json
import sys

from config import Settings
from gl.client import GitLabClient
from kc.client import KeycloakClient
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Settings — loaded from .env / environment variables
# ---------------------------------------------------------------------------
try:
    settings = Settings()
except Exception as _e:
    console.print(f"❌ Configuration error: {_e}", style="red")
    console.print("   Copy .env.example to .env and fill in your credentials.", style="yellow")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Lazy client singletons
# ---------------------------------------------------------------------------
_kc: "KeycloakClient | None" = None
_gl: "GitLabClient | None" = None


def keycloak() -> KeycloakClient:
    """Return the Keycloak client, connecting on first call."""
    global _kc
    if _kc is None:
        try:
            _kc = KeycloakClient(
                settings.keycloak_url,
                settings.keycloak_admin_user,
                settings.keycloak_admin_password,
                settings.keycloak_realm,
            )
        except Exception as e:
            console.print(f"❌ Keycloak connection failed: {e}", style="red")
            console.print("   Check KEYCLOAK_* in .env", style="yellow")
            sys.exit(1)
    return _kc


def gitlab() -> GitLabClient:
    """Return the GitLab client, connecting on first call."""
    global _gl
    if _gl is None:
        try:
            _gl = GitLabClient(settings.gitlab_url, settings.gitlab_admin_token)
        except Exception as e:
            console.print(f"❌ GitLab connection failed: {e}", style="red")
            console.print("   Check GITLAB_* in .env", style="yellow")
            sys.exit(1)
    return _gl


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def load_usernames(username: str | None, input_file: str | None) -> list[str]:
    """Resolve a username list from --user / --file options.

    Accepts:
    - plain string array: ``["user1", "user2"]``
    - object array with ``username`` key: ``[{"username": "...", ...}]``
    - mapping format:     ``[{"keycloak_username": "...", ...}]``
    """
    if username:
        return [username]

    with open(input_file) as f:
        data = json.load(f)

    if not isinstance(data, list):
        console.print("❌ File must contain a JSON array", style="red")
        sys.exit(1)

    if not data:
        return []

    if isinstance(data[0], str):
        return data

    if isinstance(data[0], dict):
        key = "keycloak_username" if "keycloak_username" in data[0] else "username"
        return [entry[key] for entry in data if key in entry]

    console.print("❌ Could not parse usernames from file", style="red")
    sys.exit(1)
