import hashlib
import os
import shutil
import string
import sys

__sha256_cache = {}  # type: dict[str, str]


def sha256(fpath, use_cache=True):
    # type: (str, bool) -> str
    global __sha256_cache
    if use_cache and fpath in __sha256_cache:
        return __sha256_cache[fpath]
    BUF_SIZE = 65536
    h = hashlib.sha256()
    with open(fpath, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            h.update(data)
    sha256_hash = h.hexdigest()
    __sha256_cache[fpath] = sha256_hash
    return sha256_hash


def is_valid_sha256(h):
    # type: (str) -> bool
    return len(h) == 64 and all(_ in string.hexdigits for _ in h)


def remove_path(p):
    # type: (str) -> (bool, str)
    if not os.path.exists(p):
        return True, "Success"
    if os.path.isfile(p):
        try:
            os.remove(p)
        except Exception as e:
            return False, str(e)
    else:
        try:
            shutil.rmtree(p)
        except Exception as e:
            return False, str(e)
    return True, "Success"


def human_readable_size(size):
    # type: (int) -> (float, str)
    DIV_KB = 1 << 10
    DIV_MB = DIV_KB << 10
    DIV_GB = DIV_MB << 10
    DIV_TB = DIV_GB << 10

    if size < DIV_KB:
        return size, "B"
    elif size < DIV_MB:
        return size / DIV_KB, "K"
    elif size < DIV_GB:
        return size / DIV_MB, "M"
    elif size < DIV_TB:
        return size / DIV_GB, "G"
    else:
        return size / DIV_TB, "T"


def get_size(path):
    # type: (str) -> (float, str)

    if os.path.isfile(path):
        total_size = os.path.getsize(path)
    else:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)

    return human_readable_size(total_size)


def get_size_str(path):
    # type: (str) -> str
    size = get_size(path)
    if isinstance(size[0], int):
        str_size = "%d %s" % size
    else:
        assert isinstance(size[0], float)
        str_size = "%.1f %s" % size
    return str_size


def fatal(s):
    # type: (str) -> None
    print("Fatal: %s" % s, file=sys.stderr)
    sys.exit(-1)


def warning(s):
    # type: (str) -> None
    print("Warning: %s" % s, file=sys.stderr)
