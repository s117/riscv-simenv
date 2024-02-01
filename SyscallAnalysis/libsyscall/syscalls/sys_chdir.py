import os

from . import syscall as s


# int chdir(const char *path);
@s.mixedomatic
class sys_chdir(s.Syscall, s.MixinSyscallHasPathArgs, s.MixinSyscallDefFd):
    # because AT_FDCWD is logically defined by chdir, sys_chdir has mixin_syscall_def_fd
    default_flag = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NONBLOCK

    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgStrPtr)
        self.path = args[0].amemval

    def is_success(self):
        # type: () -> bool
        return self.ret == 0

    def get_arg_paths(self):
        # type: () -> s.GenericPathList_t
        return [s.GenericPath(self.at_cwd, self.path)]

    def def_fd_get_path(self):
        # type: () -> s.GenericPath
        return s.GenericPath(self.at_cwd, self.path)

    def def_fd_get_flags(self):
        # type: () -> int
        return self.default_flag
