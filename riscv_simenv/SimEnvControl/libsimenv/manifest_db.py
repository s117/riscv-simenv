import os
import sys
from collections import defaultdict
from typing import List, Dict

import yaml
from fuzzywuzzy import fuzz

from .app_manifest import Manifest_t


def get_manifest_path(db_path, record_name):
    # type: (str, str) -> str
    return os.path.join(db_path, "%s.yaml" % record_name)


def save_to_manifest_db(record_name, manifest, db_path):
    # type: (str, Manifest_t, str) -> None
    out_filename = get_manifest_path(db_path, record_name)
    with open(out_filename, "w") as out_fp:
        yaml.dump(manifest, out_fp)


def load_from_manifest_db(record_name, db_path):
    # type: (str, str) -> Manifest_t
    in_filename = get_manifest_path(db_path, record_name)
    with open(in_filename, "r") as in_fp:
        return yaml.safe_load(in_fp)


def get_avail_apps_in_db(db_path):
    # type: (str) -> List[str]
    try:
        avail_apps = list(map(
            lambda tp: tp[0],
            filter(
                lambda tp: tp[1].lower() == ".yaml",
                map(
                    lambda p: os.path.splitext(p),
                    os.listdir(db_path)
                )
            )
        ))
    except FileNotFoundError:
        return []

    return avail_apps


def get_app_name_suggestion(name, limit, db_path):
    # type: (str, int, str) -> List[str]
    PICKING_FUZZ_RATION_THRESHOLD = 36
    avail_apps = get_avail_apps_in_db(db_path)
    ranked_suggestions = sorted(map(
        lambda arn: (arn, fuzz.ratio(name, arn)),
        avail_apps
    ), key=lambda i: i[1], reverse=True)
    suggestion_list = list()
    for r_idx in range(min(len(ranked_suggestions), limit)):
        if ranked_suggestions[r_idx][1] >= PICKING_FUZZ_RATION_THRESHOLD:
            suggestion_list.append(ranked_suggestions[r_idx][0])

    return suggestion_list


def is_app_available(name, db_path):
    # type: (str, str) -> bool
    return os.path.isfile(get_manifest_path(db_path, name))


def prompt_app_name_suggestion(app_name, db_path):
    # type: (str, str) -> None
    suggestions = get_app_name_suggestion(app_name, limit=10, db_path=db_path)
    if suggestions:
        print("Did you mean:", file=sys.stderr)
        for s in suggestions:
            print("\t%s" % s, file=sys.stderr)
    else:
        print("No app name suggestion.", file=sys.stderr)


def stat_app_sysroot_dependency(db_path):
    # type: (str) -> Dict[str, List[str]]
    apps = get_avail_apps_in_db(db_path=db_path)
    sysroots_apps_dep = defaultdict(list)
    for app in apps:
        app_manifest = load_from_manifest_db(app, db_path)
        app_sysroot = app_manifest["app_pristine_sysroot"]
        sysroots_apps_dep[app_sysroot].append(app)
    return sysroots_apps_dep
