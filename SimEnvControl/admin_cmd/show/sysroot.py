import click
from natsort import natsorted
from tabulate import tabulate

from ...libsimenv.manifest_db import stat_app_sysroot_dependency
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.sysroots_db import get_all_sysroots, get_pristine_sysroot_dir
from ...libsimenv.utils import get_size_str


@click.command()
@click.pass_context
def cmd_show_sysroot(ctx):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])
    sysroots = get_all_sysroots(sysroots_db_path=sysroots_archive_path)
    sysroots_apps_dep = stat_app_sysroot_dependency(manifest_db_path)

    row = []
    for sysroot in natsorted(sysroots):
        sysroot_path = get_pristine_sysroot_dir(sysroots_archive_path, sysroot)
        if sysroot in sysroots_apps_dep:
            dep = ", ".join(sysroots_apps_dep[sysroot])
        else:
            dep = '-'
        sysroot_size = get_size_str(sysroot_path)
        row.append(
            [sysroot, sysroot_size, dep, sysroot_path]
        )
    print(tabulate(row, headers=["Sysroot name", "Size", "Used by app", "Sysroot location"]))
