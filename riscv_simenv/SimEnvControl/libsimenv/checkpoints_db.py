import os
from typing import Dict, List


def get_app_checkpoint_dir(chkpt_root, app_name):
    # type: (str, str) -> str
    return os.path.join(chkpt_root, app_name)


def get_checkpoint_abspath(chkpt_root, app_name, checkpoint):
    # type: (str, str, str) -> str
    return os.path.join(
        get_app_checkpoint_dir(chkpt_root, app_name), checkpoint
    )


def glob_checkpoints_in_dir(app_chkpt_dir):
    # type: (str) -> List[str]
    if not os.path.isdir(app_chkpt_dir):
        return []
    return list(filter(lambda _p: _p.endswith(".gz"), os.listdir(app_chkpt_dir)))


def get_available_checkpoints_for_app(chkpt_root, app):
    # type: (str, str) -> List[str]
    app_chkpt_folder = get_app_checkpoint_dir(chkpt_root, app)
    return glob_checkpoints_in_dir(app_chkpt_folder)


def glob_all_checkpoints(chkpt_root):
    # type: (str) -> Dict[str, List[str]]
    apps = filter(lambda _p: os.path.isdir(get_app_checkpoint_dir(chkpt_root, _p)), os.listdir(chkpt_root))

    result = dict()
    for app in apps:
        chkpts = get_available_checkpoints_for_app(chkpt_root, app)
        result[app] = chkpts

    return result


def get_all_available_checkpoints_for_any(chkpt_root):
    # type: (str) -> List[str]
    all_available = glob_all_checkpoints(chkpt_root)
    all_chkpts = []
    for v in all_available.values():
        all_chkpts.extend(v)
    return all_chkpts


if __name__ == '__main__':
    test_path = "./checkpoints"


    def main():
        all_chkpt = glob_all_checkpoints(test_path)
        for app, chkpts in all_chkpt.items():
            print("- %s" % app)
            for chkpt in chkpts:
                print("   %s" % chkpt)


    main()
