#!/usr/bin/env bash
# Local Daemon Lifecycle Management Script for d2-renderer.
#
# Single-Line Summary:
#     POSIX shell daemon supervisor managing background native Python server processes.
#
# Architectural Purpose:
#     Bridges the operational gap between interactive foreground execution (`python3 server.py`)
#     and heavyweight OS supervisors (`launchd` / `systemd`). Enables non-interactive desktop
#     automations (Apple Shortcuts, Raycast, Alfred, VS Code tasks, shell aliases) to start,
#     stop, toggle, or query the local rendering microservice on bare metal without holding
#     a terminal shell hostage.
#
# Approach & Invariants:
#     1. Zero External Dependencies: Relies solely on POSIX utilities (sh, curl, ps, kill, nohup)
#        and standard Python stdlib without virtualenv or process supervisor packages.
#     2. Ephemeral State Isolation: Keeps state files (.pid and .log) in $D2_STATE_DIR (default:
#        ~/.d2-renderer/) to prevent dirty working trees in git repositories.
#     3. Stripped-PATH Resilience: Dynamically queries standard runtime roots ($HOME/.local/bin,
#        Homebrew prefixes, /usr/local/bin) so non-login GUI shells find Python and d2.
#     4. Standard Daemon Exit Codes: 'status' returns 0 when healthy and 1 when stopped.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${PORT:-8088}"
HOST="${HOST:-127.0.0.1}"
STATE_DIR="${D2_STATE_DIR:-$HOME/.d2-renderer}"
PID_FILE="$STATE_DIR/d2-renderer.pid"
LOG_FILE="$STATE_DIR/d2-renderer.log"

# Non-interactive desktop launchers (Apple Shortcuts, GUI hotkeys) execute with a bare PATH
# (/usr/bin:/bin). Prepend standard binary locations dynamically.
resolve_system_path() {
  local extra_paths=()
  [ -d "$HOME/.local/bin" ] && extra_paths+=("$HOME/.local/bin")
  [ -d "/opt/homebrew/bin" ] && extra_paths+=("/opt/homebrew/bin")
  [ -d "/usr/local/bin" ] && extra_paths+=("/usr/local/bin")
  [ -d "/home/linuxbrew/.linuxbrew/bin" ] && extra_paths+=("/home/linuxbrew/.linuxbrew/bin")

  if command -v brew >/dev/null 2>&1; then
    local brew_bin
    brew_bin="$(brew --prefix 2>/dev/null)/bin" || true
    [ -n "$brew_bin" ] && [ -d "$brew_bin" ] && extra_paths+=("$brew_bin")
  fi

  local joined_extra=""
  for p in "${extra_paths[@]}"; do
    joined_extra="${joined_extra}${p}:"
  done
  export PATH="${joined_extra}${PATH:-}"
}

resolve_system_path

find_python() {
  local py
  for py in python3.12 python3.13 python3.11 python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if command -v "$py" >/dev/null 2>&1; then
      if "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
        command -v "$py"
        return 0
      fi
    fi
  done
  echo "Error: Python 3.9+ standard library interpreter not found." >&2
  return 1
}

find_d2() {
  if command -v d2 >/dev/null 2>&1; then
    command -v d2
    return 0
  fi
  for loc in "$HOME/.local/bin/d2" "/opt/homebrew/bin/d2" "/usr/local/bin/d2" "/home/linuxbrew/.linuxbrew/bin/d2"; do
    if [ -x "$loc" ]; then
      echo "$loc"
      return 0
    fi
  done
  return 1
}

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      if ps -p "$pid" -o command= 2>/dev/null | grep -q "server.py"; then
        return 0
      fi
    fi
  fi
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

start_daemon() {
  mkdir -p "$STATE_DIR"

  if is_running; then
    local pid=""
    [ -f "$PID_FILE" ] && pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    echo "d2-renderer is already running on http://${HOST}:${PORT}${pid:+ (PID: $pid)}"
    return 0
  fi

  local python_bin
  python_bin="$(find_python)"

  if ! find_d2 >/dev/null 2>&1; then
    echo "WARNING: 'd2' compiler binary not found in PATH." >&2
    echo "Install D2 (https://d2lang.com/tour/install or 'brew install d2') to enable diagram rendering." >&2
  fi

  (
    cd "$REPO_DIR"
    nohup "$python_bin" "$REPO_DIR/server.py" --port "$PORT" --bind "$HOST" </dev/null >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
  )

  local new_pid
  new_pid="$(cat "$PID_FILE")"

  # Poll health probe to verify process initialized and bound to the port
  local ready=0
  for _ in {1..30}; do
    if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.1
  done

  if [ "$ready" -eq 1 ]; then
    echo "d2-renderer started on http://${HOST}:${PORT} (PID: $new_pid)"
    return 0
  else
    echo "Error: d2-renderer failed to respond on http://${HOST}:${PORT}/health within 3s. Check logs at $LOG_FILE" >&2
    return 1
  fi
}

stop_daemon() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "d2-renderer is not running."
    return 0
  fi

  local pid=""
  if [ -f "$PID_FILE" ]; then
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  fi

  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in {1..30}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    # Find orphan listener PID if PID file was purged or outdated
    local port_pids
    if command -v lsof >/dev/null 2>&1; then
      port_pids="$(lsof -ti ":$PORT" 2>/dev/null || true)"
      if [ -n "$port_pids" ]; then
        kill $port_pids 2>/dev/null || true
      fi
    fi
  fi

  rm -f "$PID_FILE"
  echo "d2-renderer stopped."
  return 0
}

toggle_daemon() {
  if is_running; then
    stop_daemon
  else
    start_daemon
  fi
}

status_daemon() {
  if is_running; then
    local pid=""
    [ -f "$PID_FILE" ] && pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    echo "d2-renderer is RUNNING on http://${HOST}:${PORT}${pid:+ (PID: $pid)}"
    return 0
  else
    echo "d2-renderer is STOPPED."
    return 1
  fi
}

show_logs() {
  mkdir -p "$STATE_DIR"
  touch "$LOG_FILE"
  tail -n "${LINES_COUNT:-50}" "$LOG_FILE"
}

case "${1:-up}" in
  up|start)
    start_daemon
    ;;
  down|stop)
    stop_daemon
    ;;
  toggle)
    toggle_daemon
    ;;
  status)
    status_daemon
    ;;
  restart)
    stop_daemon
    sleep 0.5
    start_daemon
    ;;
  logs)
    show_logs
    ;;
  help|-h|--help)
    echo "Usage: ./scripts/manage-daemon.sh [up|down|toggle|status|restart|logs]"
    ;;
  *)
    echo "Unknown command: $1" >&2
    echo "Usage: ./scripts/manage-daemon.sh [up|down|toggle|status|restart|logs]" >&2
    exit 1
    ;;
esac
