#!/usr/bin/env python3
"""Renders the D2 diagrams used in the documentation to committed SVG files.

GitHub cannot reach a localhost renderer, so every diagram in the docs is a static SVG in
the repository, drawn by this project's own container (it uses the TALA layout engine that
the service bundles). The D2 source sits next to each image inside a collapsible block, so
a reader can copy the code behind the picture.

Two modes keep pictures, sources and prose from drifting apart:

    python3 scripts/build-doc-diagrams.py            # rewrite the SVG files and embedded sources
    python3 scripts/build-doc-diagrams.py --check    # fail if anything is stale

Check mode fails when a committed SVG differs from a fresh render, or when a
`<!-- d2-source: PATH -->` block in a Markdown file differs from the `.d2` file it names.
Output is deterministic for a pinned D2 version, so a clean check means a clean diff.

Usage:
    python3 scripts/build-doc-diagrams.py [--check] [--renderer URL]
    python3 scripts/build-doc-diagrams.py --embed docs/diagrams/request-flow.d2 --into docs/030-architecture.md --alt "..." --width 560

The renderer defaults to $DOC_RENDERER_URL, then http://localhost:8080.
"""

import argparse
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (source directory, output directory). Each .d2 file becomes <out>/<name>.svg.
DIAGRAM_DIRS = [
    (ROOT / "docs" / "diagrams", ROOT / "docs" / "img"),
    (ROOT / "examples", ROOT / "examples" / "img"),
]

# TALA keeps labels readable at README width; dagre and ELK lay wide diagrams out sideways.
# A diagram that needs left-to-right order sets `vars: {d2-config: {layout-engine: dagre}}`.
LAYOUT = "tala"

EMBED_PATTERN = re.compile(
    r"<!-- d2-source: (?P<path>\S+) -->\s*<details>.*?```d2\n(?P<code>.*?)\n```", re.DOTALL
)


def render(renderer: str, source: str) -> bytes:
    """Returns the SVG the renderer draws for D2 source text.

    Raises:
        RuntimeError: If the renderer is unreachable or rejects the diagram, with the
            reply body so the D2 error is visible.
    """
    # A source that names its own engine (d2-config layout-engine) keeps it; the query
    # parameter would override that choice.
    query = "" if "layout-engine" in source else f"?layout={LAYOUT}"
    request = urllib.request.Request(
        f"{renderer}/d2/svg{query}",
        data=source.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as reply:
            return reply.read()
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"renderer rejected the diagram: {err.read().decode('utf-8', 'replace')}") from err
    except OSError as err:
        raise RuntimeError(f"renderer unreachable at {renderer}: {err}") from err


def diagram_files():
    """Yields (d2 path, svg path) for every diagram source in the repository."""
    for source_dir, out_dir in DIAGRAM_DIRS:
        for d2_path in sorted(source_dir.glob("*.d2")):
            yield d2_path, out_dir / f"{d2_path.stem}.svg"


def embedded_sources():
    """Yields (markdown path, d2 path named by the marker, embedded code) for each block."""
    for md_path in sorted(ROOT.rglob("*.md")):
        if any(part in {"node_modules", ".git", "render-check"} for part in md_path.parts):
            continue
        for match in EMBED_PATTERN.finditer(md_path.read_text(encoding="utf-8")):
            yield md_path, ROOT / match["path"], match["code"]


def embed_markdown(d2_rel: str, alt: str, width: int, into: str) -> str:
    """Builds the image plus collapsible-source block that documents paste in.

    A fixed width is set because D2's SVG declares only a viewBox, and browsers size such
    an image inconsistently without one.
    """
    d2_path = ROOT / d2_rel
    svg_rel = os.path.relpath(dict(diagram_files())[d2_path], start=(ROOT / into).parent)
    code = d2_path.read_text(encoding="utf-8").rstrip("\n")
    return (
        f'<img src="{svg_rel}" alt="{alt}" width="{width}">\n\n'
        f"<!-- d2-source: {d2_rel} -->\n<details>\n<summary>D2 source</summary>\n\n"
        f"```d2\n{code}\n```\n\n</details>"
    )


def sync_embedded_sources() -> None:
    """Rewrites every embedded D2 block so it matches the .d2 file its marker names."""
    for md_path in sorted({path for path, _, _ in embedded_sources()}):
        text = md_path.read_text(encoding="utf-8")

        def replace(match):
            code = (ROOT / match["path"]).read_text(encoding="utf-8").rstrip("\n")
            return match.group(0).replace(match["code"], code, 1)

        updated = EMBED_PATTERN.sub(replace, text)
        if updated != text:
            md_path.write_text(updated, encoding="utf-8")
            print(f"updated embedded sources in {md_path.relative_to(ROOT)}")


def write_all(renderer: str) -> int:
    """Renders every diagram to its SVG, then syncs embedded sources. Returns 0."""
    for d2_path, svg_path in diagram_files():
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_bytes(render(renderer, d2_path.read_text(encoding="utf-8")))
        print(f"wrote {svg_path.relative_to(ROOT)}")
    sync_embedded_sources()
    return 0


def check_all(renderer: str) -> int:
    """Returns the number of stale images and mismatched embedded sources."""
    problems = []
    for d2_path, svg_path in diagram_files():
        fresh = render(renderer, d2_path.read_text(encoding="utf-8"))
        if not svg_path.exists():
            problems.append(f"missing {svg_path.relative_to(ROOT)}")
        elif svg_path.read_bytes() != fresh:
            problems.append(f"stale {svg_path.relative_to(ROOT)} (re-run without --check)")
    for md_path, d2_path, code in embedded_sources():
        if not d2_path.exists():
            problems.append(f"{md_path.relative_to(ROOT)} names missing source {d2_path.relative_to(ROOT)}")
        elif d2_path.read_text(encoding="utf-8").rstrip("\n") != code:
            problems.append(f"{md_path.relative_to(ROOT)} embeds out-of-date code for {d2_path.relative_to(ROOT)}")
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print("doc diagrams are current")
    return len(problems)


def main() -> int:
    """Parses arguments and runs the chosen mode. Returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if any SVG or embedded source is stale")
    parser.add_argument("--renderer", default=os.environ.get("DOC_RENDERER_URL", "http://localhost:8080"))
    parser.add_argument("--embed", metavar="D2_PATH", help="print the Markdown block for one diagram")
    parser.add_argument("--into", default="README.md", help="Markdown file the block will live in")
    parser.add_argument("--alt", default="")
    parser.add_argument("--width", type=int, default=640)
    args = parser.parse_args()
    try:
        if args.embed:
            print(embed_markdown(args.embed, args.alt, args.width, args.into))
            return 0
        return 1 if (check_all if args.check else write_all)(args.renderer.rstrip("/")) else 0
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
