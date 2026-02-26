"""Group synchronization between Keycloak and GitLab.

OIDC doesn't support automatic group assignment (would require SAML).
This module provides scheduled sync to mirror Keycloak group membership to GitLab.
"""

import logging
from typing import Dict, List, Set

from clients import GitLabClient, KeycloakClient

logger = logging.getLogger(__name__)


class GroupSync:
    """Synchronize Keycloak groups to GitLab."""

    def __init__(self, kc_client: KeycloakClient, gl_client: GitLabClient):
        self.kc = kc_client
        self.gl = gl_client

        # Groups to sync (must exist in both Keycloak and GitLab)
        self.managed_groups = [
            "gitlab-admins",
            "gitlab-developers",
            "gitlab-external",
            "demo-team-alpha",
            "demo-team-beta",
        ]

    def sync_all_groups(self) -> Dict[str, any]:
        """
        Sync all managed groups from Keycloak to GitLab.

        Returns:
            Summary of sync operations
        """
        logger.info("Starting group synchronization...")

        summary = {
            "total_groups": len(self.managed_groups),
            "synced": 0,
            "errors": 0,
            "details": {},
        }

        for group_name in self.managed_groups:
            try:
                result = self._sync_group(group_name)
                summary["synced"] += 1
                summary["details"][group_name] = result
                logger.info(f"Synced group '{group_name}': {result}")
            except Exception as e:
                summary["errors"] += 1
                summary["details"][group_name] = {"error": str(e)}
                logger.error(f"Failed to sync group '{group_name}': {e}")

        logger.info(
            f"Group sync complete: {summary['synced']}/{summary['total_groups']} groups synced"
        )
        return summary

    def _sync_group(self, group_name: str) -> Dict[str, any]:
        """
        Sync a single group.

        Returns membership changes made.
        """
        # 1. Get Keycloak group members (usernames)
        kc_members = self._get_keycloak_group_members(group_name)

        # 2. Get GitLab group members (usernames)
        gl_members = self._get_gitlab_group_members(group_name)

        # 3. Calculate diff
        to_add = kc_members - gl_members
        to_remove = gl_members - kc_members

        # 4. Apply changes
        added = []
        removed = []

        for username in to_add:
            try:
                self._add_user_to_gitlab_group(username, group_name)
                added.append(username)
            except Exception as e:
                logger.error(f"Failed to add {username} to {group_name}: {e}")

        for username in to_remove:
            try:
                self._remove_user_from_gitlab_group(username, group_name)
                removed.append(username)
            except Exception as e:
                logger.error(f"Failed to remove {username} from {group_name}: {e}")

        return {
            "keycloak_members": len(kc_members),
            "gitlab_members_before": len(gl_members),
            "added": added,
            "removed": removed,
        }

    def _get_keycloak_group_members(self, group_name: str) -> Set[str]:
        """Get usernames of all members in a Keycloak group."""
        try:
            # Get group by name
            groups = self.kc.admin.get_groups({"search": group_name, "exact": True})
            if not groups:
                logger.warning(f"Keycloak group '{group_name}' not found")
                return set()

            group_id = groups[0]["id"]

            # Get group members
            members = self.kc.admin.get_group_members(group_id)

            return {member["username"] for member in members}
        except Exception as e:
            logger.error(
                f"Error getting Keycloak group members for '{group_name}': {e}"
            )
            return set()

    def _get_gitlab_group_members(self, group_name: str) -> Set[str]:
        """Get usernames of all members in a GitLab group."""
        try:
            # Find group by path
            groups = self.gl.client.groups.list(search=group_name)
            matching_group = next((g for g in groups if g.path == group_name), None)

            if not matching_group:
                logger.warning(f"GitLab group '{group_name}' not found")
                return set()

            # Get group members
            members = matching_group.members.list(get_all=True)

            return {member.username for member in members}
        except Exception as e:
            logger.error(f"Error getting GitLab group members for '{group_name}': {e}")
            return set()

    def _add_user_to_gitlab_group(self, username: str, group_name: str):
        """Add a user to a GitLab group."""
        # Find group
        groups = self.gl.client.groups.list(search=group_name)
        matching_group = next((g for g in groups if g.path == group_name), None)

        if not matching_group:
            raise ValueError(f"GitLab group '{group_name}' not found")

        # Find user by username
        users = self.gl.client.users.list(username=username)
        if not users:
            logger.warning(
                f"User '{username}' not found in GitLab (may not have logged in yet)"
            )
            return

        user_id = users[0].id

        # Add user to group (default access level: Developer = 30)
        # Access levels: Guest=10, Reporter=20, Developer=30, Maintainer=40, Owner=50
        access_level = 30  # Developer

        # Special handling for admin group
        if group_name == "gitlab-admins":
            # Note: GitLab admin status is separate from group membership
            # This would require additional API call to set admin flag
            access_level = 40  # Maintainer for admin group

        matching_group.members.create(
            {"user_id": user_id, "access_level": access_level}
        )
        logger.info(f"Added user '{username}' to GitLab group '{group_name}'")

    def _remove_user_from_gitlab_group(self, username: str, group_name: str):
        """Remove a user from a GitLab group."""
        # Find group
        groups = self.gl.client.groups.list(search=group_name)
        matching_group = next((g for g in groups if g.path == group_name), None)

        if not matching_group:
            raise ValueError(f"GitLab group '{group_name}' not found")

        # Find user
        users = self.gl.client.users.list(username=username)
        if not users:
            logger.warning(f"User '{username}' not found in GitLab")
            return

        user_id = users[0].id

        # Remove user from group
        matching_group.members.delete(user_id)
        logger.info(f"Removed user '{username}' from GitLab group '{group_name}'")
