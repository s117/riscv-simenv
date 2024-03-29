from typing import List, Iterable

from pyparsing import ParseResults

from .fd_tracker import FileDescriptorTracker
from .strace_parser import StraceInputParser
from ..syscalls import factory as syscall_factory
from ..syscalls.syscall import SyscallArgInteger, SyscallArgStrPtr, MixinSyscallUseFd, MixinSyscallDefFd, Syscall


class SyscallTraceConstructor:

    def __init__(self, initial_working_dir):
        # type: (str) -> None
        self.syscalls = list()  # type: List[Syscall]
        self.fd_res = FileDescriptorTracker(initial_working_dir)

    def get_fd_resolver(self):
        # type: () -> FileDescriptorTracker
        return self.fd_res

    def on_strace_parsed(self, p, start, end):
        # type: (ParseResults, int, int) -> None
        args = list()
        for pa in p.syscall_args:
            if pa.arg_type in StraceInputParser.list_arg_type_strptr:
                args.append(SyscallArgStrPtr(pa.arg_name, pa.arg_type, pa.arg_val, pa.arg_memval))
            elif pa.arg_type in StraceInputParser.list_arg_type_num:
                args.append(SyscallArgInteger(pa.arg_name, pa.arg_type, pa.arg_val))
            else:
                raise ValueError("Invalid syscall argument type %s" % p.arg_type)
        new_syscall = syscall_factory.construct_syscall(
            p.syscall_name, args, p.ret_code, p.syscall_id,
            self.fd_res.getcwd(), len(self.syscalls)
        )
        self.syscalls.append(new_syscall)

        if isinstance(new_syscall, MixinSyscallUseFd):
            fd_defs = map(
                lambda fd: self.fd_res.lookup_def(fd),
                new_syscall.use_fd_get_fds()
            )  # type: Iterable[MixinSyscallDefFd]

            for fd_def in fd_defs:
                if fd_def:
                    fd_def.def_fd_add_use(new_syscall)
                new_syscall.use_fd_add_def(fd_def)

        self.fd_res.on_syscall(new_syscall, start, end)

    def parse_strace_str(self, strace_str):
        # type: (str) -> None
        for i, start, end in StraceInputParser.parse(strace_str):
            if i:
                self.on_strace_parsed(i, start, end)
