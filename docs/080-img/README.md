# Documentation Images

## Purpose

Committed static SVG renderings of the architecture diagrams located in [070-diagrams/](../070-diagrams/README.md). These static assets ensure diagrams display reliably in public web hosts, GitHub, and GitLab without requiring a running rendering microservice.

## Contents

| File | Source | Description |
| :--- | :--- | :--- |
| [local-use.svg](./local-use.svg) | [local-use.d2](../070-diagrams/local-use.d2) | Local editor workflow with Lightweight Markdown Preview and local container. |
| [request-flow.svg](./request-flow.svg) | [request-flow.d2](../070-diagrams/request-flow.d2) | Incoming request lifecycle: size validation, LRU cache lookup, and offline compile. |
| [offline-compile.svg](./offline-compile.svg) | [offline-compile.d2](../070-diagrams/offline-compile.d2) | Sandboxed compile in an ephemeral directory with `--bundle=false`. |
| [deployment.svg](./deployment.svg) | [deployment.d2](../070-diagrams/deployment.d2) | CI/CD pipeline from git push through GHCR publish to Cloud Run deploy. |

## Rebuild

These images are compiled programmatically by running:

```bash
python3 scripts/build-doc-diagrams.py
```

## Navigation

- [Documentation Index](../README.md)
- [Diagram Sources](../070-diagrams/README.md)
