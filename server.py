#!/usr/bin/env python3
"""D2 Diagram Rendering HTTP Microservice.

A lightweight, zero-dependency HTTP server that compiles D2 diagram specifications
into SVG graphics on the fly. Supports Kroki-compatible GET URLs (deflate + base64url)
and raw POST payloads, with LRU memory caching and query-based styling options.

The service is meant to sit on the public internet behind <img> tags, so it has no
authentication. Instead, every render is bounded: input size (MAX_SOURCE_BYTES),
runtime (RENDER_TIMEOUT_SECONDS) and cache size are capped so one caller cannot exhaust
a small instance. Cloud Run adds the remaining caps (concurrency, instance count).
"""

import base64
import functools
import http.server
import os
import re
import subprocess
import tempfile
import urllib.parse
import zlib
from typing import Tuple

# Cloud Run injects PORT; 8080 keeps local and Docker runs unchanged.
PORT = int(os.environ.get("PORT", "8080"))

# Limits exist because the service is public: each render spawns a process, so
# unbounded input or runtime would let one caller exhaust a small free-tier instance.
RENDER_TIMEOUT_SECONDS = int(os.environ.get("RENDER_TIMEOUT_SECONDS", "20"))
MAX_SOURCE_BYTES = int(os.environ.get("MAX_SOURCE_BYTES", str(256 * 1024)))


class SourceTooLarge(ValueError):
    """Raised when D2 source (raw or decompressed) exceeds MAX_SOURCE_BYTES."""


# 256 entries keeps worst-case cache memory well inside a 512 MiB instance.
@functools.lru_cache(maxsize=256)
def compile_d2_cached(source_text: str, sketch: bool, theme: str, layout: str) -> bytes:
    """Executes the D2 CLI compiler with caching.

    Args:
        source_text: Raw D2 declarative diagram script.
        sketch: If True, renders with hand-drawn aesthetic (--sketch).
        theme: Theme ID string (e.g., '0', '200'). Ignored if empty.
        layout: Layout engine name (e.g., 'dagre', 'elk'). Ignored if empty.

    Returns:
        Rendered SVG output as bytes.

    Raises:
        subprocess.CalledProcessError: If D2 compiler fails.
        subprocess.TimeoutExpired: If rendering exceeds RENDER_TIMEOUT_SECONDS.
    """
    # --bundle=false keeps the compiler offline: D2 would otherwise download every icon or
    # image URL a diagram names, which on a public instance means fetching attacker-chosen
    # addresses (private ranges, the cloud metadata server). The SVG keeps the URLs as
    # <image href> references, so a viewer's own browser decides what to load.
    cmd = ["d2", "-", "-", "--bundle=false"]

    if sketch:
        cmd.append("--sketch")
    if theme:
        cmd.append(f"--theme={theme}")
    if layout:
        cmd.append(f"--layout={layout}")

    # D2 imports (`...@name`) resolve against the working directory. An empty directory per
    # compile means a diagram can import nothing from the server's own files.
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


# Short reasons for the status line. http.server's own table says "Request Entity Too Large"
# for 413; the current RFC name is used instead.
ERROR_REASONS = {400: "Bad Request", 404: "Not Found", 413: "Payload Too Large", 504: "Gateway Timeout"}


class D2Handler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for D2 diagram rendering."""

    server_version = "D2Renderer/1.0"

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _parse_options(self, query_params: dict) -> Tuple[bool, str, str]:
        """Extracts and sanitizes rendering options from query parameters."""
        sketch = query_params.get("sketch", ["false"])[0].lower() in ("true", "1", "yes")

        theme = query_params.get("theme", [""])[0]
        # Theme and layout flow into the d2 command line, so only safe identifier characters pass.
        if theme and not re.match(r"^[0-9a-zA-Z_-]+$", theme):
            theme = ""

        layout = query_params.get("layout", [""])[0]
        if layout and not re.match(r"^[a-zA-Z0-9_-]+$", layout):
            layout = ""

        return sketch, theme, layout

    def _send_error_text(self, code: int, message: str):
        """Replies with the standard one-line reason and the full message as a plain-text body.

        BaseHTTPRequestHandler.send_error would put `message` in the status line, and a
        multi-line compiler message there breaks strict HTTP clients such as Node's fetch.
        """
        body = message.encode("utf-8")
        self.send_response(code, ERROR_REASONS[code])
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_svg(self, svg_bytes: bytes, is_cached: bool = False):
        """Sends a 200 OK response with SVG content and caching headers."""
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("X-Cache", "HIT" if is_cached else "MISS")
        self.end_headers()
        self.wfile.write(svg_bytes)

    def _render_and_send(self, d2_code: str, query_params: dict):
        """Compiles D2 source (cache-aware) and sends the SVG or an error response."""
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

        is_cached = compile_d2_cached.cache_info().hits > cache_info_before.hits
        self._send_svg(svg, is_cached=is_cached)

    @staticmethod
    def _decode_payload(encoded_str: str) -> str:
        """Decodes a Kroki-style payload, refusing inputs that inflate past the source limit."""
        compressed = base64.urlsafe_b64decode(encoded_str.encode("ascii"))
        inflater = zlib.decompressobj()
        raw = inflater.decompress(compressed, MAX_SOURCE_BYTES)
        if inflater.unconsumed_tail:
            raise SourceTooLarge(f"Decoded diagram exceeds {MAX_SOURCE_BYTES} bytes")
        return raw.decode("utf-8")

    def do_GET(self):
        """Handles GET requests for health probes and encoded diagram URLs."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.strip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == "health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
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
        """Handles POST requests containing raw D2 script bodies."""
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
            # Checked before reading so an oversized body never enters memory.
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


def run(port: int = PORT):
    """Starts the threaded HTTP server."""
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), D2Handler)
    print(f"D2 Renderer microservice listening on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
