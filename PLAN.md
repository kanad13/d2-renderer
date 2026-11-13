# Plan

Goal: Standardize diagrams, elevate documentation hierarchy and numbering, establish clear conceptual framing, and eliminate repository drift.

Acceptance:
- All D2 diagrams in `docs/070-diagrams/` and `docs/090-examples/` compiled and verified with `/d2-architect` standards.
- ASCII box diagram in `README.md` replaced with a compliant `/mermaid-architect` diagram.
- `docs/` restructured with consistent three-digit numbering (`010-` through `090-`), and `examples/` moved into `docs/090-examples/`.
- All automated integration tests (`python3 -m unittest discover -s tests -v`) and doc drift checks pass without error.
- All relative markdown links and image sources across the repository resolve correctly.

Done:
- Migrated `docs/setup` -> `docs/010-setup`, `docs/visualizations` -> `docs/040-visualizations` (with `010-test-preview.md`), `docs/decisions` -> `docs/060-decisions`, `docs/diagrams` -> `docs/070-diagrams`, `docs/img` -> `docs/080-img`, and `examples` -> `docs/090-examples`.
- Standardized all 12 `.d2` diagrams to use `/d2-architect` layout (TALA layout engine, `pad: 24`, `theme-id: 0`, `dark-theme-id: 200`, semantic shapes, snake_case keys).
- Recompiled all 12 SVG diagrams via `scripts/build-doc-diagrams.py` and synchronized embedded markdown code fences.
- Re-encoded `hello.d2` to Kroki base64url payload and updated `README.md` and `docs/020-api-reference.md`.
- Refactored `README.md` introduction to clearly define `d2-renderer` as a standalone rendering server and turnkey container solving the end-to-end authoring workflow.
- Replaced ASCII architecture diagram in `README.md` with an insertion-compliant Mermaid flowchart (`Theme A`).
- Updated path references in `scripts/build-doc-diagrams.py`, `scripts/build-render-check.py`, `tests/test_server.py`, `.dockerignore`, `AGENTS.md`, `TESTING.md`, `SECURITY.md`, and documentation indices.

Next action:
Run full link integrity verification, test suite execution, and invoke a specialized subagent to perform an independent verification audit.

Blockers:
None
