from . import syscall as s


# int lstat(const char *pathname, struct stat *statbuf);
@s.mixedomatic
class sys_lstat(s.Syscall, s.MixinSyscallHasPathArgs):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgStrPtr)
        self.pathname = args[0].amemval

    def is_success(self):
        # type: () -> bool
        return self.ret == 0

    def get_arg_paths(self):
        # type: () -> s.GenericPathList_t
        return [s.GenericPath(self.at_cwd, self.pathname)]
