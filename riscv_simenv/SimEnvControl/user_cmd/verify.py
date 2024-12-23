import os
import sys

import click

from riscv_simenv.SyscallAnalysis.libsyscall.analyzer.file_usage import FileUsageInfo
from riscv_simenv.SyscallAnalysis.libsyscall.target_path_converter import TargetPathConverter
from ..libsimenv.app_manifest import Manifest_t, verify_manifest_format, verify_manifest_fs_access_format
from ..libsimenv.autocomplete import complete_app_names
from ..libsimenv.manifest_db import load_from_manifest_db, prompt_app_name_suggestion
from ..libsimenv.repo_path import get_repo_components_path
from ..libsimenv.utils import sha256, is_valid_sha256, fatal

warnings = dict()
failures = dict()


def add_warning(pname, warn):
    # type: (str, str) -> None
    if pname not in warnings:
        warnings[pname] = warn


def add_failure(pname, fail):
    # type: (str, str) -> None
    if pname not in failures:
        failures[pname] = fail


def has_read_perm(pname):
    # type: (str) -> bool
    return os.access(pname, os.R_OK)


def has_write_perm(pname):
    # type: (str) -> bool
    def check_dir_writeable(dirname):
        # type: (str) -> bool
        if os.path.isdir(dirname):
            return os.access(dirname, os.W_OK)
        pdir = os.path.dirname(dirname)
        if not pdir:
            pdir = '.'
        return check_dir_writeable(pdir)

    if os.path.exists(pname):
        if os.path.isfile(pname):
            return os.access(pname, os.W_OK)
        else:
            return False
    return check_dir_writeable(pname)


def check_exist(pname):
    # type: (str) -> bool
    if not os.path.exists(pname):
        add_failure(pname, "Path not exist")
        return False
    return True


def check_read(pname):
    # type: (str) -> bool
    if not check_exist(pname):
        return False
    if not has_read_perm(pname):
        add_failure(pname, "Path not readable")
        return False
    return True


def check_write(pname, non_exist_ok):
    # type: (str, bool) -> bool
    if not non_exist_ok and not check_exist(pname):
        return False
    if not has_write_perm(pname):
        add_failure(pname, "Path not writable")
        return False
    return True


def check_isdir(pname):
    # type: (str) -> bool
    if not os.path.isdir(pname):
        add_failure(pname, "Path is not a DIR")
        return False
    return True


def check_isfile(pname):
    # type: (str) -> bool
    if not os.path.isfile(pname):
        add_failure(pname, "Path is not a FILE")
        return False
    return True


def check_hash(pname, expect):
    # type: (str, str) -> bool
    if expect is None:
        return True
    elif expect == 'SKIP':
        add_warning(pname, "SHA256 checking was skipped")
        return True
    elif expect == 'DIR':
        return check_isdir(pname)
    elif is_valid_sha256(expect):
        if not check_exist(pname):
            return False
        if not check_isfile(pname):
            return False
        if not check_read(pname):
            return False
        actual = sha256(pname)
        if actual != expect:
            add_failure(pname, "File hash not match, Expect: %s, Actual: %s" % (expect, actual))
            return False
        return True
    else:
        raise ValueError("Malformed hash: %s" % expect)


def perform_manifest_fsck(manifest, target_sysroot):
    # type: (Manifest_t, str) -> None
    path_converter = TargetPathConverter({"/": os.path.abspath(target_sysroot)})
    for pname, details in manifest['fs_access'].items():
        host_path = path_converter.t2h(pname)
        print("Checking path [%s] <--> [%s]" % (pname, host_path))
        file_usage = FileUsageInfo.build_from_str(details['usage'])
        pre_run_hash = details['hash']['pre-run']

        check_hash(host_path, pre_run_hash)

        if file_usage.has_remove():
            check_write(host_path, non_exist_ok=pre_run_hash is None)

        if file_usage.has_create():
            if not pre_run_hash:
                check_write(host_path, non_exist_ok=pre_run_hash is None)

        if file_usage.has_open_wr() or file_usage.has_open_rw() or file_usage.has_write_data():
            check_write(host_path, non_exist_ok=pre_run_hash is None)

        if file_usage.has_open_rd() or file_usage.has_open_rw() or file_usage.has_read_data():
            if pre_run_hash:
                check_read(host_path)
            elif not file_usage.has_create():
                add_warning(host_path, "Possible corrupt manifest: use a non-exist file?")


@click.command()
@click.pass_context
@click.argument("app-name", shell_complete=complete_app_names, type=click.STRING)
@click.argument("simenv-path", type=click.Path(exists=True, dir_okay=True, file_okay=False))
def cmd_env_verify(ctx, app_name, simenv_path):
    """
    Perform integrity checking for a simenv.
    """
    _, manifest_db_path, _ = get_repo_components_path(ctx.obj["repo_path"])

    print("Begin pre-run file environment checking: %s @ [%s]" % (app_name, simenv_path))
    print()

    try:
        manifest = load_from_manifest_db(app_name, manifest_db_path)
        if "fs_access" not in manifest:
            print(f"Cannot verify {app_name} because its manifest doesn't include FS access information")
            sys.exit(-1)
        verify_manifest_format(manifest, skip_extra_field=True)
        verify_manifest_fs_access_format(manifest)
    except FileNotFoundError:
        print("Fatal: No manifest file for app '%s'" % app_name, file=sys.stderr)
        prompt_app_name_suggestion(app_name, manifest_db_path)
        sys.exit(-1)
    except ValueError as ve:
        fatal("%s has a malformed manifest (%s)" % (app_name, ve))
    else:
        perform_manifest_fsck(manifest, simenv_path)
        print()
        path_with_caveat = set(warnings.keys()).union(failures.keys())
        if path_with_caveat:
            print("Caveat:", file=sys.stderr)
            for p in path_with_caveat:
                print("[%s]" % p, file=sys.stderr)
                if p in failures:
                    print("  - (failed) %s" % failures[p], file=sys.stderr)
                if p in warnings:
                    print("  - (warn) %s" % warnings[p], file=sys.stderr)

        if failures:
            print("Pre-Run FS checking failed.", file=sys.stderr)
            sys.exit(-1)
        else:
            print("Pre-Run FS checking passed%s." % (" with warning" if warnings else ""))


if __name__ == '__main__':
    cmd_env_verify()
