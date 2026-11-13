#!/usr/bin/env python3
"""Automated integration test suite for D2 Diagram Rendering Microservice.

Single-Line Summary:
    Comprehensive integration test suite exercising HTTP endpoints, limits, and security boundaries.

Architectural Purpose:
    Proves functional correctness, security sandboxing, caching efficiency, and error
    framing of d2-renderer against running local containers, host processes, or remote
    deployments. Guarantees that clients (Lightweight Markdown Preview in VS Code,
    curl scripts, browser <img> tags) receive deterministic, well-formed SVGs and errors.

Approach & Invariants:
    1. End-to-End HTTP Boundary Testing: Tests exercise full HTTP request-response cycles,
       validating RFC status lines, CORS headers, Content-Type, and cache headers.
    2. Raw Socket Framing Probes: Socket-level byte reads verify that error responses
       adhere to single-line status phrases without raw newline leaks.
    3. Security Sandboxing Verification: Starts isolated test servers with mock compilers
       to assert offline compilation (`--bundle=false`) and empty working directories.
    4. Documentation Parity: Programmatically decodes every D2 payload across repository
       Markdown files to guarantee published examples never drift from the live engine.
"""

import base64
import http.client
import http.server
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import List, Tuple
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib

TARGET_URL = os.environ.get("TEST_TARGET_URL", "http://127.0.0.1:8088")
# Address of this host as visible from within the Docker container under test.
# Docker Desktop routes through host.docker.internal; set TEST_STANDIN_HOST when testing elsewhere.
STANDIN_HOST = os.environ.get("TEST_STANDIN_HOST", "host.docker.internal")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def encode_d2(d2_text: str) -> str:
    """Compresses and base64url encodes D2 text into a Kroki-compatible string.

    Args:
        d2_text: Raw declarative D2 diagram text.

    Returns:
        URL-safe base64 string representation.
    """
    compressed = zlib.compress(d2_text.encode("utf-8"), 9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def raw_exchange(host: str, port: int, request: bytes) -> Tuple[str, str, str]:
    """Transmits raw bytes over a TCP socket and parses the HTTP response framing.

    Standard libraries (urllib, http.client) automatically sanitize status line
    formatting. Bare socket inspection is required to prove that status lines
    strictly conform to RFC single-line specifications.

    Args:
        host: Hostname or IP of the target HTTP server.
        port: TCP port of the target HTTP server.
        request: Full HTTP request wire bytes.

    Returns:
        A tuple of (status_line, headers_text, body_text).
    """
    with socket.create_connection((host, port), timeout=15) as sock:
        sock.sendall(request)
        data = b""
        while chunk := sock.recv(65536):
            data += chunk
    head, _, body = data.partition(b"\r\n\r\n")
    status_line, _, headers = head.decode("latin-1").partition("\r\n")
    return status_line, headers, body.decode("utf-8", errors="replace")


def post_request(path: str, body: bytes) -> bytes:
    """Builds raw HTTP/1.1 POST wire bytes with accurate Content-Length header.

    Args:
        path: Request URL path.
        body: Raw payload bytes.

    Returns:
        Encoded HTTP/1.1 POST request bytes.
    """
    return (f"POST {path} HTTP/1.1\r\nHost: t\r\nContent-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n").encode() + body


def get_request(path: str) -> bytes:
    """Builds raw HTTP/1.1 GET wire bytes requesting connection termination.

    Args:
        path: Request URL path.

    Returns:
        Encoded HTTP/1.1 GET request bytes.
    """
    return f"GET {path} HTTP/1.1\r\nHost: t\r\nConnection: close\r\n\r\n".encode()


class TestD2Server(unittest.TestCase):
    """Integration test suite executing against a running target server."""

    @classmethod
    def setUpClass(cls):
        """Ensures the local output directory exists for test artifact inspection."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _http_get(self, path: str):
        """Dispatches an HTTP GET request to the target server under test.

        Args:
            path: Relative URL path.

        Returns:
            HTTP response object from urllib.request.urlopen.
        """
        url = urllib.parse.urljoin(TARGET_URL, path)
        req = urllib.request.Request(url)
        return urllib.request.urlopen(req, timeout=10)

    def _http_post(self, path: str, body: str):
        """Dispatches an HTTP POST request carrying plain text to the target server.

        Args:
            path: Relative URL path.
            body: Plain text string payload.

        Returns:
            HTTP response object from urllib.request.urlopen.
        """
        url = urllib.parse.urljoin(TARGET_URL, path)
        data = body.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "text/plain"})
        return urllib.request.urlopen(req, timeout=10)

    def test_01_health_check(self):
        """Verifies GET /health returns 200 OK with expected CORS headers."""
        res = self._http_get("/health")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.read(), b"OK")
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "*")

    def test_02_get_simple_diagram(self):
        """Verifies GET /d2/svg/<encoded> renders a valid SVG diagram."""
        d2_code = "x -> y: Hello World"
        encoded = encode_d2(d2_code)
        res = self._http_get(f"/d2/svg/{encoded}")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.headers.get("Content-Type"), "image/svg+xml; charset=utf-8")
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "*")
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("Hello World", svg_content)

    def test_03_get_sketch_mode(self):
        """Verifies ?sketch=true produces a valid sketch-styled SVG."""
        d2_code = "a -> b: Sketchy"
        encoded = encode_d2(d2_code)
        res_standard = self._http_get(f"/d2/svg/{encoded}")
        svg_standard = res_standard.read().decode("utf-8")

        res_sketch = self._http_get(f"/d2/svg/{encoded}?sketch=true")
        self.assertEqual(res_sketch.status, 200)
        svg_sketch = res_sketch.read().decode("utf-8")
        self.assertIn("</svg>", svg_sketch)
        self.assertNotEqual(svg_standard, svg_sketch)

    def test_04_get_theme(self):
        """Verifies ?theme=200 applies a custom theme."""
        d2_code = "a -> b: Themed"
        encoded = encode_d2(d2_code)
        res = self._http_get(f"/d2/svg/{encoded}?theme=200")
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)

    def test_05_post_raw_diagram(self):
        """Verifies POST /d2/svg accepts raw body text and returns SVG."""
        d2_code = "user -> db: Query records"
        res = self._http_post("/d2/svg", d2_code)
        self.assertEqual(res.status, 200)
        self.assertEqual(res.headers.get("Content-Type"), "image/svg+xml; charset=utf-8")
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("Query records", svg_content)

    def test_06_render_example_architecture(self):
        """Verifies rendering of the full architecture.d2 example file."""
        example_path = os.path.join(os.path.dirname(__file__), "..", "docs", "090-examples", "architecture.d2")
        with open(example_path, "r", encoding="utf-8") as f:
            d2_code = f.read()
        res = self._http_post("/d2/svg", d2_code)
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("Microservice Architecture", svg_content)
        with open(os.path.join(OUTPUT_DIR, "architecture_rendered.svg"), "w", encoding="utf-8") as out:
            out.write(svg_content)

    def test_07_render_example_sequence(self):
        """Verifies rendering of the full sequence.d2 example file."""
        example_path = os.path.join(os.path.dirname(__file__), "..", "docs", "090-examples", "sequence.d2")
        with open(example_path, "r", encoding="utf-8") as f:
            d2_code = f.read()
        res = self._http_post("/d2/svg", d2_code)
        self.assertEqual(res.status, 200)
        svg_content = res.read().decode("utf-8")
        self.assertIn("</svg>", svg_content)
        self.assertIn("OAuth Provider", svg_content)
        self.assertIn("User Database", svg_content)
        with open(os.path.join(OUTPUT_DIR, "sequence_rendered.svg"), "w", encoding="utf-8") as out:
            out.write(svg_content)

    def test_08_lru_caching(self):
        """Verifies in-memory LRU cache serves hits on duplicate requests."""
        unique_token = str(uuid.uuid4())
        d2_code = f"cache_{unique_token} -> hit_{unique_token}: test"
        encoded = encode_d2(d2_code)

        res1 = self._http_get(f"/d2/svg/{encoded}")
        self.assertEqual(res1.status, 200)
        self.assertEqual(res1.headers.get("X-Cache"), "MISS")

        res2 = self._http_get(f"/d2/svg/{encoded}")
        self.assertEqual(res2.status, 200)
        self.assertEqual(res2.headers.get("X-Cache"), "HIT")

    def test_09_invalid_base64_returns_400(self):
        """Verifies malformed base64 strings return HTTP 400 Bad Request."""
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_get("/d2/svg/this_is_not_valid_deflate_base64!!!")
        self.assertEqual(ctx.exception.code, 400)

    def test_10_invalid_d2_syntax_returns_400(self):
        """Verifies invalid D2 syntax triggers HTTP 400 with compiler error message."""
        bad_syntax = "invalid syntax { unclosed bracket"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_post("/d2/svg", bad_syntax)
        self.assertEqual(ctx.exception.code, 400)
        body = ctx.exception.read().decode("utf-8")
        self.assertIn("D2", body)

    def test_11_unmatched_route_returns_404(self):
        """Verifies unmatched routes return HTTP 404 Not Found."""
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_get("/non_existent_endpoint")
        self.assertEqual(ctx.exception.code, 404)

    def test_12_oversized_post_returns_413(self):
        """Verifies a declared body above the limit is refused before any body is read."""
        parsed = urllib.parse.urlparse(TARGET_URL)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
        conn.putrequest("POST", "/d2/svg")
        conn.putheader("Content-Length", str(50 * 1024 * 1024))
        conn.endheaders()
        res = conn.getresponse()
        self.assertEqual(res.status, 413)
        conn.close()

    def test_13_decompression_bomb_returns_413(self):
        """Verifies a tiny payload that inflates past the limit is refused."""
        bomb = encode_d2("a" * (5 * 1024 * 1024))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._http_get(f"/d2/svg/{bomb}")
        self.assertEqual(ctx.exception.code, 413)


class TestWellFormedErrors(unittest.TestCase):
    """Verifies that all error responses maintain RFC single-line status formatting."""

    HOST = urllib.parse.urlparse(TARGET_URL).hostname
    PORT = urllib.parse.urlparse(TARGET_URL).port

    def assert_well_formed(self, request: bytes, code: int, reason: str, body_contains: str):
        """Asserts socket response status line format and content-type headers.

        Args:
            request: Full request wire bytes.
            code: Expected HTTP status code integer.
            reason: Expected HTTP status reason string.
            body_contains: Substring expected in the response body.
        """
        status_line, headers, body = raw_exchange(self.HOST, self.PORT, request)
        self.assertRegex(status_line, rf"^HTTP/1\.[01] {code} {reason}$")
        self.assertIn("text/plain; charset=utf-8", headers)
        self.assertIn(body_contains, body)

    def test_15_compile_error_post(self):
        """Verifies D2 compilation failure on POST returns formatted 400 Bad Request."""
        self.assert_well_formed(post_request("/d2/svg", b"x -> -> y {"), 400, "Bad Request", "failed to compile")

    def test_16_compile_error_get(self):
        """Verifies D2 compilation failure on GET returns formatted 400 Bad Request."""
        path = f"/d2/svg/{encode_d2('x -> -> y {')}"
        self.assert_well_formed(get_request(path), 400, "Bad Request", "failed to compile")

    def test_17_malformed_payload_get(self):
        """Verifies invalid base64 URL payload returns formatted 400 Bad Request."""
        self.assert_well_formed(get_request("/d2/svg/not!valid"), 400, "Bad Request", "Malformed encoded payload")

    def test_18_empty_post_body(self):
        """Verifies empty POST body returns formatted 400 Bad Request."""
        self.assert_well_formed(post_request("/d2/svg", b""), 400, "Bad Request", "Empty request body")

    def test_19_not_found_get_and_post(self):
        """Verifies unknown endpoint returns formatted 404 Not Found."""
        self.assert_well_formed(get_request("/nope"), 404, "Not Found", "Not Found")
        self.assert_well_formed(post_request("/nope", b"a"), 404, "Not Found", "Not Found")

    def test_20_payload_too_large(self):
        """Verifies oversized POST and decompression bomb return formatted 413 Payload Too Large."""
        too_big = (f"POST /d2/svg HTTP/1.1\r\nHost: t\r\nContent-Length: {50 * 1024 * 1024}\r\n"
                   "Connection: close\r\n\r\n").encode()
        self.assert_well_formed(too_big, 413, "Payload Too Large", "exceeds")
        bomb = f"/d2/svg/{encode_d2('a' * (5 * 1024 * 1024))}"
        self.assert_well_formed(get_request(bomb), 413, "Payload Too Large", "exceeds")

    def test_26_unsupported_method_uses_the_same_format(self):
        """Verifies unsupported HTTP methods return formatted 501 Not Implemented."""
        status_line, headers, body = raw_exchange(
            self.HOST, self.PORT, b"PUT /d2/svg HTTP/1.1\r\nHost: t\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        self.assertRegex(status_line, r"^HTTP/1\.[01] 501 Not Implemented$")
        self.assertIn("text/plain; charset=utf-8", headers)
        self.assertIn("Unsupported method", body)

    def test_21_http_client_reads_error_body(self):
        """Verifies standard library HTTP client successfully reads multi-line compiler errors."""
        conn = http.client.HTTPConnection(self.HOST, self.PORT, timeout=10)
        conn.request("POST", "/d2/svg", body=b"x -> -> y {")
        res = conn.getresponse()
        self.assertEqual((res.status, res.reason), (400, "Bad Request"))
        self.assertIn("failed to compile", res.read().decode("utf-8"))
        conn.close()


class RecordingServer:
    """Mock HTTP server that records request paths to test SSRF invariants."""

    def __enter__(self):
        """Starts the mock HTTP server on an ephemeral loopback port."""
        hits = self.hits = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.end_headers()
                self.wfile.write(b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"/>')

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        """Shuts down and releases server resources."""
        self.httpd.shutdown()
        self.httpd.server_close()


class TestOfflineCompile(unittest.TestCase):
    """Verifies that compilation runs strictly offline without outbound network calls."""

    def test_22_icon_urls_trigger_no_outbound_request(self):
        """Verifies that icon URLs referenced in diagrams trigger zero outbound requests."""
        with RecordingServer() as icon_host:
            url = f"http://{STANDIN_HOST}:{icon_host.port}/a.svg"
            req = urllib.request.Request(urllib.parse.urljoin(TARGET_URL, "/d2/svg"),
                                         data=f"x: X {{ icon: {url} }}".encode(),
                                         headers={"Content-Type": "text/plain"})
            res = urllib.request.urlopen(req, timeout=15)
            svg = res.read().decode("utf-8")
            time.sleep(0.5)
            self.assertEqual(res.status, 200)
            self.assertEqual(icon_host.hits, [])
            self.assertIn(f'<image href="{url}"', svg)

    def test_23_private_and_metadata_icon_urls_still_render(self):
        """Verifies diagrams with loopback, link-local, and cloud metadata icon URLs compile safely."""
        for url in ("http://127.0.0.1:9/a.svg", "http://169.254.169.254/a.svg",
                    "http://metadata.google.internal/computeMetadata/v1/a.svg"):
            req = urllib.request.Request(urllib.parse.urljoin(TARGET_URL, "/d2/svg"),
                                         data=f"x: X {{ icon: {url} }}".encode(),
                                         headers={"Content-Type": "text/plain"})
            started = time.monotonic()
            res = urllib.request.urlopen(req, timeout=15)
            self.assertEqual(res.status, 200, url)
            self.assertLess(time.monotonic() - started, 5, url)

    def test_24_compile_runs_offline_in_an_empty_directory(self):
        """Verifies compiler executes with --bundle=false in an empty temporary directory."""
        server_path = os.path.join(os.path.dirname(__file__), "..", "server.py")
        with tempfile.TemporaryDirectory() as bin_dir:
            fake_d2 = os.path.join(bin_dir, "d2")
            with open(fake_d2, "w", encoding="utf-8") as f:
                f.write('#!/bin/sh\ncat >/dev/null\n'
                        'printf \'<svg>args=%s pwd=%s entries=%s</svg>\' "$*" "$(pwd)" "$(ls -A | wc -l | tr -d " ")"\n')
            os.chmod(fake_d2, os.stat(fake_d2).st_mode | stat.S_IEXEC)

            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"], PORT=str(port))
            server = subprocess.Popen([sys.executable, server_path], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                base = f"http://127.0.0.1:{port}"
                for _ in range(50):
                    try:
                        urllib.request.urlopen(base + "/health", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    self.fail("test server did not start")
                req = urllib.request.Request(base + "/d2/svg", data=b"...@secret",
                                             headers={"Content-Type": "text/plain"})
                out = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
                self.assertIn("--bundle=false", out)
                self.assertIn("entries=0", out)
                self.assertNotIn(os.path.realpath(os.path.dirname(server_path)), out)
            finally:
                server.terminate()
                server.wait(timeout=5)


class TestDocumentedPayloads(unittest.TestCase):
    """Verifies that every encoded diagram published in documentation decodes and renders."""

    ROOT = os.path.join(os.path.dirname(__file__), "..")
    URL_PAYLOAD = re.compile(r"/d2/svg/([A-Za-z0-9_=-]{16,})")
    BARE_PAYLOAD = re.compile(r"^\s*([A-Za-z0-9_-]{60,}=*)\s*$", re.MULTILINE)

    def documented_payloads(self) -> List[Tuple[str, str]]:
        """Scans Markdown documentation files to locate all embedded D2 URL payloads.

        Returns:
            List of (file_path, base64_payload_string) tuples.
        """
        found = []
        paths = [os.path.join(self.ROOT, "README.md")]
        for folder in ("docs",):
            for dirpath, _, names in os.walk(os.path.join(self.ROOT, folder)):
                paths += [os.path.join(dirpath, n) for n in names if n.endswith(".md")]
        for path in paths:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for match in self.URL_PAYLOAD.findall(text) + self.BARE_PAYLOAD.findall(text):
                found.append((os.path.relpath(path, self.ROOT), match))
        return found

    def test_25_every_documented_payload_renders(self):
        """Verifies that each discovered documentation payload compiles successfully to SVG."""
        payloads = self.documented_payloads()
        self.assertGreaterEqual(len(payloads), 1)
        sources = []
        for path, payload in payloads:
            with self.subTest(file=path, payload=payload[:24]):
                source = zlib.decompress(base64.urlsafe_b64decode(payload)).decode("utf-8")
                sources.append(source.strip())
                self.assertTrue(source.strip())
                res = urllib.request.urlopen(f"{TARGET_URL}/d2/svg/{payload}", timeout=15)
                self.assertEqual(res.status, 200)
                self.assertIn("</svg>", res.read().decode("utf-8"))

    def test_27_api_example_encodes_the_visible_source(self):
        """Verifies that the GET URL payload in the API reference encodes docs/090-examples/hello.d2."""
        with open(os.path.join(self.ROOT, "docs", "090-examples", "hello.d2"), encoding="utf-8") as f:
            hello = f.read().strip()
        decoded = [zlib.decompress(base64.urlsafe_b64decode(p)).decode("utf-8").strip()
                   for path, p in self.documented_payloads() if path.endswith("020-api-reference.md")]
        self.assertIn(hello, decoded)


class TestDocumentationDiagrams(unittest.TestCase):
    """Verifies that static committed SVGs match fresh compiler output."""

    def test_28_committed_diagrams_are_current(self):
        """Verifies that all committed SVGs and embedded doc blocks match current renders."""
        import importlib.util

        script = os.path.join(os.path.dirname(__file__), "..", "scripts", "build-doc-diagrams.py")
        spec = importlib.util.spec_from_file_location("build_doc_diagrams", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.check_all(TARGET_URL), 0)


class TestRenderTimeout(unittest.TestCase):
    """Verifies that runaway renders exceeding RENDER_TIMEOUT_SECONDS abort with HTTP 504."""

    def test_14_slow_render_returns_504(self):
        """Verifies that a stalled compilation process aborts with 504 Gateway Timeout."""
        server_path = os.path.join(os.path.dirname(__file__), "..", "server.py")
        with tempfile.TemporaryDirectory() as bin_dir:
            fake_d2 = os.path.join(bin_dir, "d2")
            with open(fake_d2, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\nexec sleep 30\n")
            os.chmod(fake_d2, os.stat(fake_d2).st_mode | stat.S_IEXEC)

            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]

            env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"],
                       PORT=str(port), RENDER_TIMEOUT_SECONDS="1")
            server = subprocess.Popen([sys.executable, server_path], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                base = f"http://127.0.0.1:{port}"
                for _ in range(50):
                    try:
                        urllib.request.urlopen(base + "/health", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    self.fail("test server did not start")

                started = time.monotonic()
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    req = urllib.request.Request(base + "/d2/svg", data=b"a -> b",
                                                 headers={"Content-Type": "text/plain"})
                    urllib.request.urlopen(req, timeout=10)
                self.assertEqual(ctx.exception.code, 504)
                self.assertLess(time.monotonic() - started, 10)

                status_line, headers, body = raw_exchange("127.0.0.1", port, post_request("/d2/svg", b"a -> b"))
                self.assertRegex(status_line, r"^HTTP/1\.[01] 504 Gateway Timeout$")
                self.assertIn("text/plain; charset=utf-8", headers)
                self.assertIn("limit", body)
            finally:
                server.terminate()
                server.wait(timeout=5)


class TestHostRuntimeErgonomics(unittest.TestCase):
    """Verifies CLI flag ergonomics and error handling when running server.py directly on host."""

    def test_29_missing_d2_binary_returns_500(self):
        """Verifies that an environment missing 'd2' returns a formatted HTTP 500 status."""
        server_path = os.path.join(os.path.dirname(__file__), "..", "server.py")
        with tempfile.TemporaryDirectory() as empty_bin_dir:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]

            env = dict(os.environ, PATH=empty_bin_dir, PORT=str(port))
            server = subprocess.Popen([sys.executable, server_path], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                base = f"http://127.0.0.1:{port}"
                for _ in range(50):
                    try:
                        urllib.request.urlopen(base + "/health", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    self.fail("test server did not start")

                status_line, headers, body = raw_exchange("127.0.0.1", port, post_request("/d2/svg", b"a -> b"))
                self.assertRegex(status_line, r"^HTTP/1\.[01] 500 Internal Server Error$")
                self.assertIn("text/plain; charset=utf-8", headers)
                self.assertIn("D2 compiler binary 'd2' not found on system PATH", body)
            finally:
                server.terminate()
                server.wait(timeout=5)

    def test_30_cli_arguments_override_port_and_host(self):
        """Verifies CLI arguments --port and --bind take precedence over defaults."""
        server_path = os.path.join(os.path.dirname(__file__), "..", "server.py")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

        server = subprocess.Popen([sys.executable, server_path, "--port", str(port), "--bind", "127.0.0.1"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    res = urllib.request.urlopen(base + "/health", timeout=1)
                    self.assertEqual(res.status, 200)
                    self.assertEqual(res.read(), b"OK")
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                self.fail("test server did not start with CLI arguments")
        finally:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
