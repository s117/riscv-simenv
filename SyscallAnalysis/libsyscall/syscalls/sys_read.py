from typing import List

from . import syscall as s


# ssize_t read(int fd, void *buf, size_t count);
@s.mixedomatic
class sys_read(s.Syscall, s.MixinSyscallUseFd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        assert isinstance(args[2], s.SyscallArgInteger)
        self.fd = args[0].avalue
        self.count = args[2].avalue

    def is_success(self):
        # type: () -> bool
        return self.ret != -1

    def use_fd_get_fds(self):
        # type: () -> List[int]
        return [self.fd]
