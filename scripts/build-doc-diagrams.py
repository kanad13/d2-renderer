#!/usr/bin/env python3
"""Renders the D2 diagrams used in documentation to static committed SVG files.

Single-Line Summary:
    Synchronizes D2 diagram specifications with committed SVGs and embedded doc blocks.

Architectural Purpose:
    GitHub, GitLab, and web hosts cannot reach localhost renderers. To ensure diagram
    images render in public Markdown without broken image icons, all documentation diagrams
    are compiled offline to static SVGs committed in docs/080-img/ and docs/090-examples/img/.
    This script guarantees that committed SVGs and embedded code blocks never drift
    from their canonical .d2 sources.

Approach & Invariants:
    1. Deterministic Rendering: Generates SVGs using the service's bundled TALA layout
       engine, ensuring reproducible output matching the pinned D2 release.
    2. Automated Drift Verification: `--check` mode compares committed SVGs and embedded
       code fences against fresh renders, failing CI if documentation drifts.
    3. Single Source of Truth: Canonical specifications live in .d2 files; Markdown
       `<!-- d2-source: PATH -->` blocks are programmatically synchronized.
"""

import argparse
import os
import pathlib
import re
import sys
from typing import Iterator, Tuple
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Mapping of (source_directory, output_directory). Each .d2 file compiles to <out>/<name>.svg.
DIAGRAM_DIRS = [
    (ROOT / "docs" / "070-diagrams", ROOT / "docs" / "080-img"),
    (ROOT / "docs" / "090-examples", ROOT / "docs" / "090-examples" / "img"),
]

# TALA provides deterministic, clean architecture layouts without overlapping labels.
# Diagrams requiring left-to-right flow override this via in-diagram vars: {d2-config: ...}.
LAYOUT = "tala"

EMBED_PATTERN = re.compile(
    r"<!-- d2-source: (?P<path>\S+) -->\s*<details>.*?```d2\n(?P<code>.*?)\n```", re.DOTALL
)


def render(renderer: str, source: str) -> bytes:
    """Invokes the HTTP renderer to compile D2 source text to SVG bytes.

    Args:
        renderer: Base URL of the rendering microservice (e.g. 'http://localhost:8088').
        source: Raw D2 declarative diagram script.

    Returns:
        Rendered SVG document as raw bytes.

    Raises:
        RuntimeError: If the renderer is unreachable or compilation fails.
    """
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


def diagram_files() -> Iterator[Tuple[pathlib.Path, pathlib.Path]]:
    """Discovers all canonical D2 diagram files and their expected SVG output targets.

    Yields:
        Tuples of (d2_source_path, target_svg_path).
    """
    for source_dir, out_dir in DIAGRAM_DIRS:
        for d2_path in sorted(source_dir.glob("*.d2")):
            yield d2_path, out_dir / f"{d2_path.stem}.svg"


def embedded_sources() -> Iterator[Tuple[pathlib.Path, pathlib.Path, str]]:
    """Extracts all embedded D2 code blocks across repository Markdown documents.

    Yields:
        Tuples of (markdown_file_path, referenced_d2_file_path, embedded_code_content).
    """
    for md_path in sorted(ROOT.rglob("*.md")):
        if any(part in {"node_modules", ".git", "render-check"} for part in md_path.parts):
            continue
        for match in EMBED_PATTERN.finditer(md_path.read_text(encoding="utf-8")):
            yield md_path, ROOT / match["path"], match["code"]


def embed_markdown(d2_rel: str, alt: str, width: int, into: str) -> str:
    """Constructs a responsive image tag paired with a collapsible D2 source block.

    Args:
        d2_rel: Relative path from repository root to the .d2 source file.
        alt: Informative accessibility alt text describing the diagram.
        width: Display width in pixels for consistent browser rendering.
        into: Path of the target Markdown file receiving the embedded block.

    Returns:
        HTML and Markdown block ready for insertion.
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
    """Updates embedded D2 blocks in all Markdown files to match their source .d2 files."""
    for md_path in sorted({path for path, _, _ in embedded_sources()}):
        text = md_path.read_text(encoding="utf-8")

        def replace(match: re.Match) -> str:
            code = (ROOT / match["path"]).read_text(encoding="utf-8").rstrip("\n")
            return match.group(0).replace(match["code"], code, 1)

        updated = EMBED_PATTERN.sub(replace, text)
        if updated != text:
            md_path.write_text(updated, encoding="utf-8")
            print(f"updated embedded sources in {md_path.relative_to(ROOT)}")


def write_all(renderer: str) -> int:
    """Renders all repository diagrams to SVGs and synchronizes embedded Markdown blocks.

    Args:
        renderer: Base URL of the rendering microservice.

    Returns:
        Exit code 0 on success.
    """
    for d2_path, svg_path in diagram_files():
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_bytes(render(renderer, d2_path.read_text(encoding="utf-8")))
        print(f"wrote {svg_path.relative_to(ROOT)}")
    sync_embedded_sources()
    return 0


def check_all(renderer: str) -> int:
    """Verifies that committed SVGs and embedded blocks match fresh renders.

    Args:
        renderer: Base URL of the rendering microservice.

    Returns:
        Count of detected discrepancies (0 if fully current).
    """
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
    """CLI handler supporting compile, verification, and block generation modes."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if any SVG or embedded source is stale")
    parser.add_argument("--renderer", default=os.environ.get("DOC_RENDERER_URL", "http://localhost:8088"))
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
