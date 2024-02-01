from . import syscall as s


# char *getcwd(char *buf, size_t size);
@s.mixedomatic
class sys_getcwd(s.Syscall):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)

    def is_success(self):
        # type: () -> bool
        return self.ret != 0
