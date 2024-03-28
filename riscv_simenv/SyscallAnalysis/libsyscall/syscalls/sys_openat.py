from typing import List

from . import syscall as s


# int openat(int dirfd, const char *pathname, int flags, mode_t mode);
@s.mixedomatic
class sys_openat(s.Syscall, s.MixinSyscallHasPathArgs, s.MixinSyscallDefFd, s.MixinSyscallUseFd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        assert isinstance(args[1], s.SyscallArgStrPtr)
        assert isinstance(args[2], s.SyscallArgInteger)
        assert isinstance(args[3], s.SyscallArgInteger)
        self.dirfd = args[0].avalue
        self.pathname = args[1].amemval
        self.flags = args[2].avalue
        self.mode = args[3].avalue

    def is_success(self):
        # type: () -> bool
        return self.ret >= 0

    def new_fd(self):
        # type: () -> int
        return self.ret

    def def_fd_get_path(self):
        # type: () -> s.GenericPath
        self.check_fd_def(0)
        return s.GenericPath(self.def_list[0].def_fd_get_path().abspath(), self.pathname)

    def get_arg_paths(self):
        # type: () -> s.GenericPathList_t
        return [self.def_fd_get_path()]

    def use_fd_get_fds(self):
        # type: () -> List[int]
        return [self.dirfd]

    def def_fd_get_flags(self):
        # type: () -> int
        return self.flags
