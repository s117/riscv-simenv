import click

from .checkpoint import cmd_rm_checkpoint
from .manifest import cmd_rm_manifest
from .sysroot import cmd_rm_sysroot


@click.group()
@click.pass_context
def cmd_group_remove(ctx):
    """
    Remove sysroot / app / checkpoint from the repository.
    """
    pass


cmd_group_remove.add_command(cmd_rm_checkpoint, name="checkpoint")
cmd_group_remove.add_command(cmd_rm_manifest, name="manifest")
cmd_group_remove.add_command(cmd_rm_sysroot, name="sysroot")
