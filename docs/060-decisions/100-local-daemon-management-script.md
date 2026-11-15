# 100. Local Daemon Management Script for Native Python

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

`d2-renderer` runs natively as standard-library Python (`python3 server.py`) alongside Docker and Google Cloud Run. The native footprint suits developer machines: about 26 MB of resident memory and about 100 ms to first healthy response, measured on the maintainer's Mac, with no container runtime.

Running the native server in the background has four problems:

- `python3 server.py` holds the terminal unless the user backgrounds it with `nohup ... &`.
- Stopping a background process by hand (`lsof -ti :8088 | xargs kill`) can kill unrelated processes that use the port.
- Desktop automations (macOS Shortcuts, Raycast, Alfred, VS Code tasks, cron) run with a minimal `PATH` (`/usr/bin:/bin`) and do not find Python 3.12 or `d2` without extra setup.
- `launchd` and `systemd` need unit files with absolute paths, which makes ad-hoc start, stop and toggle awkward.

## Decision

Provide `scripts/manage-daemon.sh`, a bash script with no dependencies beyond bash, curl, ps, kill, nohup and Python 3.12:

- **Commands:** `up`, `down`, `toggle`, `status`, `restart` and `logs`. `up` and `down` are idempotent.
- **Shell:** bash, not POSIX `sh`. The script avoids bash 4 features so it runs on the macOS system bash 3.2.
- **PATH recovery:** the script prepends `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin` and the Linuxbrew bin directory before it looks for Python and `d2`.
- **State:** PID and log files live in `$D2_STATE_DIR` (default `~/.d2-renderer/`), named by port, so the git working tree stays clean and several daemons can coexist.
- **Ownership:** the PID file is the only proof that the script started a process. If another process answers on the port, `up`, `down` and `toggle` report an error and never kill it. `status` reports it as unmanaged.
- **Shutdown:** `SIGTERM`, then `SIGKILL` after 3 seconds. The server keeps no state that needs a clean shutdown.
- **Exit codes:** `status` returns 0 when the server answers and 1 when it does not.
- **Location:** `scripts/`, so `server.py` and the `Dockerfile` remain the canonical entry points.

## Rejected

- **`run.sh` at the repository root:** it would rank a convenience helper with the primary entry points and confuse container-first users.
- **Wrapping Docker commands:** `docker run -d` and `docker stop` already provide this.
- **Python daemonizer packages (`daemonocle`, `supervisor`):** they break the rule of no dependencies beyond the standard library.
- **`launchd` or `systemd` alone:** they leave ad-hoc starts and one-command toggles without support. The `launchd` recipe stays in the [local Python guide](../010-setup/020-local-python.md) for persistent use.
- **Finding the process by port with `lsof`:** it can match clients and unrelated services, and `lsof` is not on a bare `PATH`.

## Consequences

- One command, `./scripts/manage-daemon.sh toggle`, starts or stops the server from any launcher.
- A start that fails reports the last log lines and leaves no PID file behind.
- The log file never rotates. Users delete it when it grows too large.
- `tests/test_manage_daemon.py` starts its own servers on free ports and runs in every CI job that runs `unittest discover`.

## Navigation

- [Decision index](./README.md)
