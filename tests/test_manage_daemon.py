#!/usr/bin/env bash
# Automated integration tests for scripts/manage-daemon.sh.
"""Unit and lifecycle integration tests for scripts/manage-daemon.sh.

Single-Line Summary:
    Exercises daemon start, stop, toggle, idempotency, and status exit codes in isolation.

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
"""

import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request

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

    def run_cmd(self, cmd: str) -> subprocess.CompletedProcess:
        """Helper to invoke manage-daemon.sh with the test environment."""
        return subprocess.run(
            [SCRIPT_PATH, cmd],
            env=self.env,
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
        pid_file = os.path.join(self.state_dir, "d2-renderer.pid")
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
        pid_file = os.path.join(self.state_dir, "d2-renderer.pid")
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
        pid_file = os.path.join(self.state_dir, "d2-renderer.pid")
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
        urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health")

        res = self.run_cmd("logs")
        self.assertEqual(res.returncode, 0)
        self.assertIn("/health", res.stdout)


if __name__ == "__main__":
    unittest.main()
