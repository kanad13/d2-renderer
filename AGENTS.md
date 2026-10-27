# AGENTS.md

Instructions for coding agents working in this repository. Humans: start at [README.md](./README.md).

## What this is

A Python 3.12 standard-library HTTP service that turns D2 diagram text into SVG by calling the `d2` CLI. It ships as a Docker image (`ghcr.io/kanad13/d2-renderer`) and runs on Google Cloud Run in an EU region. Diagram URLs are embedded in public pages, so the service is deliberately open (no token). See [docs/decisions/](./docs/decisions/README.md) for why.

## Goal of every coding session

End each session with the render check passing, judged by you, not just by exit codes:

1. Generate the page: `python3 scripts/build-render-check.py` (writes `render-check/index.html`, git-ignored).
2. Open it in the browser tool and take a screenshot.
3. Confirm every diagram shows a real picture: no broken-image icons, no clipped or overlapping labels, sketch and theme variants look different from the plain ones.
4. Local (Docker) and remote (Cloud Run) panels must both render. If remote is unreachable, say so explicitly; do not report success.

If a change breaks rendering, fix it before ending the session.

## Commands

| Task         | Command                                                             |
| :----------- | :------------------------------------------------------------------ |
| Build image  | `docker build -t d2-renderer:test .`                                |
| Run locally  | `docker run -d --name d2-test -p 8080:8080 d2-renderer:test`        |
| Run tests    | `python3 -m unittest discover -s tests -v` (needs a running server) |
| Render check | `python3 scripts/build-render-check.py`                             |
| Stop local   | `docker rm -f d2-test`                                              |

## Rules

- **Commits:** small, at natural checkpoints, using the `commit-scribe` skill. Do not add `Co-Authored-By` or any other agent attribution trailer.
- **Docs use placeholders.** Never paste this maintainer's real project IDs, emails, billing accounts or URLs into docs or scripts. Use `<PLACEHOLDER>` names, and have scripts read values from arguments or environment variables.
- **Record decisions.** A new choice with trade-offs gets a file in `docs/decisions/`. Do not edit an accepted decision; add a new one that supersedes it.
- **One fact, one place.** Link to the canonical doc instead of copying commands.
- **Dependencies:** the server has none beyond the standard library. Do not add any without an ADR.
- **Cost safety:** the Cloud Run service must keep `max-instances` at 1 and stay in a Tier 1 EU region. Never create always-on instances.
- **Secrets:** none are used. Do not add credentials to the repo; deployment uses keyless GitHub-to-Google federation.
- **Docs hygiene:** after doc changes, run the `markdown-audit` checks (numbering, README per folder, working relative links).

## Layout

| Path        | Purpose                                             |
| :---------- | :-------------------------------------------------- |
| `server.py` | The HTTP service. Limits are env-configurable.      |
| `tests/`    | Integration tests against a running server.         |
| `scripts/`  | Helper scripts (render check, GCP setup).           |
| `docs/`     | Architecture, runbook, operations, plan, decisions. |
| `examples/` | Sample `.d2` files.                                 |
