import copy
import json
import os
import pathlib
from typing import Dict, Union, TextIO, Set, Tuple, List

from riscv_simenv.SyscallAnalysis.libsyscall.analyzer.file_usage import FileUsageInfo, stat_file_usage
from riscv_simenv.SyscallAnalysis.libsyscall.analyzer.syscall_trace_constructor import SyscallTraceConstructor
from .content_manager import ContentManager
from .utils import fatal, is_valid_sha256

Manifest_t = Dict[str, Union[str, Dict, List]]


def new_manifest(app_name, proxy_kernel, stdin_redir, app_cmd, app_init_cwd, memsize, sysroot_name, copy_spawn):
    # type: (str, str, str, str, str, int, str, bool) -> Manifest_t
    manifest = dict()
    manifest["app_name"] = app_name
    manifest["app_proxy_kernel"] = proxy_kernel
    manifest["app_stdin_redir"] = stdin_redir
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
    verify_manifest_format(existing_manifest, skip_extra_field=True)

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

    # 2. Handle extra input files
    readonly_usage = FileUsageInfo.build_from_str("FUSE_OPEN_RD | FUSE_READ_DATA")
    # 2.1 Handle the input via STDIN redirection (if used)
    stdin_file_target_path = manifest["app_stdin_redir"]
    if stdin_file_target_path:
        assert pathlib.PurePosixPath(stdin_file_target_path).is_absolute()
        print(f"File '{stdin_file_target_path}' was passed as the input to the app via STDIN redirection.")
        # 2.2 Record input files passed as STDIN
        if not content_manager.locate_pristine_file(stdin_file_target_path):
            fatal(
                "Manifest indicates the app uses file [%s] via STDIN redirection, "
                "but it is not found in the pristine sysroot [%s]" %
                (stdin_file_target_path, content_manager.get_pristine_sysroot())
            )
        manifest_add_fs_access_entry(stdin_file_target_path, readonly_usage)
        print(f"Added STDIN redirection input [{stdin_file_target_path}] to the manifest.")
    # 2.2 Handle the proxy kernel
    if not content_manager.locate_pristine_file(app_proxy_kernel):
        fatal(
            f"Cannot find the proxy kernel inside the pristine sysroot at \"{app_proxy_kernel}\"."
        )
    manifest_add_fs_access_entry(app_proxy_kernel, readonly_usage)
    print(f"Added proxy kernel [{app_proxy_kernel}] to the manifest.")

    verify_manifest_fs_access_format(manifest)

    return manifest


def update_manifest_instret(existing_manifest, fesvr_final_state_fp):
    # type: (Manifest_t, TextIO) -> Manifest_t
    verify_manifest_format(existing_manifest, skip_extra_field=True)
    manifest = copy.deepcopy(existing_manifest)

    fesvr_final_state_dump = json.load(fesvr_final_state_fp)
    instret = [s["instret"] for s in fesvr_final_state_dump["core_state"]]
    print(f"The number of instructions executed by each core reported by the FESVR:")
    for idx, coren_instret in enumerate(instret):
        if not isinstance(coren_instret, int):
            fatal(
                f"In the final state dump json from FESVR, data['core_state'][{idx}]['instret'] is not an integer.")
        print(f"  - core{idx}: {coren_instret} instructions")

    manifest["instret"] = instret

    verify_manifest_instret(manifest)

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


def _ensure_list_type(manifest, key):
    # type: (Manifest_t, str) -> None
    _ensure_exist(manifest, key)
    if not isinstance(manifest[key], list):
        raise ValueError("Field [%s] in the manifest is not a list: %s" % (key, manifest[key]))


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


def verify_manifest_instret(manifest):
    # type: (Manifest_t) -> None
    """
    The manifest['instret'] is an array of number of instructions executed on each CPU core
    when the app's execution is finished. It indicates the length of a benchmark in terms of
    the total dynamic instruction count.
    """
    _ensure_list_type(manifest, "instret")
    for idx, coren_instret in enumerate(manifest["instret"], start=1):
        if not isinstance(coren_instret, int):
            raise ValueError("The %dth element in manifest['instret'] is not an integer." % idx)


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


def verify_manifest_format(manifest, skip_extra_field=False):
    # type: (Manifest_t, bool) -> bool
    _ensure_str_type(manifest, "app_name")
    _ensure_str_type(manifest, "app_proxy_kernel")
    _ensure_str_type(manifest, "app_stdin_redir")
    _ensure_str_type(manifest, "app_cmd")
    _ensure_str_type(manifest, "app_init_cwd")
    _ensure_str_type(manifest, "app_pristine_sysroot")
    _ensure_int_type(manifest, "app_memsize")
    _ensure_in_set(manifest, "app_spawn_mode", {"copy", "link"})

    if not skip_extra_field:
        verify_manifest_fs_access_format(manifest)
        verify_manifest_instret(manifest)

    return True


def manifest_status(manifest):
    # type: (Manifest_t) -> Tuple[bool, bool, bool]
    try:
        verify_manifest_format(manifest, skip_extra_field=True)
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

    try:
        verify_manifest_instret(manifest)
    except ValueError:
        instret_ok = False
    else:
        instret_ok = True

    return base_ok, fs_access_ok, instret_ok
