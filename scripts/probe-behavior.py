#!/usr/bin/env python3
"""Probes one running d2-renderer and prints a behavior table, so two builds can be diffed.

Why: status codes in the unit suite say a build works; this script records HOW it behaves
at the HTTP edge (status-line shape, icon handling, error bodies). Run it against the
deployed service before a change and against the new build after, then compare outputs.

Usage:
    python3 scripts/probe-behavior.py <BASE_URL>      # e.g. http://localhost:8080

The probes are read-only and small: a dozen requests, no load.
"""

import base64
import http.client
import shutil
import socket
import subprocess
import sys
import urllib.parse
import zlib

# The pre-fix README example; kept here only to prove how a bad payload is answered.
BAD_PAYLOAD = "eNqLDslMSVTISyzJSVXIyS_PMFTIT1NIy89XKE7NSy3KL1JwBPI980oSc9MVghKT80tS01OKUqGGSnKLi0tKUsvy89A1pmfm5aCZAwD2Hhz_"
ICON_OK = "https://icons.terrastruct.com/essentials%2F092-graph%20bar.svg"


def encode(src: str) -> str:
    """Returns the URL-safe zlib+Base64 payload for D2 text."""
    return base64.urlsafe_b64encode(zlib.compress(src.encode(), 9)).decode()


def raw(base: str, method: str, path: str, body: bytes = b""):
    """Returns (status_line, headers_text, body) read straight from a socket."""
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


def post(base: str, d2: str, query: str = ""):
    """POSTs D2 text over a raw socket and returns (status_line, headers, body)."""
    return raw(base, "POST", "/d2/svg" + query, d2.encode())


def one_line(s: str) -> str:
    return s.replace("\n", "\\n")[:90]


def main(base: str):
    """Runs every probe against `base` and prints the behavior table."""
    rows = []

    def add(name, value):
        rows.append((name, value))

    s, _, b = raw(base, "GET", "/health")
    add("health", f"{s} body={b[:10]!r}")

    s, _, b = post(base, "a -> b")
    add("post simple", f"{s} svg={b[:4]!r}")

    s, _, b = post(base, "a -> b -> c", "?layout=tala")
    add("post tala", f"{s} svg={b[:4]!r}")

    s, h, b = post(base, "x -> -> y {")
    nl = "\n" in s or "\r" in s
    add("compile error status line", one_line(s))
    add("compile error body content-type", next((l for l in h.split("\r\n") if l.lower().startswith("content-type")), "n/a"))
    add("compile error body mentions compiler", b"failed to compile" in b or b"connection missing" in b)

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
        sys.exit(__doc__)
    main(sys.argv[1].rstrip("/"))
