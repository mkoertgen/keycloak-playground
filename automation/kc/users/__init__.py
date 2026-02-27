"""kc/users/ — User management commands package."""

import click

from .actions import send_email, set_actions
from .data import export, import_users
from .lifecycle import disable, enable, revoke_sessions
from .monitoring import check_sessions, list_status, monitor


@click.group()
def user():
    """User management commands."""


# Register lifecycle commands
user.add_command(enable)
user.add_command(disable)
user.add_command(revoke_sessions)

# Register data commands
user.add_command(export)
user.add_command(import_users, name="import")

# Register monitoring commands
user.add_command(check_sessions)
user.add_command(list_status)
user.add_command(monitor)

# Register action commands
user.add_command(set_actions)
user.add_command(send_email)
