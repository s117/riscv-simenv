import click

from .app_analyze import cmd_add_app_analyze
from .app_register import cmd_add_app_register


@click.group()
@click.pass_context
def cmd_group_add_app(ctx):
    """
    Add sysroot / app / checkpoint to the repository.
    """
    pass


cmd_group_add_app.add_command(cmd_add_app_register, name="register")
cmd_group_add_app.add_command(cmd_add_app_analyze, name="analyze")
