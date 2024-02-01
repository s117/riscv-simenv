from . import syscall as s


# int close(int fd);
@s.mixedomatic
class sys_close(s.Syscall, s.MixinSyscallUseFd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        self.target_fd = args[0].avalue

    def is_success(self):
        # type: () -> bool
        return self.ret == 0

    def closing_fd(self):
        # type: () -> int
        return self.target_fd

    def use_fd_get_fds(self):
        return [self.closing_fd()]
