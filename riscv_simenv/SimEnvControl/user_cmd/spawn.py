import os
import shutil
import stat
import sys

import click

from riscv_simenv.SyscallAnalysis.libsyscall.analyzer.file_usage import FileUsageInfo
from riscv_simenv.SyscallAnalysis.libsyscall.target_path_converter import TargetPathConverter
from ..libsimenv.app_manifest import verify_manifest_format, Manifest_t
from ..libsimenv.autocomplete import complete_app_names
from ..libsimenv.manifest_db import load_from_manifest_db, prompt_app_name_suggestion
from ..libsimenv.repo_path import get_repo_components_path
from ..libsimenv.sysroots_db import get_pristine_sysroot_dir, set_dir_writeable_u
from ..libsimenv.utils import fatal, remove_path


def usage_must_copy_spawn(usage):
    # type: (FileUsageInfo) -> bool
    """
    Check whether a file must be copy-spawn based or its usage.
    Return True if the file must be copy-spawned, False otherwise.
    """
    return (
            usage.has_write_data() or
            usage.has_open_rw() or
            usage.has_open_wr() or
            usage.has_stat()
    )


def usage_must_writable(usage):
    # type: (FileUsageInfo) -> bool
    """
    Check whether the spawn file must be writable by the RISCV app/
    Return True if the file must be writable, False otherwise.
    """
    return (
            usage.has_write_data() or
            usage.has_open_rw() or
            usage.has_open_wr() or
            usage.has_remove() or
            usage.has_create()
    )


def spawn_file(src, dst, usage, copy_mode):
    # type: (str, str, FileUsageInfo, bool) -> bool
    """
    Spawns a new file from src to dst.

    Return True if file was spawn as a symbolic link.
    Return False if file was spawn as a copy of origin.
    """
    assert dst
    assert src
    par_dir = os.path.dirname(dst)
    spawn_dir(par_dir)
    if os.path.isdir(dst):
        fatal("Malformed manifest input: %s implies both input file and dir" % dst)
    if copy_mode or usage_must_copy_spawn(usage):
        shutil.copy2(src, dst, follow_symlinks=False)
        print("Copy %s -> %s" % (src, dst))
        return False
    else:
        os.symlink(src, dst)
        print("Symlink %s -> %s" % (src, dst))
        return True


def spawn_dir(dpath):
    # type: (str) -> None
    if dpath:
        if os.path.isfile(dpath):
            fatal("Malformed manifest input: %s implies both dir and input" % dpath)
        os.makedirs(dpath, exist_ok=True)
        print("Mkdir %s" % dpath)


def do_selective_spawn(app_pristine_sysroot_path, dest_dir, manifest, copy_mode):
    # type: (str, str, Manifest_t, bool) -> None
    pristine_path_converter = TargetPathConverter({"/": os.path.abspath(app_pristine_sysroot_path)})
    spawn_path_converter = TargetPathConverter({"/": os.path.abspath(dest_dir)})

    os.makedirs(dest_dir, exist_ok=True)

    copy_mode = copy_mode or manifest["app_spawn_mode"] == "copy"

    for pname, details in manifest['fs_access'].items():
        pre_run_hash = details['hash']['pre-run']
        file_usage = FileUsageInfo.build_from_str(details['usage'])
        if pre_run_hash:
            if pre_run_hash == 'DIR':
                spawn_dir(spawn_path_converter.t2h(pname))
            else:
                file_src = pristine_path_converter.t2h(pname)
                file_dst = spawn_path_converter.t2h(pname)
                spawn_file(file_src, file_dst, file_usage, copy_mode)
                if usage_must_writable(file_usage):
                    # ensure the write permission is present when needed by the app
                    if not os.access(file_dst, os.W_OK):
                        st = os.stat(file_dst)
                        os.chmod(file_dst, st.st_mode | stat.S_IWRITE)


def do_raw_dump_spawn(sysroot_path, dest_dir):
    # type: (str, str) -> None
    shutil.copytree(sysroot_path, dest_dir, symlinks=False)
    set_dir_writeable_u(dest_dir)


@click.command()
@click.pass_context
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
@click.argument("dest-dir", type=click.Path())
@click.option("-f", "--force", is_flag=True,
              help="If path [new-dir] already exist, remove it before create the new simenv.")
@click.option("--raw", is_flag=True,
              help="Directly copy the entire pristine sysroot to dest-dir "
                   "(instead of selectively spawn only the files specified in the manifest).")
@click.option("-c", "--copy-mode", is_flag=True,
              help="Copy the file to the new simenv, regardless the spawn mode given by the manifest.")
def cmd_env_spawn(ctx, app_name, dest_dir, raw, force, copy_mode):
    """
    Spawn a simenv.
    """

    sysroots_archive_path, manifest_db_path, _ = get_repo_components_path(ctx.obj["repo_path"])

    if os.path.exists(dest_dir):
        if force:
            succ, msg = remove_path(dest_dir)
            if not succ:
                fatal("Fail to remove \"%s\", reason:\n%s" % (dest_dir, msg))
        else:
            fatal("Path \"%s\" already exist, new simenv not spawned." % dest_dir)

    try:
        manifest = load_from_manifest_db(app_name, manifest_db_path)
        verify_manifest_format(manifest, skip_fs_access=raw)
    except FileNotFoundError:
        print("Fatal: No manifest file for app '%s'" % app_name, file=sys.stderr)
        prompt_app_name_suggestion(app_name, manifest_db_path)
        sys.exit(-1)
    except ValueError as ve:
        fatal("%s has a malformed manifest (%s)" % (app_name, ve))
    else:
        app_pristine_sysroot_name = manifest["app_pristine_sysroot"]
        app_pristine_sysroot_path = get_pristine_sysroot_dir(sysroots_archive_path, app_pristine_sysroot_name)
        if not os.path.isdir(app_pristine_sysroot_path):
            fatal("App's pristine sysroot [%s] does not exist" % app_pristine_sysroot_path)

        print("Spawning simenv for app %s" % app_name)
        if raw:
            do_raw_dump_spawn(app_pristine_sysroot_path, dest_dir)
        else:
            do_selective_spawn(app_pristine_sysroot_path, dest_dir, manifest, copy_mode)


if __name__ == '__main__':
    cmd_env_spawn()
