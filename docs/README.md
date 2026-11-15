# Documentation

## Purpose

How to configure, deploy, operate, and extend `d2-renderer`, and why it is engineered this way. The project [README](../README.md) provides an orientation to the service and its broader ecosystem.

## Start Here

- **Running the service:** Read the [Deployment & Setup Guide](./010-setup/README.md) to choose Docker, native Python, or Google Cloud Run.
- **Calling the endpoints:** Consult the [API Reference](./020-api-reference.md).
- **Understanding safety and limits:** Inspect [Architecture](./030-architecture.md).
- **Exploring D2 capabilities & visual testing:** Browse the [Visualization Gallery](./040-visualizations/README.md) or open the unrendered [Test Document](./040-visualizations/010-test-preview.md).
- **Operating a cloud instance:** Follow the [Operations Guide](./050-operations.md).
- **Reviewing design choices:** Inspect [Decision Records](./060-decisions.md).
- **Exploring diagram examples:** Browse [Examples](./090-examples/README.md).

## Contents

| Document | Summary |
| :--- | :--- |
| [010-setup/](./010-setup/README.md) | Guides for Docker, native Python, and Cloud Run deployments. |
| [020-api-reference.md](./020-api-reference.md) | Endpoints, query parameters, encoding, error replies, and rendering rules. |
| [030-architecture.md](./030-architecture.md) | Components, request flow, offline compile, deployment, and limits, with diagrams. |
| [040-visualizations/](./040-visualizations/README.md) | Showcase of D2 architectures, schemas, sequences, and an unrendered test document. |
| [050-operations.md](./050-operations.md) | Health checks, cost, tags, rollback, logs, tuning, and teardown. |
| [060-decisions.md](./060-decisions.md) | Decision records: what was chosen, what was rejected, and why. |
| [070-diagrams/](./070-diagrams/README.md) | Canonical D2 sources for the architecture diagrams in these docs. |
| [080-img/](./080-img/) | Committed static SVG images rendered from `070-diagrams/`. |
| [090-examples/](./090-examples/README.md) | Eight ready-made D2 diagrams with rendered SVGs and curl commands. |

## Conventions

- Commands use `<PLACEHOLDER>` values. Real project IDs, emails, and billing accounts never appear here.
- One fact lives in one document; others link to it.
- Every diagram is a committed SVG with its D2 source beside it. `python3 scripts/build-doc-diagrams.py` rebuilds them.

Draw `d2` fences in VS Code with [Lightweight Markdown Preview](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview); the extension sends them to this service.

## Navigation

- [Project README](../README.md)
- [Testing guide](../TESTING.md)
