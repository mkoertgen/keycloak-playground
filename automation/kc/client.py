"""Keycloak admin API client."""

from rich.console import Console

from keycloak import KeycloakAdmin, KeycloakGetError

console = Console()


class KeycloakClient:
    """Keycloak admin client."""

    def __init__(self, url: str, admin_user: str, admin_password: str, realm: str):
        self.url = url
        self.realm = realm

        password_str = (
            admin_password.get_secret_value()
            if hasattr(admin_password, "get_secret_value")
            else admin_password
        )

        self.admin = KeycloakAdmin(
            server_url=url,
            username=admin_user,
            password=password_str,
            realm_name=realm,
            verify=True,
            user_realm_name="master",
        )

        console.print(f"✓ Connected to Keycloak: {url} (realm: {realm})", style="green")

    def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username (exact match)."""
        try:
            users = self.admin.get_users({"username": username, "exact": True})
            return users[0] if users else None
        except KeycloakGetError:
            return None

    def get_user_sessions(self, user_id: str) -> list[dict]:
        """Get all active sessions for a user."""
        try:
            return self.admin.get_user_sessions(user_id)
        except Exception as e:
            console.print(f"⚠️  Error getting sessions for {user_id}: {e}", style="yellow")
            return []

    def get_credentials(self, user_id: str) -> list[dict]:
        """Get all credentials for a user (password, OTP, etc.)."""
        try:
            return self.admin.get_credentials(user_id)
        except Exception as e:
            console.print(f"⚠️  Error getting credentials for {user_id}: {e}", style="yellow")
            return []

    def disable_user(self, user_id: str) -> bool:
        """Disable a user."""
        try:
            self.admin.update_user(user_id, {"enabled": False})
            console.print(f"✓ Disabled user {user_id}", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to disable user {user_id}: {e}", style="red")
            return False

    def enable_user(self, user_id: str) -> bool:
        """Enable a user."""
        try:
            self.admin.update_user(user_id, {"enabled": True})
            console.print(f"✓ Enabled user {user_id}", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to enable user {user_id}: {e}", style="red")
            return False

    def revoke_user_sessions(self, user_id: str) -> bool:
        """Revoke all sessions for a user."""
        try:
            self.admin.user_logout(user_id)
            console.print(f"✓ Revoked sessions for {user_id}", style="green")
            return True
        except Exception as e:
            console.print(f"⚠️  Error revoking sessions for {user_id}: {e}", style="yellow")
            return False

    # -----------------------------------------------------------------------
    # Group operations
    # -----------------------------------------------------------------------

    def get_groups(self, search: str | None = None) -> list[dict]:
        """Get all groups, optionally filtered by search term."""
        try:
            query = {"search": search} if search else {}
            return self.admin.get_groups(query)
        except Exception as e:
            console.print(f"⚠️  Error getting groups: {e}", style="yellow")
            return []

    def get_group_by_name(self, name: str) -> dict | None:
        """Get group by name (exact match)."""
        try:
            groups = self.admin.get_groups({"search": name, "exact": True})
            return groups[0] if groups else None
        except Exception:
            return None

    def get_group_members(self, group_id: str) -> list[dict]:
        """Get all members of a group."""
        try:
            return self.admin.get_group_members(group_id)
        except Exception as e:
            console.print(f"⚠️  Error getting group members: {e}", style="yellow")
            return []

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to a group."""
        try:
            self.admin.group_user_add(user_id, group_id)
            console.print(f"✓ Added user to group", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to add user to group: {e}", style="red")
            return False

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove a user from a group."""
        try:
            self.admin.group_user_remove(user_id, group_id)
            console.print(f"✓ Removed user from group", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to remove user from group: {e}", style="red")
            return False
