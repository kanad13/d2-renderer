# Documentation

## Purpose

How to configure, deploy, operate, and extend `d2-renderer`, and why it is engineered this way. The project [README](../README.md) provides an orientation to the service and its broader ecosystem.

## Start Here

- **Running the service:** Read the [Deployment & Setup Guide](./setup/README.md) to choose Docker, native Python, or Google Cloud Run.
- **Calling the endpoints:** Consult the [API Reference](./020-api-reference.md).
- **Understanding safety and limits:** Inspect [Architecture](./030-architecture.md).
- **Exploring D2 capabilities & visual testing:** Browse the [Visualization Gallery](./visualizations/README.md) or open the unrendered [Test Document](./visualizations/test-preview.md).
- **Operating a cloud instance:** Follow the [Operations Guide](./050-operations.md).

## Contents

| Document | Summary |
| :--- | :--- |
| [**setup/**](./setup/README.md) | Guides for Docker, native Python, and Cloud Run deployments. |
| [**visualizations/**](./visualizations/README.md) | Showcase of D2 architectures, schemas, sequences, and an unrendered test document. |
| [020-api-reference.md](./020-api-reference.md) | Endpoints, query parameters, encoding, error replies, and rendering rules. |
| [030-architecture.md](./030-architecture.md) | Components, request flow, offline compile, deployment, and limits, with diagrams. |
| [050-operations.md](./050-operations.md) | Health checks, cost, tags, rollback, logs, tuning, and teardown. |
| [decisions/](./decisions/README.md) | Decision records: what was chosen, what was rejected, and why. |
| [diagrams/](./diagrams/README.md) | D2 sources for the architecture diagrams in these docs. |

## Conventions

- Commands use `<PLACEHOLDER>` values. Real project IDs, emails, and billing accounts never appear here.
- One fact lives in one document; others link to it.
- Every diagram is a committed SVG with its D2 source beside it. `python3 scripts/build-doc-diagrams.py` rebuilds them.

Draw `d2` fences in VS Code with [Lightweight Markdown Preview](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview); the extension sends them to this service.

## Navigation

- [Project README](../README.md)
- [Testing guide](../TESTING.md)
