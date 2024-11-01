import sys

import click

from ...libsimenv.autocomplete import complete_app_names
from ...libsimenv.checkpoints_db import get_available_checkpoints_for_app
from ...libsimenv.manifest_db import is_app_available, get_manifest_path
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.utils import warning, remove_path


@click.command()
@click.pass_context
@click.argument("app-names", shell_complete=complete_app_names, type=click.STRING, nargs=-1)
@click.option("-f", "--force", is_flag=True,
              help="Skip confirmation if there are any checkpoints belong to the sysroot to be deleted.")
def cmd_rm_manifest(ctx, app_names, force):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])

    app_removed = set()
    all_succeed = True
    for app in app_names:
        if app in app_removed:
            continue
        if not is_app_available(app, manifest_db_path):
            warning(f"app {app} does not exist!")
            continue

        app_checkpoints = get_available_checkpoints_for_app(checkpoints_archive_path, app)
        if app_checkpoints:
            app_checkpoints_str = '\n'.join(app_checkpoints)
            warning(f"{app} has those checkpoints:\n{app_checkpoints_str}")
            if not force:
                if not click.confirm(f"Do you still want to remove {app}?", default=False):
                    continue
        print(f"Removing manifest for {app}...")
        succeed, msg = remove_path(get_manifest_path(manifest_db_path, app))
        if not succeed:
            all_succeed = False
            warning(f"fail to remove the manifest, reason:\n{msg}")
        else:
            app_removed.add(app)

    if not all_succeed:
        sys.exit(1)
