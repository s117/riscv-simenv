from typing import List

from . import syscall as s


# int ftruncate(int fd, off_t length);
@s.mixedomatic
class sys_ftruncate(s.Syscall, s.MixinSyscallUseFd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        assert isinstance(args[1], s.SyscallArgInteger)
        self.fd = args[0].avalue
        self.length = args[1].avalue

    def is_success(self):
        # type: () -> bool
        return self.ret == 0

    def use_fd_get_fds(self):
        # type: () -> List[int]
        return [self.fd]
