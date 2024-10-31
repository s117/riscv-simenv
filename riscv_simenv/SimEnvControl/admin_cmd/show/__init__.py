import click

from .checkpoint import cmd_show_checkpoint
from .manifest import cmd_show_manifest
from .sysroot import cmd_show_sysroot


@click.group()
@click.pass_context
def cmd_group_show(ctx):
    """
    Show sysroot / app / checkpoint from the repository.
    """
    pass


cmd_group_show.add_command(cmd_show_checkpoint, name="checkpoint")
cmd_group_show.add_command(cmd_show_manifest, name="manifest")
cmd_group_show.add_command(cmd_show_sysroot, name="sysroot")
tabulate_formats = {
    "tablefmt": "fancy_grid",
    "maxcolwidths": 32
}
