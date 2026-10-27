#!/usr/bin/env python3
"""Builds render-check/index.html: every sample diagram, rendered by each configured server.

The page exists so a human or coding agent can LOOK at the output. A 200 status proves the
service answered; only a screenshot proves labels are not clipped and options visibly work.

Usage:
    python3 scripts/build-render-check.py [--local URL] [--remote URL]

Remote defaults to the RENDERER_REMOTE_URL environment variable; omit it to render only
the local column. Output is git-ignored.
"""

import argparse
import base64
import html
import os
import pathlib
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (title, d2 source, query string). Inline cases cover each feature the service exposes.
INLINE_CASES = [
    ("Ping / pong", "x -> y: Ping\ny -> x: Pong", ""),
    ("Cylinder shape", "database: Customer DB {\n  shape: cylinder\n}", ""),
    ("Sketch mode", "client -> server: Request\nserver -> db: Query", "?sketch=true"),
    ("Theme 200 (dark mauve)", "client -> server: Request\nserver -> db: Query", "?theme=200"),
    ("Sketch + theme 4", "a -> b -> c -> a: loop", "?sketch=true&theme=4"),
    ("ELK layout", "direction: right\na -> b -> c\na -> c\nb -> d", "?layout=elk"),
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
    return base64.urlsafe_b64encode(zlib.compress(source.encode("utf-8"), 9)).decode("ascii")


def collect_cases():
    cases = list(INLINE_CASES)
    for path in sorted((ROOT / "examples").glob("*.d2")):
        cases.append((f"examples/{path.name}", path.read_text(encoding="utf-8"), ""))
    return cases


def build(servers: dict) -> str:
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
  .tag { font-weight: 600; margin-bottom: 6px; }
  .status { margin-left: 8px; font-weight: 400; padding: 1px 6px; border-radius: 3px; background: #eee; }
  .ok .status { background: #cfeccf; } .bad .status { background: #f5c2c2; }
  img { display: block; margin: 0 auto; max-width: 100%; max-height: 520px; }
  #summary { font-weight: 600; padding: 8px 12px; background: #fff; border: 1px solid #ddd; border-radius: 6px; }
</style></head><body>
<h1>d2-renderer render check</h1>
<p id="summary">checking...</p>
{{BODY}}
<script>
  const cells = [...document.querySelectorAll('.cell')];
  let pending = cells.length, bad = 0;
  const finish = () => {
    document.getElementById('summary').textContent =
      bad === 0 ? `All ${cells.length} images loaded` : `${bad} of ${cells.length} images FAILED`;
  };
  cells.forEach(cell => {
    const img = cell.querySelector('img'), status = cell.querySelector('.status');
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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", default="http://localhost:8080")
    parser.add_argument("--remote", default=os.environ.get("RENDERER_REMOTE_URL", ""))
    args = parser.parse_args()

    servers = {"local (Docker)": args.local}
    if args.remote:
        servers["remote (Cloud Run)"] = args.remote

    out_dir = ROOT / "render-check"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(build(servers), encoding="utf-8")
    print(f"wrote {out} ({len(servers)} server column(s))")


if __name__ == "__main__":
    main()
