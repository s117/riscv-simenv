# riscv-simenv

Pack a RISC-V workload once, then launch it the same way every time, on
[spike](https://github.com/riscv-software-src/riscv-isa-sim) or any simulator
that accepts spike's command line (such as 721sim).

`riscv-simenv` keeps a **workload repository** of programs, their input files, and
their checkpoints. For any workload in it, the tool builds a minimal root filesystem
holding exactly the files that workload touches (a **simenv**), checks it against a
recorded manifest, and generates a Makefile that runs the simulator inside it.

## Why it exists

Under the RISC-V proxy kernel (pk), a simulated program has no filesystem of its own.
pk forwards every system call (`openat`, `read`, `write`, `getcwd`, ...) through HTIF
to the front-end server (fesvr), which runs it on the host. That causes two problems.

**Runs are not reproducible.** The program reads and writes real host files, relative
to the host's working directory. Whether a run succeeds, and what it produces,
depends on the state of whatever directory you launched it from.

**Checkpoints need the host state too.** A checkpoint captures the simulator's
registers and memory, but the open files, file offsets, and working directory live in
the host process. The checkpointing scheme this tool supports restores them by
replaying the program's whole syscall history against the host from the start. The
replay only lands in the right place if the host filesystem is byte-for-byte the same
as it was when the checkpoint was taken.

`riscv-simenv` provides that filesystem:

- A **manifest** records every path the workload touches, how it uses each one, and
  its SHA-256 before and after the run.
- `spawn` builds a fresh directory containing only those paths. Files the workload
  only reads are symlinked to a read-only master copy; files it writes, creates,
  deletes or `stat`s are copied in.
- `verify` checks the spawned directory against the manifest before every run.
- The generated Makefile starts the simulator with `+chroot=<simenv>` and
  `+target-cwd=<dir>`, so the program sees the simenv as `/`.

## Concepts

| Term | Meaning |
| --- | --- |
| **app** | One program with one input set, e.g. `401.bzip2_dryerjpg_test`. |
| **pristine sysroot** | The read-only master copy of a root filesystem, stored in the repository. Several apps can share one. |
| **simenv** | A working copy spawned from a pristine sysroot for a single run, holding only the files the app needs. |
| **manifest** | A YAML file per app: how to launch it, plus every path it touches with pre-run and post-run hashes. |
| **checkpoint** | A gzipped simulator snapshot, usually the start of a SimPoint interval, that a simulator can resume from. |
| **workload repository** | A directory containing `manifests/`, `sysroots/` and `checkpoints/`. |

## Requirements

- Linux and Python 3.11 or newer.
- A spike build whose fesvr accepts `+chroot=` and `+target-cwd=`. Resuming from a
  checkpoint also needs the simulator to load one (`-c<file>` by default), and adding
  new apps needs `+strace=` and `+final-state-dump=`.
- A workload repository. You can create an empty one with `riscv-simenv repo initrepo`.

## Installation

```bash
pip install riscv-simenv
```

From a source checkout:

```bash
poetry install        # or: pip install .
```

### Shell completion

App, checkpoint and sysroot names tab-complete in bash and zsh:

```bash
eval "$(_RISCV_SIMENV_COMPLETE=bash_source riscv-simenv)"   # bash
eval "$(_RISCV_SIMENV_COMPLETE=zsh_source riscv-simenv)"    # zsh
```

## Quick start

Point the tool at a repository, find an app, and run it:

```bash
export RISCV_SIMENV_REPO_PATH=/path/to/repo

riscv-simenv list                    # all apps, with checkpoint counts
riscv-simenv list 000.helloworld     # checkpoints for one app

mkdir run && cd run
riscv-simenv mkgen 000.helloworld    # writes ./Makefile
make cleanrun                        # spawn ./simenv, verify it, run the simulator
```

The app names in this README come from one example repository. Run
`riscv-simenv list` to see what yours contains.

`mkgen` writes `Makefile` into the current directory and spawns the simenv at
`./simenv`, so give each run its own empty directory. The Makefile calls
`riscv-simenv` itself, so `RISCV_SIMENV_REPO_PATH` must still be set when you run
`make`.

The repository is found from `--repo-path`, then `$RISCV_SIMENV_REPO_PATH`, then
`~/.config/simenv_repo` if that directory exists.

### Makefile targets

| Target | What it does |
| --- | --- |
| `cleanrun` | `envclean`, `envsetup`, then `run`. The usual entry point. |
| `envsetup` | Spawn the simenv into `./simenv`. |
| `envcheck` | Verify `./simenv` against the manifest. `run` and `gdb` depend on it. |
| `envclean` | Delete `./simenv`. |
| `run` | Launch the simulation. |
| `gdb`, `cleangdb` | The same launch under `gdb --args`. |
| `app_target_cwd`, `app_target_cmd`, `app_mem` | Print a manifest field, for scripts. |

The launch line is:

```make
$(SIM) -m$(APP_MEMSIZE) $(SIM_FLAGS) $(SIM_FLAGS_EXTRA) \
    $(FESVR_FLAGS) $(FESVR_FLAGS_EXTRA) +chroot=$(SIMENV_SYSROOT) +target-cwd=$(APP_INIT_CWD) \
    $(PK_PATH) $(PK_FLAGS) $(PK_FLAGS_EXTRA) \
    $(APP_CMD) $(APP_CMD_EXTRA)
```

The four `*_EXTRA` variables are empty and are meant to be overridden on the `make`
command line:

```bash
make cleanrun SIM_FLAGS_EXTRA=-e100000000           # stop after 100M instructions
make cleanrun FESVR_FLAGS_EXTRA=+std-dump=./console # tee target stdout/stderr to files
make run SIM=echo                                   # print the launch line instead of running
```

Use `SIM_FLAGS_EXTRA` rather than `SIM_FLAGS`: `mkgen -c` stores the checkpoint flag
in `SIM_FLAGS`, so overriding that drops the checkpoint.

Always use `make cleanrun` rather than running `make run` twice. A second `run`
reuses a simenv that the first run already modified.

### Resuming from a checkpoint

```bash
riscv-simenv mkgen 401.bzip2_dryerjpg_test -c 401.bzip2_dryerjpg_test.126.0.40.gz
make cleanrun SIM_FLAGS_EXTRA=-e100000000
```

Checkpoints are named `<app>.<simpoint-index>.<weight>.gz`. Each one marks the start
of a 100M-instruction SimPoint interval, and the weight is the share of the whole
program that interval represents. Run each checkpoint for one interval with `-e`,
then combine the results using the weights:

- For per-instruction metrics such as CPI or MPKI, take the weighted mean:
  `Σ wᵢ·Mᵢ / Σ wᵢ`.
- For IPC, use `1 / Σ wᵢ·CPIᵢ`, not the weighted mean of the per-interval IPCs.

Weights are rounded to two decimals in the filename, so they often sum to 0.99 or
1.01. Divide by the actual sum.

A run stopped by `-e` never reaches `exit()`, so `make` always reports
`Error 1`. That is expected. Because target stdout is buffered, such a run usually
prints nothing either.

### Using another simulator

`mkgen` reads two environment variables and writes their values into the Makefile:

```bash
export RISCV_SIMENV_SIM_CMD=/path/to/721sim     # default: spike
export RISCV_SIMENV_SIM_FLAG_LDCKPT=-c          # default: -c
riscv-simenv mkgen 401.bzip2_dryerjpg_test -c 401.bzip2_dryerjpg_test.126.0.40.gz
```

Changing them after `mkgen` has no effect on an existing Makefile; regenerate it, or
override `SIM=` on the `make` command line. Note that spike's `-s<n>` sets the
SimPoint interval while 721sim's `-s<n>` skips `n` instructions, so don't copy
`-s` flags between the two.

## Command reference

| Command | Purpose |
| --- | --- |
| `riscv-simenv list [APP...] [-b]` | List apps, or the checkpoints of the given apps. `-b` prints bare names for scripts. |
| `riscv-simenv mkgen APP [-c CKPT] [--bootstrap]` | Write a Makefile for `APP` in the current directory. |
| `riscv-simenv spawn APP DEST [-f] [--raw] [-c]` | Build a simenv at `DEST`. `-f` replaces an existing `DEST`, `--raw` copies the whole pristine sysroot, `-c` copies files instead of symlinking them. |
| `riscv-simenv verify APP SIMENV` | Check a simenv against the app's manifest. |
| `riscv-simenv repo ...` | Repository management, described below. |

The generated Makefile calls `spawn` and `verify` for you.

Repository management:

| Command | Purpose |
| --- | --- |
| `repo initrepo DIR` | Create an empty repository. |
| `repo subrepo [-c] DIR APP...` | Copy the given apps (manifests and sysroots, plus checkpoints with `-c`) into a new repository. |
| `repo add sysroot NAME PATH [-f]` | Import a directory as a read-only pristine sysroot. |
| `repo add app register ...` | Create a manifest for a new app. See below. |
| `repo add app analyze APP ...` | Fill in a manifest from a bootstrap run. Usually called by `make bootstrap-analyze`. |
| `repo add checkpoint APP FILE.gz... [-s]` | Import checkpoints as read-only files. `-s` deletes the app's existing checkpoints first. |
| `repo remove sysroot NAME... [-f]` | Delete sysroots. Asks first if an app still uses one, unless `-f` is given. |
| `repo remove manifest APP... [-f]` | Delete apps. Asks first if an app still has checkpoints, unless `-f` is given. |
| `repo remove checkpoint APP [CKPT...] [--remove-all]` | Delete checkpoints. |
| `repo show sysroot [--without-size]` | Table of sysroots, their sizes and the apps using them. |
| `repo show manifest` | Table of manifests and how complete each one is. |
| `repo show checkpoint APP` | Table of an app's checkpoints and their sizes. |

Every command accepts `--help`.

## Repository layout

```text
<repo>/
├── manifests/
│   └── <app>.yaml
├── sysroots/
│   └── <sysroot-name>/       # read-only after import
└── checkpoints/
    └── <app>/
        └── <app>.<index>.<weight>.gz
```

## Adding a new app

1. **Import its sysroot**, a directory tree that will appear as `/` to the program:

   ```bash
   riscv-simenv repo add sysroot 000.helloworld ./helloworld-rootfs
   ```

2. **Register the app.** Paths are as the program sees them inside the sysroot. A
   relative `--proxy-kernel` or `--stdin-redir` is resolved against `--init-cwd`.
   Everything after `--` is the program's command line.

   ```bash
   riscv-simenv repo add app register \
       --app-name 000.helloworld \
       --sysroot-name 000.helloworld \
       --proxy-kernel /boot/pk \
       --init-cwd /app \
       --memsize 256 \
       -- helloworld.rv64
   ```

   Add `--stdin-redir <file>` to feed a file to stdin, or `--copy-spawn` to always copy
   files into the simenv rather than symlink them.

3. **Do a bootstrap run.** This spawns the entire sysroot and runs the app under spike
   with a syscall trace:

   ```bash
   mkdir bootstrap && cd bootstrap
   riscv-simenv mkgen 000.helloworld --bootstrap
   make bootstrap-run
   ```

4. **Analyze the run.** This parses the syscall trace, hashes every path the app
   touched in the pristine and post-run sysroots, and records them in the manifest
   with the app's instruction count:

   ```bash
   make bootstrap-analyze
   ```

   The analysis refuses traces that contradict the filesystem. For example, it fails
   if a file's hash changed but the trace shows no write to it.

5. **Import checkpoints** (optional). Generate them with spike, e.g.
   `--make-checkpoint=<desc-file>`, then:

   ```bash
   riscv-simenv repo add checkpoint 000.helloworld ckpts/*.gz
   ```

`riscv-simenv repo show manifest` shows how far each app has got: `BASE` after
step 2, `FULL` after step 4.

## The manifest

```yaml
app_name: 000.helloworld
app_cmd: helloworld.rv64
app_init_cwd: /app
app_memsize: 256                 # MiB, passed as -m256
app_pristine_sysroot: 000.helloworld
app_proxy_kernel: /boot/pk
app_spawn_mode: link             # or "copy"
app_stdin_redir: ''
fs_access:                       # added by "repo add app analyze"
  /app/helloworld.rv64:
    hash:
      pre-run: 91c20d38...
      post-run: 91c20d38...
    usage: FUSE_READ_DATA | FUSE_OPEN_RD
instret:                         # added by "repo add app analyze"
- 1000000002
```

Each `usage` is a `|`-separated set of flags:

| Flag | Set when the path was... |
| --- | --- |
| `FUSE_OPEN_RD`, `FUSE_OPEN_WR`, `FUSE_OPEN_RW` | opened read-only, write-only, or read-write |
| `FUSE_READ_DATA` | read |
| `FUSE_WRITE_DATA` | written or truncated |
| `FUSE_STAT` | queried for metadata (`fstat`, `fstatat`, `faccessat`, ...) |
| `FUSE_CREATE` | created |
| `FUSE_REMOVE` | removed, or renamed away |
| `FUSE_ABS_REF` | referred to by an absolute path |

A path is copied into the simenv rather than symlinked if it is written, opened for
writing, or `stat`ed, since a symlink would report the wrong metadata.

A hash is a SHA-256 digest, `DIR` for a directory, `SKIP` for a path that isn't
checked (such as a device file), or `null` if the path doesn't exist at that point.
A file the app creates has `pre-run: null`.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `RISCV_SIMENV_REPO_PATH` | The repository to use. `--repo-path` overrides it. |
| `RISCV_SIMENV_SIM_CMD` | Simulator written into generated Makefiles. Default `spike`. |
| `RISCV_SIMENV_SIM_FLAG_LDCKPT` | Flag used to load a checkpoint. Default `-c`. |

## Caveats

- **A checkpoint depends on the memory size.** The simulator checks that the
  checkpoint's memory size matches `-m`, so changing `APP_MEMSIZE` breaks every
  checkpoint for that app.
- **A checkpoint depends on the simulator build.** Register state is stored as raw
  bytes, so rebuilding the simulator with a different configuration can invalidate
  existing checkpoints without any error.
- **Restoring replays syscalls.** A resumed run re-executes the program's earlier
  syscalls, so console output from before the checkpoint appears again, and loading
  a checkpoint takes longer the further into the program it is. Judge progress by
  instruction count, not by console output.
- **Checkpoints are single-core**, whatever `-p` is set to.
- **An empty `~/.config/simenv_repo` counts as a valid repository.** If your app list
  is unexpectedly empty, check that `RISCV_SIMENV_REPO_PATH` is set.

## License

BSD-style license from North Carolina State University. See
[LICENSE](https://github.com/s117/riscv-simenv/blob/main/LICENSE).
