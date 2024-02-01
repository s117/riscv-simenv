import os
import shutil
import stat
from typing import List, Tuple

from .utils import remove_path


def add_sysroot(sysroots_db_path, sysroot_name, src_path):
    # type: (str, str, str) -> Tuple[bool, str]
    new_sysroot_path = get_pristine_sysroot_dir(sysroots_db_path, sysroot_name)
    try:
        shutil.copytree(src_path, new_sysroot_path, symlinks=False)
        set_dir_readonly_ugo(new_sysroot_path)
    except Exception as ex:
        return False, str(ex)
    else:
        return True, ""


def remove_sysroot(sysroots_db_path, sysroot_name):
    # type: (str, str) -> Tuple[bool, str]
    sysroot_to_remove_path = get_pristine_sysroot_dir(sysroots_db_path, sysroot_name)
    set_dir_writeable_u(sysroot_to_remove_path)
    return remove_path(sysroot_to_remove_path)


def get_pristine_sysroot_dir(sysroots_db_path, sysroot_name):
    # type: (str, str) -> str
    return os.path.join(sysroots_db_path, sysroot_name)


def is_sysroot_available(sysroots_db_path, sysroot_name):
    # type: (str, str) -> bool
    return os.path.isdir(
        get_pristine_sysroot_dir(sysroots_db_path, sysroot_name)
    )


def get_all_sysroots(sysroots_db_path):
    # type: (str) -> List[str]
    sysroots = list(filter(lambda _p: is_sysroot_available(sysroots_db_path, _p), os.listdir(sysroots_db_path)))

    return sysroots


def set_file_readonly_ugo(filepath):
    # type: (str) -> None
    no_write_mask = ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    mode = os.stat(filepath).st_mode
    os.chmod(filepath, mode=mode & no_write_mask)


def set_file_writable_u(filepath):
    # type: (str) -> None
    mode = os.stat(filepath).st_mode
    os.chmod(filepath, mode=mode | stat.S_IWUSR)


def set_dir_readonly_ugo(path):
    # type: (str) -> None
    for root, dirs, files in os.walk(path):
        for dname in dirs:
            set_file_readonly_ugo(os.path.join(root, dname))
        for fname in files:
            set_file_readonly_ugo(os.path.join(root, fname))
    set_file_readonly_ugo(path)


def set_dir_writeable_u(path):
    # type: (str) -> None
    for root, dirs, files in os.walk(path):
        for dname in dirs:
            set_file_writable_u(os.path.join(root, dname))
        for fname in files:
            set_file_writable_u(os.path.join(root, fname))
    set_file_writable_u(path)


if __name__ == '__main__':
    test_path = "./sysroots"


    def main():
        sysroots = get_all_sysroots(test_path)
        for sysroot in sysroots:
            print("%s" % sysroot)


    main()
