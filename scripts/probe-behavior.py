#!/usr/bin/env python3
"""Probes a running d2-renderer instance and prints an observable behavior matrix.

Single-Line Summary:
    Executes behavioral probes over raw sockets to verify HTTP framing and security invariants.

Architectural Purpose:
    Unit tests confirm functional pass/fail status; this script captures *how* the service
    behaves at the HTTP boundary (RFC status line format, header casing, error body content-type,
    SSRF icon safety, and Node.js fetch compatibility). Running this probe against target builds
    ensures behavioral parity between local Docker, bare-metal Python, and Cloud Run deployments.

Approach & Invariants:
    1. Raw Socket Framing: Uses bare socket connections to inspect exact byte framing,
       proving status lines contain no raw newlines that would crash strict HTTP parsers.
    2. Security Invariant Probing: Tests offline compilation invariants by submitting
       diagrams with private/cloud metadata icon URLs (169.254.169.254, metadata.google.internal).
    3. Strict Client Validation: Executes Node.js `fetch` in a child process to prove
       compatibility with real-world strict JavaScript runtimes.
"""

import base64
import http.client
import shutil
import socket
import subprocess
import sys
from typing import Tuple
import urllib.parse
import zlib

# The pre-fix README example; kept here only to prove how a bad payload is answered.
BAD_PAYLOAD = "eNqLDslMSVTISyzJSVXIyS_PMFTIT1NIy89XKE7NSy3KL1JwBPI980oSc9MVghKT80tS01OKUqGGSnKLi0tKUsvy89A1pmfm5aCZAwD2Hhz_"
ICON_OK = "https://icons.terrastruct.com/essentials%2F092-graph%20bar.svg"


def encode(src: str) -> str:
    """Encodes raw D2 text into a URL-safe deflate-compressed base64 payload.

    Args:
        src: Declarative D2 script string.

    Returns:
        URL-safe base64 string matching the Kroki format.
    """
    return base64.urlsafe_b64encode(zlib.compress(src.encode(), 9)).decode()


def raw(base: str, method: str, path: str, body: bytes = b"") -> Tuple[str, str, bytes]:
    """Sends raw bytes over a TCP socket and returns parsed HTTP response parts.

    Args:
        base: Target server base URL (e.g. 'http://localhost:8088').
        method: HTTP verb ('GET', 'POST', 'OPTIONS').
        path: HTTP request path including query strings.
        body: Raw bytes to send in the request body.

    Returns:
        A tuple of (status_line_string, headers_text, body_bytes).
    """
    u = urllib.parse.urlparse(base)
    port = u.port or (443 if u.scheme == "https" else 80)
    sock = socket.create_connection((u.hostname, port), timeout=30)
    if u.scheme == "https":
        import ssl

        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=u.hostname)
    req = f"{method} {path} HTTP/1.1\r\nHost: {u.netloc}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    sock.sendall(req.encode() + body)
    data = b""
    while chunk := sock.recv(65536):
        data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    first, _, hdrs = head.decode("latin-1").partition("\r\n")
    return first, hdrs, rest


def post(base: str, d2: str, query: str = "") -> Tuple[str, str, bytes]:
    """Sends a POST request with D2 diagram text over a raw socket.

    Args:
        base: Target server base URL.
        d2: Raw D2 script text.
        query: Optional URL query string (e.g. '?layout=tala').

    Returns:
        A tuple of (status_line_string, headers_text, body_bytes).
    """
    return raw(base, "POST", "/d2/svg" + query, d2.encode())


def one_line(s: str) -> str:
    """Truncates and formats multi-line text into a single loggable string.

    Args:
        s: Input text string.

    Returns:
        Single-line formatted string truncated to 90 characters.
    """
    return s.replace("\n", "\\n")[:90]


def main(base: str):
    """Executes behavioral probe suite against target base URL and prints results.

    Args:
        base: Base URL of the running d2-renderer instance (e.g. 'http://localhost:8088').
    """
    rows = []

    def add(name: str, value: str):
        rows.append((name, value))

    s, _, b = raw(base, "GET", "/health")
    add("health", f"{s} body={b[:10]!r}")

    s, _, b = post(base, "a -> b")
    add("post simple", f"{s} svg={b[:4]!r}")

    s, _, b = post(base, "a -> b -> c", "?layout=tala")
    add("post tala", f"{s} svg={b[:4]!r}")

    s, h, b = post(base, "x -> -> y {")
    add("compile error status line", one_line(s))
    add("compile error body content-type", next((l for l in h.split("\r\n") if l.lower().startswith("content-type")), "n/a"))
    add("compile error body mentions compiler", str(b"failed to compile" in b or b"connection missing" in b))

    s, _, _ = raw(base, "GET", "/d2/svg/not!valid")
    add("malformed payload status line", one_line(s))
    s, _, _ = raw(base, "GET", "/nope")
    add("404 status line", one_line(s))

    s, _, _ = raw(base, "GET", f"/d2/svg/{BAD_PAYLOAD}")
    add("pre-fix README payload", one_line(s))

    if shutil.which("node"):
        url = f"{base}/d2/svg/{encode('x -> -> y {')}"
        js = ("fetch(process.argv[1]).then(r=>r.text()).then(t=>console.log('OK',t.slice(0,40).replace(/\\n/g,' ')))"
              ".catch(e=>console.log('FAIL',e.cause?.message||e.message))")
        out = subprocess.run(["node", "-e", js, url], capture_output=True, text=True, timeout=60).stdout.strip()
        add("node fetch on compile error", out)
    else:
        add("node fetch on compile error", "skipped (node not installed)")

    s, _, b = post(base, f"x: X {{ icon: {ICON_OK} }}")
    add("icon public host", f"{s} embedded_data_uri={b'data:image' in b} remote_href={b'href=\"https://icons' in b}")

    for label, host in [("icon cloud metadata name", "http://metadata.google.internal/computeMetadata/v1/a.svg"),
                        ("icon loopback literal", "http://127.0.0.1:9/a.svg"),
                        ("icon link-local literal", "http://169.254.169.254/a.svg")]:
        s, _, b = post(base, f"x: X {{ icon: {host} }}")
        first = b.decode("utf-8", "replace").strip().splitlines()
        add(label, f"{s} | {one_line(first[-1] if first else '')}")

    w = max(len(n) for n, _ in rows)
    print(f"target: {base}")
    for n, v in rows:
        print(f"{n:<{w}}  {v}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <BASE_URL>  # e.g. http://localhost:8088")
    main(sys.argv[1].rstrip("/"))
