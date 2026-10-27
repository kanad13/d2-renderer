# Documentation

## Purpose

How to run `d2-renderer`, call it, deploy it, operate it, and why it is built this way. The project [README](../README.md) explains what the service is for.

## Start Here

- **Using the service:** read [010-run-locally.md](./010-run-locally.md), then [020-api-reference.md](./020-api-reference.md).
- **Understanding it:** read [030-architecture.md](./030-architecture.md).
- **Running a public instance:** follow [040-deploy-gcp.md](./040-deploy-gcp.md), then keep [050-operations.md](./050-operations.md) nearby.

## Contents

| Document                                       | Summary                                                                          |
| :--------------------------------------------- | :------------------------------------------------------------------------------- |
| [010-run-locally.md](./010-run-locally.md)     | Start, update, configure and troubleshoot the container on your machine.         |
| [020-api-reference.md](./020-api-reference.md) | Endpoints, query parameters, encoding, error replies and rendering rules.        |
| [030-architecture.md](./030-architecture.md)   | Components, request flow, offline compile, deployment and limits, with diagrams. |
| [040-deploy-gcp.md](./040-deploy-gcp.md)       | Runbook: one-time Google Cloud setup, GitHub wiring, first deploy, verification. |
| [050-operations.md](./050-operations.md)       | Health checks, cost, tags, rollback, logs, tuning and teardown.                  |
| [decisions/](./decisions/README.md)            | Decision records: what was chosen, what was rejected, and why.                   |
| [diagrams/](./diagrams/README.md)              | D2 sources for the diagrams in these docs.                                       |

## Conventions

- Commands use `<PLACEHOLDER>` values. Real project IDs, emails and billing accounts never appear here.
- One fact lives in one document; others link to it.
- Every diagram is a committed SVG with its D2 source beside it. `python3 scripts/build-doc-diagrams.py` rebuilds them.

Draw `d2` fences in VS Code with [Lightweight Markdown Preview](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview); the extension sends them to this service.

## Navigation

- [Project README](../README.md)
- [Testing guide](../TESTING.md)
