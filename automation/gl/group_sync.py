"""Keycloak → GitLab group synchronization."""

import logging
from typing import Dict, Set

from gl.client import GitLabClient
from kc.client import KeycloakClient

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

    def sync_all_groups(self) -> Dict[str, dict]:
        """Sync all managed groups from Keycloak to GitLab."""
        logger.info("Starting group synchronization...")

        summary: Dict[str, dict] = {
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
            except Exception as e:
                summary["errors"] += 1
                summary["details"][group_name] = {"error": str(e)}
                logger.error(f"Failed to sync group '{group_name}': {e}")

        logger.info(
            f"Group sync complete: {summary['synced']}/{summary['total_groups']} groups synced"
        )
        return summary

    def _sync_group(self, group_name: str) -> dict:
        kc_members = self._get_keycloak_group_members(group_name)
        gl_members = self._get_gitlab_group_members(group_name)
        to_add    = kc_members - gl_members
        to_remove = gl_members - kc_members

        added, removed = [], []
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
            "keycloak_members":    len(kc_members),
            "gitlab_members_before": len(gl_members),
            "added":   added,
            "removed": removed,
        }

    def _get_keycloak_group_members(self, group_name: str) -> Set[str]:
        try:
            groups = self.kc.admin.get_groups({"search": group_name, "exact": True})
            if not groups:
                logger.warning(f"Keycloak group '{group_name}' not found")
                return set()
            members = self.kc.admin.get_group_members(groups[0]["id"])
            return {m["username"] for m in members}
        except Exception as e:
            logger.error(f"Error getting Keycloak members for '{group_name}': {e}")
            return set()

    def _get_gitlab_group_members(self, group_name: str) -> Set[str]:
        try:
            groups = self.gl.client.groups.list(search=group_name)
            group = next((g for g in groups if g.path == group_name), None)
            if not group:
                logger.warning(f"GitLab group '{group_name}' not found")
                return set()
            return {m.username for m in group.members.list(get_all=True)}
        except Exception as e:
            logger.error(f"Error getting GitLab members for '{group_name}': {e}")
            return set()

    def _add_user_to_gitlab_group(self, username: str, group_name: str):
        groups = self.gl.client.groups.list(search=group_name)
        group = next((g for g in groups if g.path == group_name), None)
        if not group:
            raise ValueError(f"GitLab group '{group_name}' not found")

        users = self.gl.client.users.list(username=username)
        if not users:
            logger.warning(f"User '{username}' not found in GitLab")
            return

        access_level = 40 if group_name == "gitlab-admins" else 30  # Maintainer / Developer
        group.members.create({"user_id": users[0].id, "access_level": access_level})
        logger.info(f"Added '{username}' to GitLab group '{group_name}'")

    def _remove_user_from_gitlab_group(self, username: str, group_name: str):
        groups = self.gl.client.groups.list(search=group_name)
        group = next((g for g in groups if g.path == group_name), None)
        if not group:
            raise ValueError(f"GitLab group '{group_name}' not found")

        users = self.gl.client.users.list(username=username)
        if not users:
            logger.warning(f"User '{username}' not found in GitLab")
            return

        group.members.delete(users[0].id)
        logger.info(f"Removed '{username}' from GitLab group '{group_name}'")
