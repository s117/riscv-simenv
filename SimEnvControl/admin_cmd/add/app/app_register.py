#!/usr/bin/env python3
import os
import pathlib

import click

from ....libsimenv.app_manifest import new_manifest
from ....libsimenv.autocomplete import complete_sysroot_names
from ....libsimenv.manifest_db import save_to_manifest_db, is_app_available
from ....libsimenv.repo_path import get_repo_components_path
from ....libsimenv.shcmd_utils import extract_stdin_file_from_shcmd
from ....libsimenv.sysroots_db import get_pristine_sysroot_dir
from ....libsimenv.utils import fatal, warning


@click.command()
@click.pass_context
@click.option("-k", "--proxy-kernel", required=True,
              help="The location of proxy kernel in the sysroot directory.")
@click.option("-c", "--app-cmd-file", required=True, type=click.File(),
              help="A single-line text file that contains the command to run this app.")
@click.option("-w", "--app-init-cwd", required=True,
              help="The CWD where you started this app. Use the target path, not host path.")
@click.option("-m", "--memsize", required=True, type=click.INT,
              help="The amount of RAM this app needs.")
@click.option("-f", "--force-overwrite", is_flag=True,
              help="[Danger] Remove existing manifest from the repository before register the new app.")
@click.option("-s", "--sysroot-name", shell_complete=complete_sysroot_names, type=click.STRING,
              help="The pristine sysroot name this app should use.")
@click.option("--copy-spawn", is_flag=True,
              help="When spawning this simenv, copying all it's input instead of making symbolic link if possible.")
@click.argument("app-name", type=click.STRING)
def cmd_add_app_register(
        ctx, proxy_kernel, app_cmd_file, app_init_cwd, memsize, force_overwrite, copy_spawn,
        app_name, sysroot_name,
):
    """
    Register the app's basic information and creating a manifest entry for it.

    So that the bootstrap Makefile can be created by the 'mkgen' subcommand.
    """
    repo_path = ctx.obj["repo_path"]
    sysroots_archive_path, manifest_db_path, _ = get_repo_components_path(repo_path)

    if not pathlib.PurePosixPath(app_init_cwd).is_absolute():
        fatal("app initial CWD must be an absolute path in the scope of the pristine sysroot.")
    if not pathlib.PurePosixPath(proxy_kernel).is_absolute():
        fatal("app Proxy Kernel path must be a absolute path in the scope of the pristine sysroot.")

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
    # 2.1 check STDIN files existence
    app_cmd = app_cmd_file.read().strip()
    stdin_files = extract_stdin_file_from_shcmd(app_cmd)
    if stdin_files is None:
        warning("Fail to parse the commandline to analyze STDIN input file(s).")
    if stdin_files:
        output_lines = []
        for f in stdin_files:
            if pathlib.PurePosixPath(f).is_absolute():
                f_hostpath = os.path.join(pristine_sysroot_path, f".{f}")
            else:
                f_hostpath = os.path.join(pristine_sysroot_path, f".{app_init_cwd}", f)
            if os.path.isfile(f_hostpath):
                output_lines.append(f"   - \"{f}\" (at \"{f_hostpath}\")")
            else:
                fatal(f"Cannot locate the STDIN intput file {f} inside the pristine sysroot at \"{f_hostpath}\"")
        print(
            "Detected following file(s) to be passed as the input via "
            f"STDIN redirection from the app launch command: {app_cmd}"
        )
        print("\n".join(output_lines))
        print("Notice: The path(s) above is shown as 'target path'.")

    # 2.2 check proxy kernel existence
    proxy_kernel_path = os.path.join(pristine_sysroot_path, f".{proxy_kernel}")
    if not os.path.isfile(proxy_kernel_path):
        fatal(
            f"Cannot locate the PK \"{proxy_kernel}\" inside the the pristine sysroot at \"{proxy_kernel_path}\""
        )

    # 3. create a new manifest
    # (skip filling the "fs_access" section, which is to be updated by the "analyze" subcommand)
    print("Creating manifest record for app %s" % app_name)
    manifest = new_manifest(app_name, proxy_kernel, app_cmd, app_init_cwd, memsize, sysroot_name, copy_spawn)
    save_to_manifest_db(app_name, manifest, db_path=manifest_db_path)

    print("Done.")
