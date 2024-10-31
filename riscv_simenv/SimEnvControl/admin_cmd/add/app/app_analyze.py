#!/usr/bin/env python3
import os
import sys

import click

from ....libsimenv.app_manifest import update_manifest_fs_access, update_manifest_instret, verify_manifest_format
from ....libsimenv.autocomplete import complete_app_names
from ....libsimenv.manifest_db import save_to_manifest_db, load_from_manifest_db, prompt_app_name_suggestion
from ....libsimenv.repo_path import get_repo_components_path
from ....libsimenv.sysroots_db import get_pristine_sysroot_dir
from ....libsimenv.utils import fatal


@click.command()
@click.pass_context
@click.option("-s", "--syscall-trace", required=True, type=click.File(),
              help="The FESVR syscall trace file.")
@click.option("-f", "--final-state-json", required=False, type=click.Path(),
              help="The FESVR final state registers dump.")
@click.option("-d", "--post-sim-sysroot-path", required=True,
              type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help="The path to the sysroot after the app has run.")
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
def cmd_add_app_analyze(ctx, syscall_trace, final_state_json, post_sim_sysroot_path, app_name):
    """
    Analyze an app for how to create SimEnv.
    """
    sysroots_archive_path, manifest_db_path, _ = get_repo_components_path(ctx.obj["repo_path"])

    try:
        manifest = load_from_manifest_db(app_name, manifest_db_path)
        verify_manifest_format(manifest, skip_extra_field=True)
    except FileNotFoundError:
        print("Fatal: No manifest file for app '%s'. Did you bootstrap it first?" % app_name, file=sys.stderr)
        prompt_app_name_suggestion(app_name, manifest_db_path)
        sys.exit(-1)
    except ValueError as ve:
        fatal("%s has a malformed manifest (%s)" % (app_name, ve))
    else:
        print("Updating manifest for app %s" % app_name)

        pristine_sysroot_path = get_pristine_sysroot_dir(sysroots_archive_path, manifest["app_pristine_sysroot"])
        if not os.path.isdir(pristine_sysroot_path):
            fatal("App's pristine sysroot [%s] does not exist" % pristine_sysroot_path)

        new_manifest = update_manifest_fs_access(manifest, pristine_sysroot_path, post_sim_sysroot_path, syscall_trace)
        if os.path.exists(final_state_json):
            with open(final_state_json, "r") as fp_final_state_json:
                new_manifest = update_manifest_instret(new_manifest, fp_final_state_json)
        save_to_manifest_db(app_name, new_manifest, db_path=manifest_db_path)
        print("Done.")
