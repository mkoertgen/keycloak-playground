"""GitLab API client."""

import requests
from rich.console import Console

console = Console()


class GitLabClient:
    """GitLab REST API client."""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = (
            token.get_secret_value() if hasattr(token, "get_secret_value") else token
        )
        self.api_url = f"{self.url}/api/v4"
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": self.token})

        # Also expose a python-gitlab client for group_sync (needs .groups, .users)
        try:
            import gitlab as _gl

            self.client = _gl.Gitlab(self.url, private_token=self.token)
            self.client.auth()
        except Exception:
            self.client = None  # optional; group_sync will fail gracefully

        # Verify REST connection
        try:
            resp = self.session.get(f"{self.api_url}/user")
            resp.raise_for_status()
            user = resp.json()
            console.print(
                f"✓ Connected to GitLab: {self.url} (as {user['username']})",
                style="green",
            )
        except Exception as e:
            console.print(f"✗ Failed to connect to GitLab: {e}", style="red")
            raise

    def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username."""
        try:
            resp = self.session.get(
                f"{self.api_url}/users", params={"username": username}
            )
            resp.raise_for_status()
            users = resp.json()
            return users[0] if users else None
        except Exception as e:
            console.print(f"⚠️  Error getting GitLab user {username}: {e}", style="yellow")
            return None

    def logout_user(self, user_id: int) -> bool:
        """Logout user from all GitLab sessions."""
        try:
            resp = self.session.post(f"{self.api_url}/users/{user_id}/logout")
            resp.raise_for_status()
            console.print(f"✓ Logged out user {user_id} from GitLab", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to logout user {user_id} from GitLab: {e}", style="red")
            return False
