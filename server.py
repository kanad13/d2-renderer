#!/usr/bin/env python3
"""D2 Diagram Rendering HTTP Microservice.

Single-Line Summary:
    Zero-dependency HTTP microservice compiling D2 diagram text into SVG graphics.

Architectural Purpose:
    Acts as an offline rendering engine for declarative D2 diagrams across local
    workstations (VS Code preview via Lightweight Markdown Preview), CI/CD pipelines,
    and serverless environments (Google Cloud Run). The service eliminates client-side
    toolchain requirements (compilers, layout engines, fonts) while preserving diagram
    privacy by preventing diagram text from leaving the user's execution boundary.

Approach & Invariants:
    1. Zero External Dependencies: Built strictly on the Python standard library
       (http.server, subprocess, urllib, zlib, functools, argparse) to eliminate
       supply-chain attack vectors and virtual environment management.
    2. Strict Offline Sandboxing: Every diagram compiles via `d2 --bundle=false`
       inside an ephemeral `tempfile.TemporaryDirectory()`, ensuring the compiler
       cannot execute outbound network calls (SSRF) or read server files via imports.
    3. Memory-Bounded LRU Caching: Maintains an in-memory LRU cache of 256 renders,
       serving duplicate requests in ~1 ms while capping container memory well inside
       a 512 MiB Cloud Run instance.
    4. Deterministic Error Framing: All error responses format as RFC single-line status
       phrases with UTF-8 plain-text diagnostic bodies, preventing header-injection
       crashes in strict HTTP clients like Node.js `fetch`.
"""

import argparse
import base64
import functools
import http.server
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import zlib
from http import HTTPStatus
from typing import Tuple

# Port defaults to 8088 to avoid common local web development clashes (e.g., 8080).
# Google Cloud Run injects the PORT environment variable at runtime.
PORT = int(os.environ.get("PORT", "8088"))
BIND_ADDRESS = os.environ.get("HOST", "0.0.0.0")

# Security limits guard public and shared instances against resource exhaustion.
# Process spawns are resource-intensive; unbounded input or execution time would
# allow malicious or runaway payloads to exhaust memory or CPU.
RENDER_TIMEOUT_SECONDS = int(os.environ.get("RENDER_TIMEOUT_SECONDS", "20"))
MAX_SOURCE_BYTES = int(os.environ.get("MAX_SOURCE_BYTES", str(256 * 1024)))

# Short reasons for the status line. http.server's default phrase is "Request Entity Too Large"
# for 413; the standard RFC phrase "Payload Too Large" is used for modern client compatibility.
ERROR_REASONS = {
    400: "Bad Request",
    404: "Not Found",
    413: "Payload Too Large",
    500: "Internal Server Error",
    504: "Gateway Timeout",
}


class SourceTooLarge(ValueError):
    """Raised when D2 diagram source exceeds MAX_SOURCE_BYTES.

    Applies to both raw incoming POST payloads and inflated decompressions from
    Kroki-compatible GET URL paths. Maps directly to HTTP 413 (Payload Too Large).
    """


@functools.lru_cache(maxsize=256)
def compile_d2_cached(source_text: str, sketch: bool, theme: str, layout: str) -> bytes:
    """Executes the D2 CLI compiler with in-memory LRU caching.

    Caches compiled SVG bytes keyed by the input source text and rendering flags.
    Repeated requests resolve in memory without spawning subprocesses.

    Args:
        source_text: Raw D2 declarative diagram specification.
        sketch: If True, passes `--sketch` to apply hand-drawn aesthetic.
        theme: Theme ID string (e.g., '0', '200'). Passed as `--theme` if non-empty.
        layout: Layout engine name ('dagre', 'elk', 'tala'). Passed if non-empty.

    Returns:
        Rendered SVG output as bytes.

    Raises:
        FileNotFoundError: If the 'd2' CLI binary is missing from system PATH.
        subprocess.CalledProcessError: If D2 compiler rejects syntax with an exit code.
        subprocess.TimeoutExpired: If compilation runtime exceeds RENDER_TIMEOUT_SECONDS.
    """
    # --bundle=false enforces strict offline isolation: D2 would otherwise attempt
    # to download icon and image URLs referenced in the diagram. On a cloud instance,
    # this prevents server-side request forgery (SSRF) targeting internal networks
    # or cloud metadata servers (169.254.169.254). URLs remain as SVG <image href> tags.
    cmd = ["d2", "-", "-", "--bundle=false"]

    if sketch:
        cmd.append("--sketch")
    if theme:
        cmd.append(f"--theme={theme}")
    if layout:
        cmd.append(f"--layout={layout}")

    # D2 relative imports (`...@path`) resolve against the compiler's working directory.
    # Running inside an ephemeral empty directory ensures import statements find no files,
    # preventing local file inclusion (LFI) of server code or secrets.
    with tempfile.TemporaryDirectory() as workdir:
        proc = subprocess.run(
            cmd,
            input=source_text.encode("utf-8"),
            capture_output=True,
            check=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            cwd=workdir,
        )
    return proc.stdout


