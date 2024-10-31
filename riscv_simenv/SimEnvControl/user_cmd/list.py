import os
import sys

import click
from natsort import natsorted

from ..libsimenv.autocomplete import complete_app_names
from ..libsimenv.checkpoints_db import get_available_checkpoints_for_app
from ..libsimenv.manifest_db import get_avail_apps_in_db, prompt_app_name_suggestion, \
    is_app_available
from ..libsimenv.repo_path import get_repo_components_path


def prompt_avail_app_name(manifest_db_path, checkpoint_db_path):
    # type: (str, str) -> None
    all_available_app_names = natsorted(get_avail_apps_in_db(manifest_db_path))
    if all_available_app_names:
        print("All available app:")
        for app in all_available_app_names:
            app_chkpts = get_available_checkpoints_for_app(checkpoint_db_path, app)
            n_chkpts = len(app_chkpts)
            print("\t%s (%d %s available)" % (app, n_chkpts, "checkpoints" if n_chkpts > 1 else "checkpoint"))
        print(
            "Run `%s list [app names]` to see the list of available checkpoint(s)." % os.path.basename(sys.argv[0])
        )
    else:
        print("No record in the manifest DB [%s]" % manifest_db_path, file=sys.stderr)
        print("To add an app to the repository, use `riscv-app-repo`", file=sys.stderr)


def prompt_apps_checkpoint(app_names, checkpoints_db_path):
    # type: (str, str) -> None
    for app in app_names:
        app_chkpts = get_available_checkpoints_for_app(checkpoints_db_path, app)
        if app_chkpts:
            print("Available checkpoints for '%s':" % app)
            for app_chkpt in natsorted(app_chkpts):
                print("   %s" % app_chkpt)
            print()
        else:
            print("No checkpoint available for '%s'." % app)
            print()


@click.command()
@click.pass_context
@click.argument("app-names", type=click.STRING, nargs=-1, shell_complete=complete_app_names)
@click.option("-b", "--brief", is_flag=True,
              help="Brief output, useful for script parsing.")
def cmd_list(ctx, app_names, brief):
    """
    List available apps and checkpoints in the SimEnv repository.
    """
    _, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])

    for app in app_names:
        if not is_app_available(app, manifest_db_path):
            print("App '%s' doesn't exist." % app, file=sys.stderr)
            prompt_app_name_suggestion(app, manifest_db_path)
            exit(-1)

    if not app_names:
        if brief:
            for app in natsorted(get_avail_apps_in_db(manifest_db_path)):
                print(app)
        else:
            prompt_avail_app_name(manifest_db_path, checkpoints_archive_path)
    else:
        if brief:
            for app in app_names:
                for app_chkpt in natsorted(get_available_checkpoints_for_app(checkpoints_archive_path, app)):
                    print(app_chkpt)
        else:
            prompt_apps_checkpoint(app_names, checkpoints_archive_path)


if __name__ == '__main__':
    cmd_list()
