from typing import List

from . import syscall as s


# int linkat(int olddirfd, const char *oldpath,
#            int newdirfd, const char *newpath, int flags);
@s.mixedomatic
class sys_linkat(s.Syscall, s.MixinSyscallHasPathArgs, s.MixinSyscallUseFd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        assert isinstance(args[1], s.SyscallArgStrPtr)
        assert isinstance(args[2], s.SyscallArgInteger)
        assert isinstance(args[3], s.SyscallArgStrPtr)
        assert isinstance(args[4], s.SyscallArgInteger)
        self.olddirfd = args[0].avalue
        self.oldpath = args[1].amemval
        self.newdirfd = args[2].avalue
        self.newpath = args[3].amemval
        self.flags = args[4].avalue

    def is_success(self):
        # type: () -> bool
        return self.ret == 0

    def get_arg_paths(self):
        # type: () -> s.GenericPathList_t
        self.check_fd_def(0)
        self.check_fd_def(1)
        return [
            s.GenericPath(self.def_list[0].def_fd_get_path().abspath(), self.oldpath),
            s.GenericPath(self.def_list[1].def_fd_get_path().abspath(), self.newpath)
        ]

    def use_fd_get_fds(self):
        # type: () -> List[int]
        return [
            self.olddirfd,
            self.newdirfd
        ]
