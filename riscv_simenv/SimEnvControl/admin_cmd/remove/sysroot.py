import sys

import click

from ...libsimenv.autocomplete import complete_sysroot_names
from ...libsimenv.manifest_db import stat_app_sysroot_dependency
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.sysroots_db import remove_sysroot, is_sysroot_available
from ...libsimenv.utils import warning


@click.command()
@click.pass_context
@click.argument("sysroot-names", shell_complete=complete_sysroot_names, type=click.STRING, nargs=-1)
@click.option("-f", "--force", is_flag=True,
              help="Skip confirmation if any app still needs the sysroot to be deleted.")
def cmd_rm_sysroot(ctx, sysroot_names, force):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])
    sysroots_apps_dep = stat_app_sysroot_dependency(manifest_db_path)

    sysroot_removed = set()
    all_succeed = True
    for sysroot in sysroot_names:
        if sysroot in sysroot_removed:
            continue
        if not is_sysroot_available(sysroots_archive_path, sysroot):
            warning(f"sysroot {sysroot} does not exist!")
            continue

        if sysroot in sysroots_apps_dep:
            warning(f"app(s) {', '.join(sysroots_apps_dep[sysroot])} needs sysroot {sysroot}!")
            if not force:
                if not click.confirm(f"Do you still want to remove {sysroot}?", default=False):
                    continue
        print(f"Removing sysroot {sysroot}...")
        succeed, msg = remove_sysroot(sysroots_archive_path, sysroot)
        if not succeed:
            all_succeed = False
            warning(f"fail to remove existed sysroot, reason:\n{msg}")
        else:
            sysroot_removed.add(sysroot)

    if not all_succeed:
        sys.exit(1)
