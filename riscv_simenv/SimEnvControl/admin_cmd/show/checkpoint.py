import click
from tabulate import tabulate

from ...libsimenv.autocomplete import complete_app_names
from ...libsimenv.checkpoints_db import get_available_checkpoints_for_app, get_checkpoint_abspath
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.utils import get_size_str


@click.command()
@click.pass_context
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
def cmd_show_checkpoint(ctx, app_name):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])
    avail_checkpoints = get_available_checkpoints_for_app(checkpoints_archive_path, app_name)
    if not avail_checkpoints:
        print(f"{app_name} doesn't have any checkpoints.")
        return
    row = []
    for checkpoint in avail_checkpoints:
        checkpoint_path = get_checkpoint_abspath(checkpoints_archive_path, app_name, checkpoint)
        checkpoint_size = get_size_str(checkpoint_path)
        row.append([checkpoint, checkpoint_size, checkpoint_path])

    print(tabulate(row, headers=["Checkpoint", "Checkpoint Size", "Checkpoint Path"]))
