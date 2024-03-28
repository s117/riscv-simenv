import click

from .app import cmd_group_add_app
from .checkpoint import cmd_add_checkpoint
from .sysroot import cmd_add_sysroot


@click.group()
@click.pass_context
def cmd_group_add(ctx):
    """
    Add sysroot / app / checkpoint to the repository.
    """
    pass


cmd_group_add.add_command(cmd_group_add_app, name="app")
cmd_group_add.add_command(cmd_add_checkpoint, name="checkpoint")
cmd_group_add.add_command(cmd_add_sysroot, name="sysroot")
