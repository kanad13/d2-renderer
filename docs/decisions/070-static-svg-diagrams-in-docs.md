# 070. Show documentation diagrams as committed SVG files

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The docs showed diagrams as `<img>` tags that pointed at `http://localhost:8080`. GitHub cannot reach a localhost address, so readers saw broken images. GitHub also shows a `d2` code fence as plain code.

## Decision

- Draw each documentation diagram with this project's own container, using the bundled TALA layout engine, and commit the SVG next to the docs.
- Show the SVG with an `<img>` tag that sets a width, then give the D2 source in a collapsible block beneath it.
- Keep sources in `docs/diagrams/` and `examples/`. `scripts/build-doc-diagrams.py` renders them, and `--check` fails CI when an SVG or an embedded source drifts.

## Rejected

- **Raw inline `<svg>` in Markdown:** GitHub removes it.
- **PNG files:** need a headless browser in the build, lose crisp text at zoom, and weigh more. D2's SVG embeds its fonts, so it rendered correctly in every browser check run for this project.
- **Mermaid for every diagram:** GitHub draws it, but the project documents D2, and its own output is the best proof it works.
- **Rendering at view time from a hosted service:** puts a third party in the reading path and exposes diagram text.

## Consequences

- Diagrams render on GitHub, in editors and offline.
- A width on each `<img>` is required, because D2's SVG declares only a `viewBox` and browsers otherwise pick a small default size.
- Arm64 and amd64 builds produce byte-identical SVGs (checked for every diagram), so the CI check holds on any runner.
- Changing a `.d2` file means regenerating its SVG in the same commit.

## Navigation

- [Decision index](./README.md)