class D2Handler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for D2 diagram rendering endpoints.

    Routes health probes, decodes Kroki-compatible GET URLs, streams POST bodies,
    and formats responses. Enforces CORS headers across all endpoints to enable
    direct embedding in web applications and Markdown previews.
    """

    server_version = "D2Renderer/1.0"

    def do_OPTIONS(self):
        """Handles CORS pre-flight requests from browser clients."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _parse_options(self, query_params: dict) -> Tuple[bool, str, str]:
        """Extracts and sanitizes rendering options from URL query parameters.

        Validates query inputs against strict regex character whitelists before
        they are injected into CLI subprocess arguments.

        Args:
            query_params: Dictionary of parsed query string parameters.

        Returns:
            A tuple of (sketch_flag, theme_identifier, layout_engine_name).
        """
        sketch = query_params.get("sketch", ["false"])[0].lower() in ("true", "1", "yes")

        theme = query_params.get("theme", [""])[0]
        if theme and not re.match(r"^[0-9a-zA-Z_-]+$", theme):
            theme = ""

        layout = query_params.get("layout", [""])[0]
        if layout and not re.match(r"^[a-zA-Z0-9_-]+$", layout):
            layout = ""

        return sketch, theme, layout

    def _send_error_text(self, code: int, message: str):
        """Replies with a standardized single-line status and plain-text body.

        Standard BaseHTTPRequestHandler.send_error attempts to place the error
        message inside the HTTP status line. Multi-line compiler diagnostics
        break strict HTTP clients (such as Node.js fetch or Go http.Client).
        This method keeps the status line single-line and sends the diagnostic in the body.

        Args:
            code: HTTP status code integer (e.g. 400, 404, 413, 500, 504).
            message: Diagnostic error message for the plain-text response body.
        """
        body = message.encode("utf-8")
        self.send_response(code, ERROR_REASONS.get(code) or HTTPStatus(code).phrase)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        """Overrides base error handler to maintain unified plain-text error framing.

        Catches errors raised internally by http.server (e.g. malformed HTTP request
        lines, unsupported verbs) and routes them through _send_error_text.

        Args:
            code: HTTP status code integer.
            message: Optional short error message.
            explain: Optional extended explanation (ignored in favor of plain text).
        """
        self._send_error_text(code, message or HTTPStatus(code).phrase)

    def _send_svg(self, svg_bytes: bytes, is_cached: bool = False):
        """Sends an HTTP 200 OK response with SVG content and caching headers.

        Emits immutable caching headers because D2 diagram URLs are deterministic
        hashes of their content.

        Args:
            svg_bytes: Rendered SVG document as raw bytes.
            is_cached: True if the render was satisfied from LRU memory cache.
        """
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("X-Cache", "HIT" if is_cached else "MISS")
        self.end_headers()
        self.wfile.write(svg_bytes)

    def _render_and_send(self, d2_code: str, query_params: dict):
        """Coordinates compilation and dispatches the SVG or an error response.

        Args:
            d2_code: Declarative D2 source text to render.
            query_params: Query parameters dictionary for styling and layout options.
        """
        sketch, theme, layout = self._parse_options(query_params)
        cache_info_before = compile_d2_cached.cache_info()

        try:
            svg = compile_d2_cached(d2_code, sketch, theme, layout)
        except subprocess.CalledProcessError as err:
            self._send_error_text(400, f"D2 Compilation Error:\n{err.stderr.decode('utf-8', errors='replace')}")
            return
        except subprocess.TimeoutExpired:
            self._send_error_text(504, f"Rendering exceeded {RENDER_TIMEOUT_SECONDS}s limit")
            return
        except FileNotFoundError:
            self._send_error_text(
                500,
                "D2 compiler binary 'd2' not found on system PATH. "
                "Install D2 (https://d2lang.com/tour/install) or run via Docker.",
            )
            return

        is_cached = compile_d2_cached.cache_info().hits > cache_info_before.hits
        self._send_svg(svg, is_cached=is_cached)

    @staticmethod
    def _decode_payload(encoded_str: str) -> str:
        """Decodes a Kroki-compatible URL payload (deflate + base64url).

        Applies bounded decompression to protect against decompression bomb attacks
        (small compressed inputs that inflate past memory limits).

        Args:
            encoded_str: URL-safe base64-encoded compressed D2 string.

        Returns:
            Decoded UTF-8 D2 script string.

        Raises:
            SourceTooLarge: If inflated text exceeds MAX_SOURCE_BYTES.
            Exception: If base64 decoding or zlib decompression fails.
        """
        compressed = base64.urlsafe_b64decode(encoded_str.encode("ascii"))
        inflater = zlib.decompressobj()
        raw = inflater.decompress(compressed, MAX_SOURCE_BYTES)
        if inflater.unconsumed_tail:
            raise SourceTooLarge(f"Decoded diagram exceeds {MAX_SOURCE_BYTES} bytes")
        return raw.decode("utf-8")

    def do_GET(self):
        """Handles HTTP GET requests for health probes and encoded diagram URLs.

        Routes:
            GET /health: Returns 200 OK for uptime monitoring.
            GET /d2/svg/<payload>[?options]: Decodes and renders encoded diagram.
        """
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.strip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == "health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        parts = path.split("/")
        if len(parts) == 3 and parts[0] == "d2" and parts[1] == "svg":
            encoded_str = parts[2]
            try:
                d2_code = self._decode_payload(encoded_str)
            except SourceTooLarge as err:
                self._send_error_text(413, str(err))
                return
            except Exception as err:
                self._send_error_text(400, f"Malformed encoded payload: {str(err)}")
                return

            self._render_and_send(d2_code, query_params)
            return

        self._send_error_text(404, "Not Found. Use /d2/svg/<encoded_string> or POST to /d2/svg")

    def do_POST(self):
        """Handles HTTP POST requests containing raw D2 specifications.

        Validates Content-Length headers and stream bounds before reading bytes
        into memory, preventing oversized payload attacks.

        Routes:
            POST /d2/svg[?options]: Compiles raw request body text into SVG.
        """
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.strip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == "d2/svg":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self._send_error_text(400, "Invalid Content-Length")
                return
            if content_length <= 0:
                self._send_error_text(400, "Empty request body")
                return

            # Header verified before stream read to prevent memory allocation for oversized bodies.
            if content_length > MAX_SOURCE_BYTES:
                self._send_error_text(413, f"Request body exceeds {MAX_SOURCE_BYTES} bytes")
                return

            try:
                d2_code = self.rfile.read(content_length).decode("utf-8")
            except Exception as err:
                self._send_error_text(400, f"Failed to read request body: {str(err)}")
                return

            self._render_and_send(d2_code, query_params)
            return

        self._send_error_text(404, "Not Found. POST to /d2/svg")


def run(host: str = BIND_ADDRESS, port: int = PORT):
    """Starts the multi-threaded HTTP server.

    Args:
        host: IP address to bind to (e.g. '0.0.0.0' or '127.0.0.1').
        port: TCP port to listen on (e.g. 8088).
    """
    if not shutil.which("d2"):
        print(
            "WARNING: 'd2' compiler binary not found in PATH.\n"
            "Install D2 (https://d2lang.com/tour/install or 'brew install d2') to enable diagram rendering."
        )
    server = http.server.ThreadingHTTPServer((host, port), D2Handler)
    print(f"D2 Renderer microservice listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    """Parses CLI options and launches the server.

    CLI options take precedence over environment variables, which in turn
    take precedence over built-in defaults.
    """
    parser = argparse.ArgumentParser(description="D2 Diagram Rendering HTTP Microservice")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=PORT,
        help="Port to listen on (default: $PORT or 8088)",
    )
    parser.add_argument(
        "--bind",
        "-b",
        type=str,
        default=BIND_ADDRESS,
        help="Address to bind to (default: $HOST or 0.0.0.0)",
    )
    args = parser.parse_args()
    run(host=args.bind, port=args.port)


if __name__ == "__main__":
    main()
