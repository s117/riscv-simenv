import copy
import os
import pathlib
from typing import Dict, Union, TextIO, Set, Tuple

from SyscallAnalysis.libsyscall.analyzer.file_usage import FileUsageInfo, stat_file_usage
from SyscallAnalysis.libsyscall.analyzer.syscall_trace_constructor import SyscallTraceConstructor
from SyscallAnalysis.libsyscall.syscalls.syscall import GenericPath
from .content_manager import ContentManager
from .shcmd_utils import extract_stdin_file_from_shcmd
from .utils import fatal, warning, is_valid_sha256

Manifest_t = Dict[str, Union[str, Dict]]


def new_manifest(app_name, proxy_kernel, app_cmd, app_init_cwd, memsize, sysroot_name, copy_spawn):
    # type: (str, str, str, str, int, str, bool) -> Manifest_t
    manifest = dict()
    manifest["app_name"] = app_name
    manifest["app_proxy_kernel"] = proxy_kernel
    manifest["app_cmd"] = app_cmd
    manifest["app_init_cwd"] = app_init_cwd
    manifest["app_memsize"] = memsize
    manifest["app_pristine_sysroot"] = sysroot_name
    if copy_spawn:
        manifest["app_spawn_mode"] = "copy"
    else:
        manifest["app_spawn_mode"] = "link"
    return manifest


def update_manifest_fs_access(existing_manifest, pristine_sysroot_path, post_sim_sysroot_path, strace_fp):
    # type: (Manifest_t, str, str, TextIO) -> Manifest_t
    verify_manifest_format(existing_manifest, skip_fs_access=True)

    manifest = copy.deepcopy(existing_manifest)
    app_cmd = manifest["app_cmd"]
    app_init_cwd = manifest["app_init_cwd"]
    app_proxy_kernel = manifest["app_proxy_kernel"]

    content_manager = ContentManager(os.path.abspath(pristine_sysroot_path), os.path.abspath(post_sim_sysroot_path))

    fs_access_dict = dict()
    manifest["fs_access"] = fs_access_dict

    def manifest_add_fs_access_entry(_path, _file_usage):
        # type: (str, FileUsageInfo) -> None
        assert pathlib.PurePosixPath(_path).is_absolute()

        pre_run_hash = content_manager.get_pristine_hash(_path)
        post_run_hash = content_manager.get_post_sim_hash(_path)

        if not pre_run_hash and not _file_usage.has_create():
            raise ValueError(
                "The strace shows the app used file/dir [%s] without creation, but it is not in the pristine sysroot." %
                _path
            )
        elif not post_run_hash and not _file_usage.has_remove():
            raise ValueError(
                "The strace shows the app used file/dir [%s] without removal, but it is not in the post-sim sysroot." %
                _path
            )
        elif pre_run_hash and post_run_hash and pre_run_hash != post_run_hash and not _file_usage.has_write_data():
            raise ValueError(
                "The strace shows app used file/dir [%s] without modification, but its hash changed after simulation" %
                _path
            )

        if _path in fs_access_dict:
            # merge if path entry already added
            stored_usage = FileUsageInfo.build_from_str(fs_access_dict[_path]["usage"])
            new_usage = stored_usage | _file_usage
            fs_access_dict[_path]["usage"] = str(new_usage)
        else:
            # create a new path entry
            fs_access_dict[_path] = {
                "usage": str(_file_usage),
                "hash": {
                    "pre-run": pre_run_hash,
                    "post-run": post_run_hash
                }
            }

    # 1. Record the files accessed by the RISCV process
    # 1.1 Analyze the syscall trace collected from the bootstrap run
    trace_analyzer = SyscallTraceConstructor(app_init_cwd)
    trace_analyzer.parse_strace_str(strace_fp.read())
    file_usage_info = stat_file_usage(trace_analyzer.syscalls)
    # 2.2 Record the analysis result (file access pattern of the RISCV process)
    for path, file_usage in file_usage_info.items():
        manifest_add_fs_access_entry(path, file_usage)

    # 2. Record the input files passed via STDIN redirection
    # 2.1 Parse the app command
    stdin_files = extract_stdin_file_from_shcmd(app_cmd)
    if stdin_files is None:
        warning("Fail to parse the commandline for analyzing STDIN input file(s).")
        stdin_files = []
    elif stdin_files:
        print(f"Recognized following file(s) passed as the input via stdin from the app run command [{app_cmd}]")
        for f in stdin_files:
            print(f"   - {f}")
        print("Notice: The path(s) above will be dealt as 'target path'.")
    # 2.2 Record input files passed as STDIN
    readonly_usage = FileUsageInfo.build_from_str("FUSE_OPEN_RD | FUSE_READ_DATA")
    for path in stdin_files:
        stdin_file_target_path = GenericPath(app_init_cwd, path).abspath()
        if not content_manager.locate_pristine_file(stdin_file_target_path):
            fatal(
                "Cmdline analysis shows the app will use file [%s] via stdin redirect, "
                "but it is not found in the pristine sysroot [%s]" %
                (stdin_file_target_path, content_manager.get_pristine_sysroot())
            )
        manifest_add_fs_access_entry(stdin_file_target_path, readonly_usage)
        print(f"Added stdin redirect source [{path}] to manifest")

    # 3. Add proxy kernel (if not already added)
    if not content_manager.locate_pristine_file(app_proxy_kernel):
        fatal(
            f"Cannot find the proxy kernel inside the pristine sysroot at \"{app_proxy_kernel}\"."
        )
    manifest_add_fs_access_entry(app_proxy_kernel, readonly_usage)
    print(f"Added proxy kernel [{app_proxy_kernel}] to manifest")

    verify_manifest_format(manifest, skip_fs_access=False)

    return manifest


