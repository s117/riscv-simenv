from . import syscall as s


# int fstatat(int dirfd, const char *pathname, struct stat *statbuf, int flags);
@s.mixedomatic
class sys_fstatat(s.syscall, s.mixin_syscall_has_path_args, s.mixin_syscall_use_fd):
    AT_EMPTY_PATH = 0x1000  # Allow empty relative pathname, <linux/fcntl.h>

    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        self.dirfd = args[0].avalue
        self.pathname = args[1].amemval
        self.flags = args[2].avalue

    def is_success(self):
        return self.ret == 0

    def get_arg_paths(self):
        if self.pathname == "" and (self.flags | self.AT_EMPTY_PATH) != 0:
            # From `man 2 fstatat`:
            # AT_EMPTY_PATH (since Linux 2.6.39)
            #        If pathname is an empty string, operate on the file referred to by dirfd (which may have been obtained using the open(2) O_PATH flag).  In this case, dirfd can refer to
            #        any type of file, not just a directory, and the behavior of fstatat() is similar to that of fstat().  If dirfd is AT_FDCWD, the call operates on the current working di‐
            #        rectory.  This flag is Linux-specific; define _GNU_SOURCE to obtain its definition.
            if self.dirfd in {1, 2, 3}:
                return []  # ignore fstat(STDIN/STDOUT/STDERR)
            return [self.def_list[0].def_fd_get_path()]
        return [s.path(self.def_list[0].def_fd_get_path().abspath(), self.pathname)]

    def use_fd_get_fds(self):
        return [self.dirfd]
