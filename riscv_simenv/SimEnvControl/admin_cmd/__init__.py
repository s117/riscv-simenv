#!/usr/bin/env python3

import click

from .add import cmd_group_add
from .initrepo import cmd_init_repo
from .remove import cmd_group_remove
from .show import cmd_group_show
from .subrepo import cmd_sub_repo


@click.group()
@click.pass_context
def cmd_group_repo(ctx):
    """
    Manage the app repository (requires admin access)
    """
    pass


cmd_group_repo.add_command(cmd_group_add, name="add")
cmd_group_repo.add_command(cmd_group_remove, name="remove")
cmd_group_repo.add_command(cmd_group_show, name="show")
cmd_group_repo.add_command(cmd_init_repo, name="initrepo")
cmd_group_repo.add_command(cmd_sub_repo, name="subrepo")
