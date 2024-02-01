import click

from ...libsimenv.autocomplete import complete_sysroot_names
from ...libsimenv.manifest_db import stat_app_sysroot_dependency
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.sysroots_db import is_sysroot_available, remove_sysroot
from ...libsimenv.utils import fatal, warning


@click.command()
@click.pass_context
@click.argument("sysroot-names", shell_complete=complete_sysroot_names, type=click.STRING, nargs=-1)
@click.option("-f", "--force", is_flag=True,
              help="Skip confirmation if any app still needs the sysroot to be deleted.")
def cmd_rm_sysroot(ctx, sysroot_names, force):
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])

    for sysroot in sysroot_names:
        if not is_sysroot_available(sysroots_archive_path, sysroot):
            fatal(f"Sysroot {sysroot} not exist!")

    sysroots_apps_dep = stat_app_sysroot_dependency(manifest_db_path)

    for sysroot in sysroot_names:
        if sysroot in sysroots_apps_dep:
            warning(f"app(s) {', '.join(sysroots_apps_dep[sysroot])} needs sysroot {sysroot}!")
            if not force:
                if not click.confirm(f"Do you still want to remove {sysroot}?", default=False):
                    continue
        print(f"Removing sysroot {sysroot}...")
        succ, msg = remove_sysroot(sysroots_archive_path, sysroot)
        if not succ:
            fatal(f"Fail to remove existed sysroot, reason:\n{msg}")
