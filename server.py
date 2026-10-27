#!/usr/bin/env python3
"""D2 Diagram Rendering HTTP Microservice.

A lightweight, zero-dependency HTTP server that compiles D2 diagram specifications
into SVG graphics on the fly. Supports Kroki-compatible GET URLs (deflate + base64url)
and raw POST payloads, with LRU memory caching and query-based styling options.
"""

import base64
import functools
import http.server
import re
import subprocess
import urllib.parse
import zlib
from typing import Tuple

PORT = 8080


@functools.lru_cache(maxsize=1024)
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
    """
    cmd = ["d2", "-", "-"]

    if sketch:
        cmd.append("--sketch")
    if theme:
        cmd.append(f"--theme={theme}")
    if layout:
        cmd.append(f"--layout={layout}")

    proc = subprocess.run(
        cmd,
        input=source_text.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    return proc.stdout


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
        # Validate theme is an integer ID or safe identifier
        if theme and not re.match(r"^[0-9a-zA-Z_-]+$", theme):
            theme = ""

        layout = query_params.get("layout", [""])[0]
        # Validate layout engine name
        if layout and not re.match(r"^[a-zA-Z0-9_-]+$", layout):
            layout = ""

        return sketch, theme, layout

    def _send_svg(self, svg_bytes: bytes, is_cached: bool = False):
        """Sends a 200 OK response with SVG content and caching headers."""
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("X-Cache", "HIT" if is_cached else "MISS")
        self.end_headers()
        self.wfile.write(svg_bytes)

    def do_GET(self):
        """Handles GET requests for health probes and encoded diagram URLs."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.strip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Health probe endpoint
        if path == "health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        # Diagram endpoint: /d2/svg/<encoded_string>
        parts = path.split("/")
        if len(parts) == 3 and parts[0] == "d2" and parts[1] == "svg":
            encoded_str = parts[2]
            try:
                # 1. Base64 URL-safe decode + zlib decompress
                compressed = base64.urlsafe_b64decode(encoded_str.encode("ascii"))
                d2_code = zlib.decompress(compressed).decode("utf-8")
            except Exception as err:
                self.send_error(400, f"Malformed encoded payload: {str(err)}")
                return

            sketch, theme, layout = self._parse_options(query_params)
            cache_info_before = compile_d2_cached.cache_info()

            try:
                svg = compile_d2_cached(d2_code, sketch, theme, layout)
                cache_info_after = compile_d2_cached.cache_info()
                is_cached = cache_info_after.hits > cache_info_before.hits
                self._send_svg(svg, is_cached=is_cached)
            except subprocess.CalledProcessError as err:
                self.send_error(400, f"D2 Compilation Error:\n{err.stderr.decode('utf-8', errors='replace')}")
            return

        self.send_error(404, "Not Found. Use /d2/svg/<encoded_string> or POST to /d2/svg")

    def do_POST(self):
        """Handles POST requests containing raw D2 script bodies."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.strip("/")
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == "d2/svg":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length <= 0:
                    self.send_error(400, "Empty request body")
                    return
                d2_code = self.rfile.read(content_length).decode("utf-8")
            except Exception as err:
                self.send_error(400, f"Failed to read request body: {str(err)}")
                return

            sketch, theme, layout = self._parse_options(query_params)
            cache_info_before = compile_d2_cached.cache_info()

            try:
                svg = compile_d2_cached(d2_code, sketch, theme, layout)
                cache_info_after = compile_d2_cached.cache_info()
                is_cached = cache_info_after.hits > cache_info_before.hits
                self._send_svg(svg, is_cached=is_cached)
            except subprocess.CalledProcessError as err:
                self.send_error(400, f"D2 Compilation Error:\n{err.stderr.decode('utf-8', errors='replace')}")
            return

        self.send_error(404, "Not Found. POST to /d2/svg")


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
