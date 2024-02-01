from typing import List

from . import syscall as s


# ssize_t readlinkat(int dirfd, const char *pathname, char *buf, size_t bufsiz);
@s.mixedomatic
class sys_readlinkat(s.Syscall, s.MixinSyscallHasPathArgs, s.MixinSyscallUseFd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        # type: (str, s.SyscallArgList_t, int, int, str, int) -> None
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        assert isinstance(args[0], s.SyscallArgInteger)
        assert isinstance(args[1], s.SyscallArgStrPtr)
        assert isinstance(args[2], s.SyscallArgInteger)
        assert isinstance(args[3], s.SyscallArgInteger)
        self.dirfd = args[0].avalue
        self.pathname = args[1].amemval
        self.buf_ptr = args[2].avalue
        self.buf_size = args[3].avalue
        # if ret > 0:
        #     assert len(args) == 6
        #     # if a link resolved successfully, two extra fields will be dumped by the FESVR:
        #     #   1. extra_host_realname   - the resolved realname obtained by the host side
        #     #   2. extra_target_realname - the converted realname sent to the target side
        #     # FESVR Patch @ syscall.cc:539
        #     #+ m_strace->syscall_record_param_path_name("extra_host_realname", (uint64_t)NULL, &path_buf[0], 'o');
        #     #+ m_strace->syscall_record_param_path_name("extra_target_realname", (uint64_t)NULL, &target_path[0], 'o');
        #
        #     assert isinstance(args[4], s.SyscallArgStrPtr)
        #     assert isinstance(args[5], s.SyscallArgStrPtr)
        #     assert args[4].aname == "extra_host_realname"
        #     assert args[5].aname == "extra_target_realname"
        #     self.realname_host = args[4].amemval
        #     self.realname_target = args[5].amemval
        # else:
        #     assert len(args) == 4
        #     self.realname_host = None
        #     self.realname_target = None

    def is_success(self):
        # type: () -> bool
        # EINVAL is also considered as "success" also because if bufsiz is positive and buf pointer is not null,
        # it implies the requested path exist. From $ man 2 readlinkat:
        #
        # RETURN VALUE
        #       On success, these calls return the number of bytes placed in buf.  (If the returned value equals bufsiz, then truncation may have occurred.)  On error, -1 is returned and errno is  set  to  indicate
        #       the error.
        #
        # ERRORS
        #       EACCES Search permission is denied for a component of the path prefix.  (See also path_resolution(7).)
        #
        #       EFAULT buf extends outside the process's allocated address space.
        #
        #       EINVAL bufsiz is not positive.
        #
        #       EINVAL The named file (i.e., the final filename component of pathname) is not a symbolic link.
        #
        #       EIO    An I/O error occurred while reading from the filesystem.
        #
        #       ELOOP  Too many symbolic links were encountered in translating the pathname.
        #
        #       ENAMETOOLONG
        #              A pathname, or a component of a pathname, was too long.
        #
        #       ENOENT The named file does not exist.
        #
        #       ENOMEM Insufficient kernel memory was available.
        #
        #       ENOTDIR
        #              A component of the path prefix is not a directory.
        #
        #       The following additional errors can occur for readlinkat():
        #
        #       EBADF  dirfd is not a valid file descriptor.
        #
        #       ENOTDIR
        #              pathname is relative and dirfd is a file descriptor referring to a file other than a directory.
        nullptr = 0
        EINVAL = -22
        return self.ret > 0 or (self.ret == EINVAL and self.buf_size > 0 and self.buf_ptr != nullptr)

    def get_arg_paths(self):
        # type: () -> s.GenericPathList_t
        self.check_fd_def(0)
        return [s.GenericPath(self.def_list[0].def_fd_get_path().abspath(), self.pathname)]

    def use_fd_get_fds(self):
        # type: () -> List[int]
        return [self.dirfd]
