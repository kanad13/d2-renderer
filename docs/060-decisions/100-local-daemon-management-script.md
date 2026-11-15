# 100. Local Daemon Management Script for Native Python

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

`d2-renderer` supports running on bare metal via native standard-library Python (`python3 server.py`) alongside Docker and Google Cloud Run. This native execution footprint is desirable on developer machines because it consumes minimal resources (~26 MB RAM, 0% CPU at idle, sub-80 ms startup) without requiring Docker Desktop or container runtimes.

However, running the native Python server locally introduced operational ergonomics friction:

- `python3 server.py` runs in the foreground, holding the terminal window hostage unless manually backgrounded with `nohup ... &`.
- Stopping a backgrounded process required manual `lsof -ti :8088 | xargs kill`, which is error-prone.
- Desktop automations (macOS Shortcuts, Raycast, Alfred, VS Code task bindings) execute in non-interactive environments where `$PATH` is minimal (`/usr/bin:/bin`), failing to locate Python 3 or `d2` without boilerplate environment exports.
- Full operating system supervisors (`launchd` on macOS, `systemd` user services on Linux) require editing static XML or unit files with hardcoded paths, making ad-hoc start/stop/toggle awkward.

## Decision

Provide a portable, zero-dependency lifecycle script at `scripts/manage-daemon.sh` to manage native background server processes:

- **Commands:** Provides idempotent `up`, `down`, `toggle`, `status`, `restart`, and `logs` subcommands.
- **Portability:** Written in POSIX-compliant shell; runs identically across macOS and Linux with zero hardcoded paths.
- **Dynamic environment recovery:** In non-login shells (such as macOS Shortcuts), dynamically discovers `python3` and `d2` compiler locations across standard runtime paths (`$HOME/.local/bin`, Homebrew prefixes, `/usr/local/bin`).
- **State isolation:** Stores process state in `$D2_STATE_DIR` (default: `~/.d2-renderer/`), keeping repository working trees clean and avoiding git dirty-state collisions.
- **Scope boundary:** The script lives in `scripts/`, preserving `server.py` and `Dockerfile` as the canonical root repository entrypoints.

## Rejected

- **Placing `run.sh` at the repository root:** Over-elevates a convenience helper to a primary project contract and risks confusing container-first users.
- **Wrapping Docker commands in the script:** Redundant; `docker run -d` and `docker stop` already provide built-in cross-platform daemon control.
- **Adding Python daemonizer dependencies (e.g., `daemonocle`, `supervisor`):** Violates the architectural invariant of strictly zero external dependencies beyond the Python standard library.
- **Relying solely on `launchd` / `systemd`:** Leaves desktop automations and ad-hoc local testing without a lightweight one-command toggle.

## Consequences

- Local users and automation tools can start, stop, or toggle `d2-renderer` on bare metal using a single command: `./scripts/manage-daemon.sh toggle`.
- Non-login runners (Apple Shortcuts, cron, GUI hotkeys) execute reliably without manual `$PATH` configuration.
- The repository root remains clean and unpolluted.
- Standard daemon exit codes are preserved (`status` returns 0 when healthy, 1 when stopped).

## Navigation

- [Decision index](./README.md)
