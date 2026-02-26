"""API clients for Keycloak and GitLab."""

import requests
from keycloak import KeycloakAdmin, KeycloakGetError
from rich.console import Console

console = Console()


class KeycloakClient:
    """Keycloak admin client."""
    
    def __init__(self, url: str, admin_user: str, admin_password: str, realm: str):
        """Initialize Keycloak client."""
        self.url = url
        self.realm = realm
        
        password_str = admin_password.get_secret_value() if hasattr(admin_password, 'get_secret_value') else admin_password
        
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
        """Get user by username."""
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
            console.print(f"⚠️  Error getting sessions for user {user_id}: {e}", style="yellow")
            return []
    
    def disable_user(self, user_id: str) -> bool:
        """Disable a user."""
        try:
            self.admin.update_user(user_id, {"enabled": False})
            console.print(f"✓ Disabled user {user_id} in Keycloak", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to disable user {user_id}: {e}", style="red")
            return False
    
    def revoke_user_sessions(self, user_id: str) -> bool:
        """Revoke all sessions for a user by setting notBefore."""
        try:
            self.admin.user_logout(user_id)
            console.print(f"✓ Revoked Keycloak sessions for user {user_id}", style="green")
            return True
        except Exception as e:
            console.print(f"⚠️  Error revoking sessions for user {user_id}: {e}", style="yellow")
            return False


class GitLabClient:
    """GitLab API client."""
    
    def __init__(self, url: str, token: str):
        """Initialize GitLab client."""
        self.url = url.rstrip('/')
        self.token = token.get_secret_value() if hasattr(token, 'get_secret_value') else token
        self.api_url = f"{self.url}/api/v4"
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": self.token})
        
        # Verify connection
        try:
            response = self.session.get(f"{self.api_url}/user")
            response.raise_for_status()
            user = response.json()
            console.print(f"✓ Connected to GitLab: {url} (as {user['username']})", style="green")
        except Exception as e:
            console.print(f"✗ Failed to connect to GitLab: {e}", style="red")
            raise
    
    def get_user_by_username(self, username: str) -> dict | None:
        """Get user by username."""
        try:
            response = self.session.get(
                f"{self.api_url}/users",
                params={"username": username}
            )
            response.raise_for_status()
            users = response.json()
            return users[0] if users else None
        except Exception as e:
            console.print(f"⚠️  Error getting GitLab user {username}: {e}", style="yellow")
            return None
    
    def logout_user(self, user_id: int) -> bool:
        """Logout user from all GitLab sessions.
        
        This calls the admin API endpoint to logout the user:
        POST /users/:user_id/logout
        """
        try:
            response = self.session.post(
                f"{self.api_url}/users/{user_id}/logout"
            )
            response.raise_for_status()
            console.print(f"✓ Logged out user {user_id} from GitLab", style="green")
            return True
        except Exception as e:
            console.print(f"✗ Failed to logout user {user_id} from GitLab: {e}", style="red")
            return False
