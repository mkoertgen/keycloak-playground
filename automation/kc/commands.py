"""kc/commands.py — Keycloak command group."""

import click

from .groups import group
from .users import user


@click.group()
def kc():
    """Keycloak operations (user, group management)."""


# Register sub-groups
kc.add_command(user)
kc.add_command(group)
