from . import syscall as s


# void exit(int status)
@s.mixedomatic
class sys_exit(s.Syscall):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        self.status = args[0].avalue

    def is_success(self):
        # type: () -> bool
        return True

    def ret_code(self):
        # type: () -> int
        return self.status
