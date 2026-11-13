# Example Diagram Images

## Purpose

Committed static SVG renderings of the example D2 diagrams defined in [090-examples/](../README.md). These assets are displayed directly in the [Visualization Gallery](../../040-visualizations/README.md) and example walkthroughs.

## Contents

| File | Source | Description |
| :--- | :--- | :--- |
| [hello.svg](./hello.svg) | [hello.d2](../hello.d2) | Minimal round-trip diagram between browser and d2-renderer. |
| [architecture.svg](./architecture.svg) | [architecture.d2](../architecture.d2) | Tiered microservices topology with users, API gateway, and persistence layer. |
| [aws-web-architecture.svg](./aws-web-architecture.svg) | [aws-web-architecture.d2](../aws-web-architecture.d2) | Cloud infrastructure spanning VPC subnets, ALB, ECS Fargate, and managed data stores. |
| [checkout-sequence.svg](./checkout-sequence.svg) | [checkout-sequence.d2](../checkout-sequence.d2) | E-commerce checkout workflow with payment authorization and failure paths. |
| [orders-schema.svg](./orders-schema.svg) | [orders-schema.d2](../orders-schema.d2) | Relational database schema with primary and foreign key constraints. |
| [cicd-pipeline.svg](./cicd-pipeline.svg) | [cicd-pipeline.d2](../cicd-pipeline.d2) | Multi-stage continuous integration and delivery pipeline with approval gate. |
| [gcp-data-platform.svg](./gcp-data-platform.svg) | [gcp-data-platform.d2](../gcp-data-platform.d2) | Streaming and batch cloud data platform with BigQuery warehouse modeling. |
| [sequence.svg](./sequence.svg) | [sequence.d2](../sequence.d2) | OAuth authentication sequence protocol between browser, app server, and identity provider. |

## Rebuild

Rebuild all example images by running:

```bash
python3 scripts/build-doc-diagrams.py
```

## Navigation

- [Examples Overview](../README.md)
- [Visualization Gallery](../../040-visualizations/README.md)
