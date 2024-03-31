import os
import sys

import click

from ..libsimenv.app_manifest import Manifest_t, verify_manifest_format
from ..libsimenv.autocomplete import complete_chkpt_names, complete_app_names
from ..libsimenv.checkpoints_db import check_checkpoint_exist, get_checkpoint_abspath
from ..libsimenv.manifest_db import load_from_manifest_db, prompt_app_name_suggestion
from ..libsimenv.repo_path import get_repo_components_path
from ..libsimenv.shcmd_utils import add_base_to_stdin_file_in_shcmd
from ..libsimenv.template_manager import instantiate_template
from ..libsimenv.utils import fatal

DEFAULT_CHECKPOINT_LOAD_FLAG = "-f"
DEFAULT_SIMULATOR = "spike"
BOOTSTRAP_SIMULATOR = "spike"


def mkgen_bootstrap(manifest, repo_path):
    # type: (Manifest_t, str) -> str
    actual_app_cmd = add_base_to_stdin_file_in_shcmd(manifest["app_cmd"], "$(SIMENV_SYSROOT)", "$(APP_INIT_CWD)")
    bootstrap_recipes = instantiate_template(
        "bootstrap-make-recipes",
        repo_path=repo_path
    )
    generated_makefile = instantiate_template(
        "Makefile",
        app_name=manifest["app_name"],
        app_cmd=actual_app_cmd,
        app_init_cwd=manifest["app_init_cwd"],
        app_memsize=manifest["app_memsize"],
        sim_cmd=BOOTSTRAP_SIMULATOR,
        sim_flags="",
        fesvr_flags="",
        app_pk_path=manifest["app_proxy_kernel"],
        pk_flags="",
        extra_recipes=bootstrap_recipes
    )
    return generated_makefile


def mkgen_normal(manifest, checkpoint_to_load_path):
    # type: (Manifest_t, str) -> str
    actual_app_cmd = add_base_to_stdin_file_in_shcmd(manifest["app_cmd"], "$(SIMENV_SYSROOT)", "$(APP_INIT_CWD)")
    actual_ckpt_flag = os.getenv("RISCV_SIMENV_SIM_FLAG_LDCKPT", default=DEFAULT_CHECKPOINT_LOAD_FLAG)
    actual_sim = os.getenv("RISCV_SIMENV_SIM_CMD", default=DEFAULT_SIMULATOR)

    if checkpoint_to_load_path:
        sim_flags = f"{actual_ckpt_flag}\"{checkpoint_to_load_path}\""
    else:
        sim_flags = ""
    generated_makefile = instantiate_template(
        "Makefile",
        app_name=manifest["app_name"],
        app_cmd=actual_app_cmd,
        app_init_cwd=manifest["app_init_cwd"],
        app_memsize=manifest["app_memsize"],
        sim_cmd=actual_sim,
        sim_flags=sim_flags,
        fesvr_flags="",
        app_pk_path=manifest["app_proxy_kernel"],
        pk_flags="",
        extra_targets="",
        extra_recipes=""
    )
    return generated_makefile


@click.command()
@click.pass_context
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
@click.option("-f", "--checkpoint", shell_complete=complete_chkpt_names,
              help="If give and exist, the generated makefile will load the given checkpoint by default.")
@click.option("--bootstrap", is_flag=True,
              help="Generate a bootstrap Makefile (will override all other options).")
def cmd_mkgen(ctx, app_name, checkpoint, bootstrap):
    """
    Generate a Makefile at the current folder that can launch an app simulation.
    """

    _, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])

    try:
        manifest = load_from_manifest_db(app_name, manifest_db_path)
        verify_manifest_format(manifest, skip_extra_field=True)
        if checkpoint and not check_checkpoint_exist(checkpoints_archive_path, app_name, checkpoint):
            fatal("App %s doesn't have checkpoint %s" % (app_name, checkpoint))
    except FileNotFoundError:
        print("Fatal: No manifest file for app '%s'" % app_name, file=sys.stderr)
        prompt_app_name_suggestion(app_name, manifest_db_path)
        sys.exit(-1)
    except ValueError as ve:
        fatal("%s has a malformed manifest (%s)" % (app_name, ve))
    else:
        print(
            "Generating makefile for app %s%s" % (
                app_name, ", checkpoint %s" % checkpoint if checkpoint else "")
        )
        if bootstrap:
            generated_makefile = mkgen_bootstrap(manifest, ctx.obj["repo_path"])
        else:
            checkpoint_path = get_checkpoint_abspath(checkpoints_archive_path, app_name,
                                                     checkpoint) if checkpoint else None
            generated_makefile = mkgen_normal(manifest, checkpoint_path)

        with open("Makefile", "w") as fp:
            fp.write(generated_makefile)
        print("Done.")


if __name__ == '__main__':
    cmd_mkgen()
