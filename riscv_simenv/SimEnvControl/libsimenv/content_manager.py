import os
import pathlib
from typing import Optional

from riscv_simenv.SyscallAnalysis.libsyscall.target_path_converter import TargetPathConverter
from .utils import sha256


class ContentManager:
    def __init__(self, pristine_sysroot, post_sim_sysroot):
        # type: (str, str) -> None
        self.post_sim_sysroot = post_sim_sysroot
        self.pristine_sysroot = pristine_sysroot
        self.pristine_path_convertor = TargetPathConverter({
            "/": pristine_sysroot
        })
        self.post_sim_path_convertor = TargetPathConverter({
            "/": post_sim_sysroot
        })

    def get_pristine_sysroot(self):
        # type: () -> str
        return self.pristine_sysroot

    def get_post_sim_sysroot(self):
        # type: () -> str
        return self.post_sim_sysroot

    def locate_pristine_file(self, target_path):
        # type: (str) -> Optional[str]
        expected_location = pathlib.PosixPath(
            self.pristine_path_convertor.t2h(target_path)
        )
        if expected_location.exists():
            return str(expected_location)
        else:
            return None

    def locate_post_sim_file(self, target_path):
        # type: (str) -> Optional[str]
        # remap from "/..." to "$post_sim_sysroot/..."
        expected_location = pathlib.PosixPath(
            self.post_sim_path_convertor.t2h(target_path)
        )
        if expected_location.exists():
            return str(expected_location)
        else:
            return None

    @staticmethod
    def do_sha256(res_path):
        # type: (str) -> Optional[str]
        if res_path:
            if os.path.isfile(res_path):
                return sha256(res_path)
            elif os.path.isdir(res_path):
                return "DIR"
            elif os.path.exists(res_path):
                return "SKIP"  # Skip this type of path, usually it is a device file
            else:
                return None
        else:
            return None

    def get_pristine_hash(self, target_path):
        # type: (str) -> Optional[str]
        res_path = self.locate_pristine_file(target_path)

        return self.do_sha256(res_path)

    def get_post_sim_hash(self, target_path):
        # type: (str) -> Optional[str]
        res_path = self.locate_post_sim_file(target_path)

        return self.do_sha256(res_path)
