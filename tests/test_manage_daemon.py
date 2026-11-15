"""Unit and lifecycle integration tests for scripts/manage-daemon.sh.

Single-Line Summary:
    Exercises daemon start, stop, toggle, restart, idempotency, ownership and status exit codes.

Architectural Purpose:
    Verifies that the POSIX lifecycle manager script reliably controls native Python server
    subprocesses across all commands (up, down, toggle, status, restart, logs) without
    leaking state or leaving orphan background processes.

Approach & Invariants:
    1. Ephemeral Sandbox Isolation: Every test executes with an isolated ephemeral $D2_STATE_DIR
       and an ephemeral test port (default 8099) so test runs never interfere with host daemons.
    2. Strict Process Teardown: TearDown guarantees that any spawned background process is
       terminated and its socket released before subsequent test cases run.
    3. Observable Evidence: Asserts on process survival via kill(pid, 0), HTTP /health reachability,
       PID file existence, and exit codes (status=0 when running, status=1 when stopped).
    4. Self-contained: These tests start their own servers and need no external server, unlike
       tests/test_server.py.
"""

import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts", "manage-daemon.sh")


def get_free_port() -> int:
    """Finds an available TCP loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestManageDaemonScript(unittest.TestCase):
    """Exercises the lifecycle commands of scripts/manage-daemon.sh."""

    def setUp(self):
        """Prepares an isolated ephemeral state directory and test port."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_dir = self.temp_dir.name
        self.port = str(get_free_port())
        self.env = os.environ.copy()
        self.env["D2_STATE_DIR"] = self.state_dir
        self.env["PORT"] = self.port
        self.env["HOST"] = "127.0.0.1"
        self.pid_file = os.path.join(self.state_dir, f"d2-renderer-{self.port}.pid")

    def tearDown(self):
        """Ensures any leftover test daemon is cleanly terminated."""
        try:
            subprocess.run(
                [SCRIPT_PATH, "down"],
                env=self.env,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            pass
        self.temp_dir.cleanup()

    def run_cmd(self, cmd: str, env=None) -> subprocess.CompletedProcess:
        """Helper to invoke manage-daemon.sh with the test environment."""
        return subprocess.run(
            [SCRIPT_PATH, cmd],
            env=env or self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_01_status_when_stopped(self):
        """Verifies that status exits with code 1 and reports stopped when inactive."""
        res = self.run_cmd("status")
        self.assertEqual(res.returncode, 1)
        self.assertIn("STOPPED", res.stdout)

    def test_02_up_starts_daemon_and_responds_healthy(self):
        """Verifies that 'up' launches the daemon, creates PID file, and responds to /health."""
        res = self.run_cmd("up")
        self.assertEqual(res.returncode, 0, f"up failed: {res.stderr}")
        self.assertIn("started on", res.stdout)

        # Check PID file
        pid_file = self.pid_file
        self.assertTrue(os.path.isfile(pid_file))
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Verify process is alive
        try:
            os.kill(pid, 0)
        except OSError:
            self.fail(f"Process {pid} is not running")

        # Verify /health responds 200 OK
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib.request.urlopen(url, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read(), b"OK")

        # Verify status now returns 0
        status_res = self.run_cmd("status")
        self.assertEqual(status_res.returncode, 0)
        self.assertIn("RUNNING", status_res.stdout)
        self.assertIn(str(pid), status_res.stdout)

    def test_03_up_is_idempotent(self):
        """Verifies calling 'up' when already running returns 0 without restarting."""
        self.run_cmd("up")
        pid_file = self.pid_file
        with open(pid_file, "r") as f:
            initial_pid = f.read().strip()

        # Second call to 'up'
        res = self.run_cmd("up")
        self.assertEqual(res.returncode, 0)
        self.assertIn("already running", res.stdout)

        with open(pid_file, "r") as f:
            current_pid = f.read().strip()
        self.assertEqual(initial_pid, current_pid)

    def test_04_down_stops_daemon_and_is_idempotent(self):
        """Verifies 'down' terminates the process, removes PID file, and handles repeat calls."""
        self.run_cmd("up")
        pid_file = self.pid_file
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        res = self.run_cmd("down")
        self.assertEqual(res.returncode, 0)
        self.assertIn("stopped", res.stdout)
        self.assertFalse(os.path.isfile(pid_file))

        # Verify process actually terminated
        time.sleep(0.2)
        with self.assertRaises(OSError):
            os.kill(pid, 0)

        # Idempotency check: calling down when stopped
        res_repeat = self.run_cmd("down")
        self.assertEqual(res_repeat.returncode, 0)
        self.assertIn("not running", res_repeat.stdout)

    def test_05_toggle_switches_state(self):
        """Verifies 'toggle' alternates between running and stopped states."""
        # 1. Initially stopped -> toggle should start
        res1 = self.run_cmd("toggle")
        self.assertEqual(res1.returncode, 0)
        self.assertIn("started on", res1.stdout)
        self.assertEqual(self.run_cmd("status").returncode, 0)

        # 2. Currently running -> toggle should stop
        res2 = self.run_cmd("toggle")
        self.assertEqual(res2.returncode, 0)
        self.assertIn("stopped", res2.stdout)
        self.assertEqual(self.run_cmd("status").returncode, 1)

    def test_06_logs_outputs_content(self):
        """Verifies 'logs' reads from the log file without error."""
        self.run_cmd("up")
        # Generate a health hit to populate logs
        urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health").close()

        res = self.run_cmd("logs")
        self.assertEqual(res.returncode, 0)
        self.assertIn("/health", res.stdout)

    def test_07_restart_replaces_process(self):
        """Verifies 'restart' stops the old process and starts a new healthy one."""
        self.run_cmd("up")
        with open(self.pid_file) as f:
            old_pid = f.read().strip()
        res = self.run_cmd("restart")
        self.assertEqual(res.returncode, 0, res.stderr)
        with open(self.pid_file) as f:
            new_pid = f.read().strip()
        self.assertNotEqual(old_pid, new_pid)
        self.assertEqual(self.run_cmd("status").returncode, 0)

    def test_08_stale_pid_file_is_ignored(self):
        """Verifies a PID file naming an unrelated live process is not treated as the daemon."""
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))  # alive, but not server.py
        self.assertEqual(self.run_cmd("status").returncode, 1)
        down = self.run_cmd("down")
        self.assertEqual(down.returncode, 0)
        os.kill(os.getpid(), 0)  # the test process must survive 'down'

    def test_09_foreign_listener_is_never_killed(self):
        """Verifies 'down' and 'up' refuse to touch a server the script did not start."""

        class Health(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")

            def log_message(self, *args):
                pass

        foreign = HTTPServer(("127.0.0.1", int(self.port)), Health)
        thread = threading.Thread(target=foreign.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(self.run_cmd("status").returncode, 0)
            self.assertIn("unmanaged", self.run_cmd("status").stdout)
            self.assertEqual(self.run_cmd("down").returncode, 1)
            self.assertEqual(self.run_cmd("up").returncode, 1)
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as resp:
                self.assertEqual(resp.status, 200)  # foreign server still alive
        finally:
            foreign.shutdown()
            foreign.server_close()

    def test_10_failed_start_leaves_no_pid_file(self):
        """Verifies a server that dies at startup is reported and cleaned up."""
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", int(self.port)))
        blocker.listen(1)  # accepts connections but never answers /health
        try:
            res = self.run_cmd("up")
            self.assertEqual(res.returncode, 1)
            self.assertFalse(os.path.exists(self.pid_file))
        finally:
            blocker.close()

    def test_11_two_ports_share_one_state_dir(self):
        """Verifies state is keyed by port, so two daemons do not shadow each other."""
        other_env = dict(self.env, PORT=str(get_free_port()))
        try:
            self.assertEqual(self.run_cmd("up").returncode, 0)
            self.assertEqual(self.run_cmd("status", env=other_env).returncode, 1)
            self.assertEqual(self.run_cmd("up", env=other_env).returncode, 0)
            self.assertEqual(self.run_cmd("down").returncode, 0)
            self.assertEqual(self.run_cmd("status", env=other_env).returncode, 0)
        finally:
            self.run_cmd("down", env=other_env)

    def test_12_works_with_stripped_path(self):
        """Verifies 'up' finds Python under the bare PATH used by cron and Apple Shortcuts."""
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".local/bin/python3"),
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        usable = [
            c for c in candidates
            if os.path.exists(c)
            and subprocess.run([c, "-c", "import sys; sys.exit(sys.version_info < (3, 12))"]).returncode == 0
        ]
        if not usable:
            self.skipTest("no Python 3.12+ in the standard tool directories")
        env = dict(self.env, PATH="/usr/bin:/bin", HOME=home)
        res = self.run_cmd("up", env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.run_cmd("status", env=env).returncode, 0)

    def test_13_unknown_command_exits_nonzero(self):
        """Verifies an unknown subcommand prints usage to stderr and exits 1."""
        res = self.run_cmd("bogus")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Usage", res.stderr)


if __name__ == "__main__":
    unittest.main()
