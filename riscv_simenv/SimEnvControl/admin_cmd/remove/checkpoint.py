import sys

import click
from natsort import natsorted

from ...libsimenv.autocomplete import complete_app_names, complete_chkpt_names
from ...libsimenv.checkpoints_db import get_available_checkpoints_for_app, get_app_checkpoint_dir, \
    get_checkpoint_abspath
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.utils import remove_path, warning


@click.command()
@click.pass_context
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
@click.argument("checkpoint-names", shell_complete=complete_chkpt_names, type=click.STRING, nargs=-1)
@click.option("--remove-all", is_flag=True,
              help="Delete all checkpoint of a given app")
def cmd_rm_checkpoint(ctx, app_name, checkpoint_names, remove_all):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])
    all_checkpoints = get_available_checkpoints_for_app(checkpoints_archive_path, app_name)
    if not all_checkpoints:
        warning(f"app {app_name} has no checkpoint!")
        return

    if remove_all:
        print(f"Removing all checkpoints for app {app_name}...")
        checkpoints_to_remove = list(natsorted(all_checkpoints))
    else:
        checkpoints_to_remove = checkpoint_names

    all_checkpoints = set(all_checkpoints)
    checkpoint_removed = set()
    all_succeed = True
    for checkpoint in checkpoints_to_remove:
        if checkpoint in checkpoint_removed:
            continue
        if checkpoint not in all_checkpoints:
            warning(f"checkpoint {checkpoint} does not exist!")
            continue

        print(f"Removing checkpoint {checkpoint}...")
        succeed, msg = remove_path(get_checkpoint_abspath(checkpoints_archive_path, app_name, checkpoint))
        if not succeed:
            all_succeed = False
            warning(f"fail to remove checkpoint, reason:\n{msg}")
        else:
            checkpoint_removed.add(checkpoint)
    if checkpoint_removed == all_checkpoints:
        app_checkpoints_dir = get_app_checkpoint_dir(checkpoints_archive_path, app_name)
        print(f"Removing the checkpoint dir \"{app_checkpoints_dir}\"")
        succeed, msg = remove_path(app_checkpoints_dir)
        if not succeed:
            all_succeed = False
            warning(f"fail to remove checkpoint dir, reason:\n{msg}")
        else:
            print(f"{app_name} has no checkpoint now.")

    if not all_succeed:
        sys.exit(1)
