#!/usr/bin/env python3
"""Builds render-check/index.html: visual verification page across configured servers.

Single-Line Summary:
    Generates a local HTML matrix rendering test diagrams against local and remote servers.

Architectural Purpose:
    Provides human and coding agent visual verification of rendered SVGs. HTTP 200
    responses confirm network and process execution, but cannot verify whether text
    is clipped, fonts are rendered accurately, or sketch and theme flags apply visibly.

Approach & Invariants:
    1. Comprehensive Test Cases: Exercises all exposed D2 features (dagre, elk, tala,
       sketch mode, dark/light themes, SQL tables, nested containers, unicode).
    2. Side-by-Side Comparison: Pairs local (Docker or host) and remote (Cloud Run)
       images side-by-side to detect rendering regressions or font discrepancies.
    3. Browser Self-Testing: Injected client-side JavaScript measures natural image
       dimensions and reports broken images directly in the browser UI.
"""

import argparse
import base64
import html
import os
import pathlib
from typing import Dict, List, Tuple
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Test cases covering core features: (title, d2_source, query_string).
INLINE_CASES = [
    ("Ping / pong", "x -> y: Ping\ny -> x: Pong", ""),
    ("Cylinder shape", "database: Customer DB {\n  shape: cylinder\n}", ""),
    ("Sketch mode", "client -> server: Request\nserver -> db: Query", "?sketch=true"),
    ("Theme 200 (dark mauve)", "client -> server: Request\nserver -> db: Query", "?theme=200"),
    ("Sketch + theme 4", "a -> b -> c -> a: loop", "?sketch=true&theme=4"),
    ("ELK layout", "direction: right\na -> b -> c\na -> c\nb -> d", "?layout=elk"),
    (
        "TALA layout (bundled since D2 v0.9.0)",
        "client -> gateway -> auth\ngateway -> orders -> db\norders -> payments -> db\nauth -> db",
        "?layout=tala",
    ),
    (
        "Same graph, dagre layout",
        "client -> gateway -> auth\ngateway -> orders -> db\norders -> payments -> db\nauth -> db",
        "?layout=dagre",
    ),
    (
        "SQL table",
        "users: {\n  shape: sql_table\n  id: int {constraint: primary_key}\n  email: varchar\n}\n"
        "orders: {\n  shape: sql_table\n  id: int {constraint: primary_key}\n  user_id: int {constraint: foreign_key}\n}\n"
        "orders.user_id -> users.id",
        "",
    ),
    (
        "Containers and unicode",
        "Cloud: {\n  api: API\n  worker: Worker\n  api -> worker: queue\n}\nUser: Käyttäjä 🙂\nUser -> Cloud.api",
        "",
    ),
]


def encode(source: str) -> str:
    """Encodes raw D2 source into a URL-safe deflate-compressed base64 payload.

    Args:
        source: Raw D2 declarative diagram script.

    Returns:
        URL-safe base64 string matching the Kroki encoding format.
    """
    return base64.urlsafe_b64encode(zlib.compress(source.encode("utf-8"), 9)).decode("ascii")


def collect_cases() -> List[Tuple[str, str, str]]:
    """Gathers all inline test cases and sample diagram files from docs/090-examples/.

    Returns:
        List of (case_title, d2_source_text, query_string) tuples.
    """
    cases = list(INLINE_CASES)
    for path in sorted((ROOT / "docs" / "090-examples").glob("*.d2")):
        cases.append((f"090-examples/{path.name}", path.read_text(encoding="utf-8"), ""))
    return cases


def build(servers: Dict[str, str]) -> str:
    """Assembles the complete HTML verification matrix document.

    Args:
        servers: Mapping of column labels (e.g. 'local') to base URLs.

    Returns:
        Full HTML document string ready to be written to disk.
    """
    rows = []
    for title, source, query in collect_cases():
        encoded = encode(source)
        cells = []
        for label, base in servers.items():
            url = f"{base.rstrip('/')}/d2/svg/{encoded}{query}"
            cells.append(
                f'<div class="cell"><div class="tag">{html.escape(label)}'
                f'<span class="status">loading</span></div>'
                f'<img src="{html.escape(url)}" alt="{html.escape(title)} ({html.escape(label)})"></div>'
            )
        rows.append(
            f'<section><h2>{html.escape(title)} <code>{html.escape(query)}</code></h2>'
            f'<div class="row">{"".join(cells)}</div></section>'
        )
    return PAGE.replace("{{BODY}}", "\n".join(rows))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>d2-renderer render check</title>
<style>
  body { font: 14px system-ui, sans-serif; margin: 24px; background: #fafafa; color: #222; }
  h1 { margin-top: 0; } h2 { font-size: 15px; margin: 24px 0 8px; }
  code { background: #eee; padding: 1px 5px; border-radius: 3px; }
  .row { display: flex; gap: 16px; flex-wrap: wrap; }
  .cell { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 8px; flex: 1 1 420px; min-width: 0; }
  .tag { font-size: 11px; text-transform: uppercase; color: #666; margin-bottom: 4px; display: flex; justify-content: space-between; }
  .cell img { max-width: 100%; height: auto; display: block; border: 1px dashed #eee; }
  .cell.bad { border-color: #d93025; background: #fce8e6; }
  .cell.ok { border-color: #1e8e3e; }
  .status { font-weight: bold; }
  #summary { font-size: 16px; margin: 12px 0 24px; padding: 8px 12px; border-radius: 4px; display: inline-block; }
  #summary.ok { background: #e6f4ea; color: #137333; }
  #summary.bad { background: #fce8e6; color: #c5221f; }
</style></head><body>
<h1>d2-renderer visual render check</h1>
<div id="summary" class="bad">running checks…</div>
{{BODY}}
<script>
  const imgs = Array.from(document.querySelectorAll('.cell img'));
  let pending = imgs.length;
  let bad = 0;
  const finish = () => {
    const s = document.getElementById('summary');
    if (bad === 0) {
      s.className = 'ok';
      s.textContent = `ALL ${imgs.length} RENDERS PASSED`;
    } else {
      s.className = 'bad';
      s.textContent = `${bad} OF ${imgs.length} RENDERS FAILED`;
    }
  };
  imgs.forEach(img => {
    const cell = img.closest('.cell');
    const status = cell.querySelector('.status');
    const done = ok => {
      cell.classList.add(ok ? 'ok' : 'bad');
      status.textContent = ok ? `loaded ${img.naturalWidth}x${img.naturalHeight}` : 'FAILED';
      if (!ok) bad++;
      if (--pending === 0) finish();
    };
    if (img.complete) done(img.naturalWidth > 0);
    else { img.onload = () => done(true); img.onerror = () => done(false); }
  });
</script></body></html>
"""


def main():
    """CLI entry point for generating render-check/index.html."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", default="http://localhost:8088", help="Local renderer URL (default: http://localhost:8088)")
    parser.add_argument("--remote", default=os.environ.get("RENDERER_REMOTE_URL", ""), help="Remote renderer URL")
    args = parser.parse_args()

    servers = {"local": args.local}
    if args.remote:
        servers["remote (Cloud Run)"] = args.remote

    out_dir = ROOT / "render-check"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(build(servers), encoding="utf-8")
    print(f"wrote {out} ({len(servers)} server column(s))")


if __name__ == "__main__":
    main()
