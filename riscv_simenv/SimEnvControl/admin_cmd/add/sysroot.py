#!/usr/bin/env python3

import click

from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.sysroots_db import is_sysroot_available, remove_sysroot, add_sysroot
from ...libsimenv.utils import fatal


@click.command()
@click.pass_context
@click.option("-f", "--force-overwrite", is_flag=True,
              help="[Danger] Remove existing sysroot from the repository before importing the new sysroot.")
@click.argument("sysroot-name")
@click.argument("sysroot-path", type=click.Path(exists=True, dir_okay=True, file_okay=False))
def cmd_add_sysroot(ctx, sysroot_name, sysroot_path, force_overwrite):
    """
    Import a pristine sysroot.
    """
    sysroots_archive_path, _, _ = get_repo_components_path(ctx.obj["repo_path"])

    if is_sysroot_available(sysroots_archive_path, sysroot_name):
        if force_overwrite:
            succ, msg = remove_sysroot(sysroots_archive_path, sysroot_name)
            if not succ:
                fatal(f"Fail to remove existed sysroot, reason:\n{msg}")
        else:
            fatal("Sysroot name %s already exist." % sysroot_name)

    print(f"Importing pristine sysroot {sysroot_name} from \"{sysroot_path}\"")
    succ, msg = add_sysroot(sysroots_archive_path, sysroot_name, sysroot_path)
    if not succ:
        fatal(f"Fail to add new sysroot, reason:\n{msg}")

    print("Done.")
