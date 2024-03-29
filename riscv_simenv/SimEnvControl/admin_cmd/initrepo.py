import os

import click

from ..libsimenv.repo_path import create_repo
from ..libsimenv.utils import fatal


@click.command()
@click.argument("new-repo-root", type=click.Path(exists=False, dir_okay=False, file_okay=False))
def cmd_init_repo(new_repo_root):
    """
    Create an empty app repository.
    """
    if os.path.exists(new_repo_root):
        fatal("Path %s already exist." % new_repo_root)

    print("Creating empty app repo at \"%s\"" % new_repo_root)
    create_repo(new_repo_root)

    print("Done.")


if __name__ == '__main__':
    cmd_init_repo()
