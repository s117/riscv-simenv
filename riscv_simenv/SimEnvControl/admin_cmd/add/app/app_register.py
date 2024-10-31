#!/usr/bin/env python3
import os
import pathlib
import shlex

import click

from ....libsimenv.app_manifest import new_manifest
from ....libsimenv.autocomplete import complete_sysroot_names
from ....libsimenv.manifest_db import save_to_manifest_db, is_app_available
from ....libsimenv.repo_path import get_repo_components_path
from ....libsimenv.sysroots_db import get_pristine_sysroot_dir
from ....libsimenv.utils import fatal, warning


@click.command(
    context_settings={
        "allow_interspersed_args": False,
    }
)
@click.pass_context
@click.option("--app-name", required=True, type=click.STRING,
              help="The name of newly added app.")
@click.option("--sysroot-name", shell_complete=complete_sysroot_names, type=click.STRING,
              help="The pristine sysroot name this app should use.")
@click.option("--proxy-kernel", required=True, type=click.STRING,
              help="The location of proxy kernel in the sysroot.")
@click.option("--init-cwd", required=True,
              help="The location of the launching working directory in the sysroot.")
@click.option("--stdin-redir", required=False, type=click.STRING,
              help="If specified, the location of a file in the sysroot to be STDIN redirected to the app.")
@click.option("--memsize", required=True, type=click.INT,
              help="The amount of RAM this app needs.")
@click.option("--copy-spawn", is_flag=True,
              help="When spawning this simenv, copying all it's input instead of making symbolic link if possible.")
@click.option("--force-overwrite", is_flag=True,
              help="[Danger] Remove existing manifest from the repository before register the new app.")
@click.argument("app-cmds", nargs=-1, type=click.UNPROCESSED)
def cmd_add_app_register(
        ctx,
        app_name,
        sysroot_name,
        proxy_kernel,
        init_cwd,
        stdin_redir,
        memsize,
        copy_spawn,
        force_overwrite,
        app_cmds
):
    """
    Register the app's basic information and creating a manifest entry for it.

    So that the bootstrap Makefile can be created by the 'mkgen' subcommand.
    """
    repo_path = ctx.obj["repo_path"]
    sysroots_archive_path, manifest_db_path, _ = get_repo_components_path(repo_path)
    if stdin_redir is None:
        stdin_redir = ""

    if not pathlib.PurePosixPath(init_cwd).is_absolute():
        fatal("app initial CWD must be an absolute path in the scope of the pristine sysroot.")
    if not pathlib.PurePosixPath(proxy_kernel).is_absolute():
        proxy_kernel = str(
            pathlib.PurePosixPath(init_cwd) / proxy_kernel
        )
    if stdin_redir and not pathlib.PurePosixPath(stdin_redir).is_absolute():
        stdin_redir = str(
            pathlib.PurePosixPath(init_cwd) / stdin_redir
        )

    # 1. Check existing information
    # 1.1 Check manifest
    if is_app_available(app_name, db_path=manifest_db_path):
        if force_overwrite:
            warning(f"exising manifest of {app_name} will be overwritten.")
        else:
            fatal(f"manifest of {app_name} already exist, add flag -f/--force-overwrite to overwrite it.")

    # 1.2 Check sysroot existence
    pristine_sysroot_path = get_pristine_sysroot_dir(sysroots_archive_path, sysroot_name)
    if not os.path.isdir(pristine_sysroot_path):
        fatal(f"cannot find pristine sysroot \"{sysroot_name}\".")

    # 2. Ensure all aux files exists
    # 2.1 check init CWD existence
    init_cwd_path = os.path.join(pristine_sysroot_path, f".{init_cwd}")
    if not os.path.isdir(init_cwd_path):
        fatal(
            f"Cannot locate the init CWD folder '{init_cwd}' inside the pristine sysroot at '{init_cwd_path}'.")

    # 2.2 check STDIN files existence
    if stdin_redir:
        stdin_redir_path = os.path.join(pristine_sysroot_path, f".{stdin_redir}")
        if not os.path.isfile(stdin_redir_path):
            fatal(
                f"Cannot locate the STDIN intput file '{stdin_redir}' inside the pristine sysroot at '{stdin_redir_path}'.")

    # 2.3 check proxy kernel existence
    proxy_kernel_path = os.path.join(pristine_sysroot_path, f".{proxy_kernel}")
    if not os.path.isfile(proxy_kernel_path):
        fatal(
            f"Cannot locate the PK '{proxy_kernel}' inside the the pristine sysroot at '{proxy_kernel_path}'."
        )

    # 3. create a new manifest
    # (skip filling the "fs_access" section, which is to be updated by the "analyze" subcommand)
    print("Creating manifest record for app %s" % app_name)
    app_cmd = " ".join(map(shlex.quote, app_cmds))
    manifest = new_manifest(app_name, proxy_kernel, stdin_redir, app_cmd, init_cwd, memsize, sysroot_name, copy_spawn)
    save_to_manifest_db(app_name, manifest, db_path=manifest_db_path)

    print("Done.")
