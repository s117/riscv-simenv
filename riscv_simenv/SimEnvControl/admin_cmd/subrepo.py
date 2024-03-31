#!/usr/bin/env python3
import os.path
import shutil
import sys
from typing import Tuple

import click

from ..libsimenv.app_manifest import verify_manifest_format, Manifest_t
from ..libsimenv.autocomplete import complete_app_names
from ..libsimenv.checkpoints_db import get_app_ckpt_dir
from ..libsimenv.manifest_db import is_app_available, prompt_app_name_suggestion, load_from_manifest_db, \
    get_manifest_path
from ..libsimenv.repo_path import create_repo, get_manifests_dir, get_checkpoints_dir, get_sysroots_dir, \
    get_repo_components_path
from ..libsimenv.sysroots_db import get_pristine_sysroot_dir
from ..libsimenv.utils import warning


def discover_files(manifest_db_path, checkpoints_archive_path, sysroots_archive_path, app_name):
    # type: (str, str, str, str) -> Tuple[Manifest_t, str, str, str]
    if not is_app_available(app_name, manifest_db_path):
        print("Fatal: No manifest file for app '%s'" % app_name, file=sys.stderr)
        prompt_app_name_suggestion(app_name, manifest_db_path)
        sys.exit(-1)

    manifest = load_from_manifest_db(app_name, manifest_db_path)
    verify_manifest_format(manifest, skip_extra_field=True)

    manifest_path = get_manifest_path(manifest_db_path, app_name)
    sysroot_dir = get_pristine_sysroot_dir(sysroots_archive_path, manifest["app_pristine_sysroot"])
    checkpoints_dir = get_app_ckpt_dir(checkpoints_archive_path, app_name)

    return manifest, manifest_path, sysroot_dir, checkpoints_dir


def xcopy(src_path, dst_path):
    # type: (str, str) -> None
    if os.path.isdir(src_path):
        print("Copying dir %s -> %s" % (src_path, dst_path))
        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
    else:
        print("Copying file %s -> %s" % (src_path, dst_path))
        shutil.copy2(src_path, dst_path)


@click.command()
@click.pass_context
@click.option("-c", "--checkpoints", is_flag=True,
              help="Include checkpoints.")
@click.argument("new-repo-root", nargs=1, type=click.Path(exists=False))
@click.argument("app-names", nargs=-1, type=click.STRING, shell_complete=complete_app_names)
def cmd_sub_repo(ctx, checkpoints, new_repo_root, app_names):
    """
    Spawn a sub-repository with the selected apps.
    """
    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])

    app_info_list = dict()
    for app_name in app_names:
        app_info_list[app_name] = discover_files(
            manifest_db_path,
            checkpoints_archive_path,
            sysroots_archive_path,
            app_name
        )

    app_copy_list = dict()
    for app_name in app_info_list.keys():
        app_manifest, app_manifest_path, app_sysroot_dir, app_ckpt_dir = app_info_list[app_name]
        if not os.path.isfile(app_manifest_path):
            warning("App %s not copied: Manifest file %s doesn't exist" % (app_name, app_manifest_path))
            continue
        if not os.path.isdir(app_sysroot_dir):
            warning("App %s not copied: Sysroot dir %s doesn't exist" % (app_name, app_sysroot_dir))
            continue
        if checkpoints and not os.path.isdir(app_ckpt_dir):
            warning("App %s doesn't has a checkpoint dir: %s" % (app_name, app_sysroot_dir))
        app_copy_list[app_name] = app_info_list[app_name]

    if app_copy_list:
        create_repo(new_repo_root)
        for app_name in app_copy_list.keys():
            print("Copying app %s ..." % app_name)
            app_manifest, app_manifest_path, app_sysroot_dir, app_ckpt_dir = app_info_list[app_name]

            new_manifest_path = get_manifest_path(
                get_manifests_dir(new_repo_root),
                app_name
            )
            new_sysroot_dir = get_pristine_sysroot_dir(
                get_sysroots_dir(new_repo_root),
                app_manifest["app_pristine_sysroot"]
            )
            new_ckpt_dir = get_app_ckpt_dir(
                get_checkpoints_dir(new_repo_root),
                app_name
            )

            if not os.path.exists(new_manifest_path):
                xcopy(app_manifest_path, new_manifest_path)
            if not os.path.exists(new_sysroot_dir):
                xcopy(app_sysroot_dir, new_sysroot_dir)
            if checkpoints and os.path.isdir(app_ckpt_dir) and not os.path.exists(new_ckpt_dir):
                xcopy(app_ckpt_dir, new_ckpt_dir)


if __name__ == '__main__':
    cmd_sub_repo()
