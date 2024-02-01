import click

from ...libsimenv.autocomplete import complete_app_names, complete_chkpt_names
from ...libsimenv.checkpoints_db import get_available_checkpoints_for_app, get_app_ckpt_dir, get_checkpoint_abspath, \
    is_app_have_checkpoints
from ...libsimenv.manifest_db import is_app_available
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.utils import fatal, remove_path


@click.command()
@click.pass_context
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
@click.argument("checkpoint-names", shell_complete=complete_chkpt_names, type=click.STRING, nargs=-1)
@click.option("--remove-all", is_flag=True,
              help="Delete all checkpoint of a given app")
def cmd_rm_checkpoint(ctx, app_name, checkpoint_names, remove_all):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])
    if not is_app_available(app_name, manifest_db_path):
        fatal(f"app {app_name} not exist!")

    app_checkpoint_list = get_available_checkpoints_for_app(checkpoints_archive_path, app_name)
    app_checkpoints_dir = get_app_ckpt_dir(checkpoints_archive_path, app_name)

    if not is_app_have_checkpoints(checkpoints_archive_path, app_name):
        fatal(f"app {app_name} has no checkpoint!")

    if remove_all:
        print(f"Removing all checkpoints for app {app_name}...")
        checkpoint_names = app_checkpoint_list

    app_checkpoint_list = set(app_checkpoint_list)
    for checkpoint in checkpoint_names:
        if checkpoint not in app_checkpoint_list:
            fatal(f"checkpoint {checkpoint} does not exist!")

    checkpoint_removed = set()
    for checkpoint in checkpoint_names:
        if checkpoint in checkpoint_removed:
            continue
        print(f"Removing checkpoint {checkpoint}...")
        succ, msg = remove_path(get_checkpoint_abspath(checkpoints_archive_path, app_name, checkpoint))
        if not succ:
            fatal(f"Fail to remove checkpoint, reason:\n{msg}")
        checkpoint_removed.add(checkpoint)
    if app_checkpoint_list and checkpoint_removed == app_checkpoint_list:
        print(f"Removing the checkpoint dir \"{app_checkpoints_dir}\"")
        succ, msg = remove_path(app_checkpoints_dir)
        if not succ:
            fatal(f"Fail to remove checkpoint dir, reason:\n{msg}")
        print(f"{app_name} has no checkpoint now.")
