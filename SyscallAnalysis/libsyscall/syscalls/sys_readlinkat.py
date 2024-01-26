from . import syscall as s


# ssize_t readlinkat(int dirfd, const char *pathname, char *buf, size_t bufsiz);
@s.mixedomatic
class sys_readlinkat(s.syscall, s.mixin_syscall_has_path_args, s.mixin_syscall_use_fd):
    def __init__(self, name, args, ret, syscall_id, at_cwd, seq_no):
        super().__init__(name, args, ret, syscall_id, at_cwd, seq_no)
        self.dirfd = args[0].avalue
        self.pathname = args[1].amemval
        if ret > 0:
            assert len(args) == 6
            # those two extra information were dumped by the FESVR
            # they are the resolved realname on the host and target side
            assert args[4].aname == "extra_host_realname"
            assert args[5].aname == "extra_target_realname"
            self.realname_host = args[4].amemval
            self.realname_target = args[5].amemval
        else:
            assert len(args) == 4
            self.realname_host = None
            self.realname_target = None

    def is_success(self):
        return self.ret > 0

    def get_arg_paths(self):
        return [s.path(self.def_list[0].def_fd_get_path().abspath(), self.pathname)]

    def use_fd_get_fds(self):
        return [self.dirfd]
