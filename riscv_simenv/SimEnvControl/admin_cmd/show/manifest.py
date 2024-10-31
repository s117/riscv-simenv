import click
from natsort import natsorted
from tabulate import tabulate

from ...libsimenv.app_manifest import manifest_status
from ...libsimenv.manifest_db import get_avail_apps_in_db, get_manifest_path, load_from_manifest_db
from ...libsimenv.repo_path import get_repo_components_path
from ...libsimenv.utils import get_size_str


@click.command()
@click.pass_context
def cmd_show_manifest(ctx):
    from . import tabulate_formats

    sysroots_archive_path, manifest_db_path, checkpoints_archive_path = get_repo_components_path(ctx.obj["repo_path"])
    apps = get_avail_apps_in_db(db_path=manifest_db_path)
    row = []

    for app in natsorted(apps):
        app_manifest_path = get_manifest_path(manifest_db_path, app)
        app_manifest = load_from_manifest_db(app, manifest_db_path)
        base_ok, fs_access_ok, instret_ok = manifest_status(app_manifest)
        if not base_ok:
            manifest_status_str = 'INVALID'
        elif not fs_access_ok and not instret_ok:
            manifest_status_str = 'BASE'
        elif fs_access_ok and not instret_ok:
            manifest_status_str = 'BASE+FS_ACC'
        elif not fs_access_ok and instret_ok:
            manifest_status_str = 'BASE+INSTRET'
        else:
            assert fs_access_ok and instret_ok
            manifest_status_str = 'FULL'
        manifest_size_str = get_size_str(app_manifest_path)
        row.append((app, manifest_status_str, manifest_size_str, app_manifest_path))

    print(
        tabulate(
            row,
            headers=["App name", "Manifest status", "Manifest size", "Manifest location"],
            **tabulate_formats
        )
    )