def _ensure_exist(manifest, key):
    # type: (Manifest_t, str) -> None
    if key not in manifest:
        raise ValueError("Manifest doesn't has the required field: %s" % key)


def _ensure_int_type(manifest, key):
    # type: (Manifest_t, str) -> None
    _ensure_exist(manifest, key)
    try:
        int(manifest[key])
    except ValueError:
        raise ValueError("Field [%s] in the manifest is not an integer: %s" % (key, manifest[key]))


def _ensure_str_type(manifest, key):
    # type: (Manifest_t, str) -> None
    _ensure_exist(manifest, key)
    if not isinstance(manifest[key], str):
        raise ValueError("Field [%s] in the manifest is not a string: %s" % (key, manifest[key]))


def _ensure_dict_type(manifest, key):
    # type: (Manifest_t, str) -> None
    _ensure_exist(manifest, key)
    if not isinstance(manifest[key], dict):
        raise ValueError("Field [%s] in the manifest is not a map: %s" % (key, manifest[key]))


def _ensure_in_set(manifest, key, valid_set):
    # type: (Manifest_t, str, Set) -> None
    _ensure_exist(manifest, key)
    if manifest[key] not in valid_set:
        raise ValueError(
            "Field [%s] in the manifest can only be one of the following value: %s" % (key, valid_set))


def verify_manifest_fs_access_format(manifest):
    # type: (Manifest_t) -> None
    _ensure_dict_type(manifest, "fs_access")
    for fpath, detail in manifest["fs_access"].items():
        if not pathlib.PurePosixPath(fpath).is_absolute():
            raise ValueError("In manifest['fs_access'], the key %s is not a Posix absolute path." % fpath)
        if "usage" not in detail:
            raise ValueError("Manifest['fs_access']['%s']['usage'] doesn't exist." % fpath)
        else:
            try:
                FileUsageInfo.build_from_str(detail["usage"])
            except Exception:
                raise ValueError("Manifest['fs_access']['%s']['usage'] is invalid." % fpath)
        if "hash" not in detail:
            raise ValueError("Manifest['fs_access']['%s']['hash'] doesn't exist." % fpath)
        elif not isinstance(detail['hash'], dict):
            raise ValueError("Manifest['fs_access']['%s']['hash'] must be a map." % fpath)
        else:
            if "pre-run" not in detail['hash']:
                raise ValueError("Manifest['fs_access']['%s']['hash']['pre-run'] doesn't exist." % fpath)
            if detail['hash']['pre-run'] is None:
                pass
            elif not isinstance(detail['hash']['pre-run'], str):
                raise ValueError("Manifest['fs_access']['%s']['hash']['pre-run'] is invalid." % fpath)
            elif detail['hash']['pre-run'] not in {"DIR", "SKIP"} and not is_valid_sha256(
                    detail['hash']['pre-run']):
                raise ValueError("Manifest['fs_access']['%s']['hash']['pre-run'] is invalid." % fpath)

            if "post-run" not in detail['hash']:
                raise ValueError("Manifest['fs_access']['%s']['hash']['post-run'] doesn't exist." % fpath)
            elif detail['hash']['post-run'] is None:
                pass
            elif detail['hash']['post-run'] is not None and not isinstance(detail['hash']['post-run'], str):
                raise ValueError("Manifest['fs_access']['%s']['hash']['post-run'] is invalid." % fpath)
            elif detail['hash']['post-run'] not in {"DIR", "SKIP"} and not is_valid_sha256(
                    detail['hash']['post-run']):
                raise ValueError("Manifest['fs_access']['%s']['hash']['post-run'] is invalid." % fpath)


def verify_manifest_format(manifest, skip_fs_access=False):
    # type: (Manifest_t, bool) -> bool
    _ensure_str_type(manifest, "app_name")
    _ensure_str_type(manifest, "app_proxy_kernel")
    _ensure_str_type(manifest, "app_cmd")
    _ensure_str_type(manifest, "app_init_cwd")
    _ensure_str_type(manifest, "app_pristine_sysroot")
    _ensure_int_type(manifest, "app_memsize")
    _ensure_in_set(manifest, "app_spawn_mode", {"copy", "link"})

    if not skip_fs_access:
        verify_manifest_fs_access_format(manifest)

    return True


def manifest_status(manifest):
    # type: (Manifest_t) -> Tuple[bool, bool]
    try:
        verify_manifest_format(manifest, skip_fs_access=True)
    except ValueError:
        base_ok = False
    else:
        base_ok = True
    try:
        verify_manifest_fs_access_format(manifest)
    except ValueError:
        fs_access_ok = False
    else:
        fs_access_ok = True

    return base_ok, fs_access_ok
