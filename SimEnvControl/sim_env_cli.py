#!/usr/bin/env python3
import click

from .admin_cmd import cmd_group_repo
# To support auto-completion in bash 4.2 shipped with CentOS 7
from .libsimenv.click_bash42_completion import patch
from .libsimenv.repo_path import get_default_repo_path
from .user_cmd.list import cmd_list
from .user_cmd.mkgen import cmd_mkgen
from .user_cmd.spawn import cmd_env_spawn
from .user_cmd.verify import cmd_env_verify

patch()


@click.group()
@click.pass_context
@click.option("--repo-path", envvar='RISCV_SIMENV_REPO_PATH',
              type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help='Override the SimEnv repository path given by the environmental variable "RISCV_SIMENV_REPO_PATH".')
def cli(ctx, repo_path):
    """
    The simenv utility
    """
    ctx.ensure_object(dict)
    if not repo_path:
        repo_path = get_default_repo_path(create_if_not_exist=False)
    ctx.obj["repo_path"] = repo_path


cli.add_command(cmd_list, name="list")
cli.add_command(cmd_mkgen, name="mkgen")
cli.add_command(cmd_env_spawn, name="spawn")
cli.add_command(cmd_env_verify, name="verify")
cli.add_command(cmd_group_repo, name="repo")
