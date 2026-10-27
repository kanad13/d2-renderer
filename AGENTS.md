# AGENTS.md

Instructions for coding agents working in this repository. Humans: start at [README.md](./README.md).

## What this is

A Python 3.12 standard-library HTTP service that turns D2 diagram text into SVG by calling the `d2` CLI. It ships as a multi-architecture Docker image (`ghcr.io/kanad13/d2-renderer`, `linux/amd64` and `linux/arm64`). People run it locally for the VS Code extension, and it runs on Google Cloud Run in an EU region. Diagram URLs are embedded in public pages, so the public service is deliberately open (no token). See [docs/decisions/](./docs/decisions/README.md) for why.

## Goal of every coding session

End each session with the render check passing, judged by you, not just by exit codes:

1. Generate the page: `python3 scripts/build-render-check.py` (writes `render-check/index.html`, git-ignored).
2. Open it in the browser tool and take a screenshot.
3. Confirm every diagram shows a real picture: no broken-image icons, no clipped or overlapping labels, sketch and theme variants look different from the plain ones.
4. Local (Docker) and remote (Cloud Run) panels must both render. If remote is unreachable, say so explicitly; do not report success.

If a change breaks rendering, fix it before ending the session.

## Commands

| Task                 | Command                                                                                                   |
| :------------------- | :-------------------------------------------------------------------------------------------------------- |
| Build image          | `docker build -t d2-renderer:test .`                                                                      |
| Run locally          | `docker run -d --name d2-test -p 8080:8080 --add-host=host.docker.internal:host-gateway d2-renderer:test` |
| Run tests            | `python3 -m unittest discover -s tests -v` (needs a running server)                                       |
| Render check         | `python3 scripts/build-render-check.py`                                                                   |
| Rebuild doc diagrams | `python3 scripts/build-doc-diagrams.py` (needs a running server)                                          |
| Compare two targets  | `python3 scripts/probe-behavior.py <BASE_URL>`                                                            |
| Stop local           | `docker rm -f d2-test`                                                                                    |

## Rules

- **Commits:** small, at natural checkpoints, using the `commit-scribe` skill. Do not add `Co-Authored-By` or any other agent attribution trailer.
- **Docs use placeholders.** Never paste this maintainer's real project IDs, emails, billing accounts or URLs into docs or scripts. Use `<PLACEHOLDER>` names, and have scripts read values from arguments or environment variables.
- **Diagrams in docs are committed SVGs.** Edit the `.d2` source in `docs/diagrams/` or `examples/`, run `scripts/build-doc-diagrams.py`, and commit the `.d2`, the SVG and any embedded source together. Embed a diagram with `scripts/build-doc-diagrams.py --embed`. `test_28` fails when they drift. See [decision 070](./docs/decisions/070-static-svg-diagrams-in-docs.md).
- **Record decisions.** A new choice with trade-offs gets a file in `docs/decisions/`. Do not edit an accepted decision; add a new one that supersedes it.
- **One fact, one place.** Link to the canonical doc instead of copying commands.
- **Dependencies:** the server has none beyond the standard library. Do not add any without an ADR.
- **Offline compile:** keep `--bundle=false` and the empty working directory ([decision 060](./docs/decisions/060-offline-compile-in-empty-directory.md)).
- **Error replies:** go through `_send_error_text` so the status line stays one line.
- **Cost safety:** the Cloud Run service must keep `max-instances` at 1 and stay in a Tier 1 EU region. Never create always-on instances.
- **Pause switch:** the repository variable `DEPLOY_ENABLED=false` skips the deploy job. Do not remove it, and do not reopen the service, unless the user asks ([operations](./docs/050-operations.md#take-the-service-offline-and-bring-it-back)).
- **Secrets:** none are used. Do not add credentials to the repo; deployment uses keyless GitHub-to-Google federation.
- **Docs hygiene:** after doc changes, run the `markdown-audit` checks (numbering, README per folder, working relative links).
- **Docs voice:** state what the service does, in the present tense. Keep factual limits as plain statements of fact.

## Layout

| Path        | Purpose                                                       |
| :---------- | :------------------------------------------------------------ |
| `server.py` | The HTTP service. Limits are env-configurable.                |
| `tests/`    | Integration tests against a running server.                   |
| `scripts/`  | Render check, behavior probe, doc-diagram builder, GCP setup. |
| `docs/`     | Guides, decision records, diagram sources and images.         |
| `examples/` | Sample `.d2` files with rendered SVGs.                        |
