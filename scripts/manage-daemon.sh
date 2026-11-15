#!/usr/bin/env bash
# Local daemon lifecycle manager for d2-renderer.
#
# Single-Line Summary:
#     Bash script that starts, stops, toggles and inspects the native Python server in the background.
#
# Architectural Purpose:
#     Fills the gap between `python3 server.py` (holds a terminal) and launchd/systemd (static
#     unit files with absolute paths). Lets non-interactive launchers (Apple Shortcuts, Raycast,
#     Alfred, cron, VS Code tasks) control the server with one command.
#
# Approach & Invariants:
#     1. Bash 3.2 compatible (the macOS system bash). No dependencies beyond bash, curl, ps,
#        kill, nohup and a Python 3.12+ interpreter.
#     2. State lives outside the repository, in $D2_STATE_DIR (default ~/.d2-renderer/), so the
#        git working tree stays clean. Files are keyed by port, so one state directory can hold
#        several daemons.
#     3. Stripped-PATH resilience: cron and Shortcuts run with PATH=/usr/bin:/bin, so common tool
#        directories are prepended before any lookup.
#     4. Ownership: the PID file is the only proof that the script started a process. A server
#        that answers /health without a matching PID file is reported but never killed.
#     5. Exit codes: `status` returns 0 when the server answers and 1 when it does not.
#
# Environment:
#     PORT (8088), HOST (127.0.0.1), D2_STATE_DIR (~/.d2-renderer), LOG_LINES (50, for `logs`).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT="${PORT:-8088}"
HOST="${HOST:-127.0.0.1}"
STATE_DIR="${D2_STATE_DIR:-$HOME/.d2-renderer}"
PID_FILE="$STATE_DIR/d2-renderer-$PORT.pid"
LOG_FILE="$STATE_DIR/d2-renderer-$PORT.log"
HEALTH_URL="http://${HOST}:${PORT}/health"
USAGE="Usage: $0 [up|down|toggle|status|restart|logs]"

# Prepend common tool directories. Plain string building avoids the empty-array failure
# that `set -u` causes in bash 3.2.
prepend_tool_dirs() {
  local dir extra=""
  for dir in "$HOME/.local/bin" /opt/homebrew/bin /usr/local/bin /home/linuxbrew/.linuxbrew/bin; do
    [ -d "$dir" ] && extra="${extra}${dir}:"
  done
  export PATH="${extra}${PATH:-/usr/bin:/bin}"
}
prepend_tool_dirs

# server.py documents Python 3.12 as the supported floor, so the script enforces the same.
find_python() {
  local py
  for py in python3.13 python3.12 python3; do
    if command -v "$py" >/dev/null 2>&1 &&
      "$py" -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
      command -v "$py"
      return 0
    fi
  done
  echo "Error: Python 3.12 or newer not found on PATH." >&2
  return 1
}

# Echo the PID from the PID file when it names a live server.py process; fail otherwise.
managed_pid() {
  local pid
  [ -f "$PID_FILE" ] || return 1
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  # Guards against PID reuse after a reboot or crash.
  ps -p "$pid" -o command= 2>/dev/null | grep -q "server.py" || return 1
  echo "$pid"
}

# True when something answers /health on the port, whoever started it.
port_answers() {
  curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1
}

start_daemon() {
  local pid
  mkdir -p "$STATE_DIR"

  if pid="$(managed_pid)"; then
    echo "d2-renderer is already running on http://${HOST}:${PORT} (PID: $pid)"
    return 0
  fi
  rm -f "$PID_FILE"

  if port_answers; then
    echo "Error: another process already answers on http://${HOST}:${PORT}. Not started by this script; stop it or set PORT." >&2
    return 1
  fi

  local python_bin
  python_bin="$(find_python)"

  if ! command -v d2 >/dev/null 2>&1; then
    echo "WARNING: 'd2' not found on PATH; /health works but rendering returns 500." >&2
    echo "Install D2 (https://d2lang.com/tour/install or 'brew install d2')." >&2
  fi

  (
    cd "$REPO_DIR"
    nohup "$python_bin" "$REPO_DIR/server.py" --port "$PORT" --bind "$HOST" </dev/null >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
  )
  pid="$(cat "$PID_FILE")"

  # Wait up to 3 s. Stop early if the process dies (for example, port already bound).
  local _
  for _ in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || break
    if port_answers; then
      echo "d2-renderer started on http://${HOST}:${PORT} (PID: $pid)"
      return 0
    fi
    sleep 0.1
  done

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  echo "Error: d2-renderer did not become healthy on ${HEALTH_URL}. Last log lines:" >&2
  tail -n 5 "$LOG_FILE" >&2 || true
  return 1
}

stop_daemon() {
  local pid _
  if ! pid="$(managed_pid)"; then
    rm -f "$PID_FILE"
    if port_answers; then
      echo "Error: a process not started by this script answers on port ${PORT}. Refusing to stop it." >&2
      return 1
    fi
    echo "d2-renderer is not running."
    return 0
  fi

  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  # Last resort after 3 s; the server holds no state that needs a clean shutdown.
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true

  rm -f "$PID_FILE"
  echo "d2-renderer stopped."
}

toggle_daemon() {
  if managed_pid >/dev/null; then
    stop_daemon
  else
    start_daemon
  fi
}

status_daemon() {
  local pid
  if pid="$(managed_pid)"; then
    echo "d2-renderer is RUNNING on http://${HOST}:${PORT} (PID: $pid)"
  elif port_answers; then
    echo "A server answers on http://${HOST}:${PORT} but was not started by this script (RUNNING, unmanaged)."
  else
    echo "d2-renderer is STOPPED."
    return 1
  fi
}

show_logs() {
  [ -f "$LOG_FILE" ] || { echo "No log file at $LOG_FILE" >&2; return 1; }
  tail -n "${LOG_LINES:-50}" "$LOG_FILE"
}

case "${1:-up}" in
  up|start) start_daemon ;;
  down|stop) stop_daemon ;;
  toggle) toggle_daemon ;;
  status) status_daemon ;;
  restart)
    stop_daemon
    start_daemon
    ;;
  logs) show_logs ;;
  help|-h|--help) echo "$USAGE" ;;
  *)
    echo "Unknown command: $1" >&2
    echo "$USAGE" >&2
    exit 1
    ;;
esac
