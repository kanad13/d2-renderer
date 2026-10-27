# Documentation

## Purpose

How `d2-renderer` is built, deployed to Google Cloud Run, operated, and why it was built that way. The project [README](../README.md) covers what the service does and how to call it.

## Start Here

New to the project: read [010-architecture.md](./010-architecture.md). Deploying your own copy: follow [020-deploy-gcp.md](./020-deploy-gcp.md).

## Contents

| Document                                     | Summary                                                                          |
| :------------------------------------------- | :------------------------------------------------------------------------------- |
| [010-architecture.md](./010-architecture.md) | Components, request flow, and the limits that protect a public service.          |
| [020-deploy-gcp.md](./020-deploy-gcp.md)     | Runbook: one-time Google Cloud setup, GitHub wiring, first deploy, verification. |
| [030-operations.md](./030-operations.md)     | Cost, budget alerts, rollback, logs, tuning limits, teardown.                    |
| [040-plan.md](./040-plan.md)                 | Delivery phases and their status.                                                |
| [decisions/](./decisions/README.md)          | Decision records: what was chosen, what was rejected, and why.                   |

## Conventions

- Commands in these docs use `<PLACEHOLDER>` values. Never paste real project IDs, emails or billing accounts here.
- One fact lives in one document; others link to it.

## Navigation

- [Project README](../README.md)
- [Testing guide](../TESTING.md)
