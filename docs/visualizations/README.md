# D2 Visualization Gallery

## Purpose

A visual reference showcasing the expressive range of the [D2 declarative diagramming language](https://d2lang.com). Unlike generic flowchart tools, D2 provides native primitives for software and system architecture: nested scoping, database schemas, multiple layout engines, sequence diagrams, and dark/sketch aesthetics.

Every diagram below is rendered directly by `d2-renderer`.

---

## Gallery

### 1. Cloud Infrastructure: AWS Multi-Tier Stack
Demonstrates nested VPC subnets, application load balancing, ECS Fargate services, and managed datastores (RDS, ElastiCache, SQS).
- **Source:** [aws-web-architecture.d2](../../examples/aws-web-architecture.d2)
- **Engine:** TALA layout engine

<img src="../../examples/img/aws-web-architecture.svg" alt="AWS architecture with Route 53, CloudFront, WAF, an ALB, ECS Fargate tasks, ElastiCache, RDS and SQS inside nested VPC subnets" width="760">

---

### 2. Modern Data Platform: Google Cloud
Demonstrates dark theme rendering (`theme=200`), spanning orchestrators, streaming ingest (Pub/Sub), BigQuery warehouse modeling, and machine learning serving.
- **Source:** [gcp-data-platform.d2](../../examples/gcp-data-platform.d2)
- **Theme:** Dark Mauve (Theme ID `200`)

<img src="../../examples/img/gcp-data-platform.svg" alt="Google Cloud data platform: Pub/Sub and Cloud Storage feed Dataflow and Dataproc into BigQuery, then Looker, Cloud Run and Vertex AI" width="620">

---

### 3. Business Workflows: Checkout Sequence (Hand-Drawn)
Demonstrates sequence diagrams with the hand-drawn aesthetic (`sketch: true`), custom actor shapes, and grouped failure paths.
- **Source:** [checkout-sequence.d2](../../examples/checkout-sequence.d2)
- **Options:** `?sketch=true&theme=100`

<img src="../../examples/img/checkout-sequence.svg" alt="Sequence diagram of a checkout between shopper, web app, order service, payment provider and inventory service" width="520">

---

### 4. Data Modeling: Relational Database Schema
Demonstrates native `sql_table` shapes, primary keys, foreign keys, and relationship arrows.
- **Source:** [orders-schema.d2](../../examples/orders-schema.d2)

<img src="../../examples/img/orders-schema.svg" alt="Entity relationship diagram of customers, orders, order items and products" width="760">

---

### 5. DevOps: CI/CD Delivery Pipeline
Demonstrates multi-stage delivery pipelines with manual approval gates, automated tests, container scanning, and automated rollbacks.
- **Source:** [cicd-pipeline.d2](../../examples/cicd-pipeline.d2)

<img src="../../examples/img/cicd-pipeline.svg" alt="CI/CD pipeline from a developer push through lint, tests, build and scan to staging, approval and production" width="700">

---

### 6. Microservices Topology
Demonstrates tiered architectures with person actors, API gateways, decoupled microservices, and persistence layers.
- **Source:** [architecture.d2](../../examples/architecture.d2)

<img src="../../examples/img/architecture.svg" alt="Microservice architecture: users, API gateway, internal services and a data layer" width="760">

---

## Verifying Your Renderer

To test these diagrams live in VS Code or via HTTP:
- Open [test-preview.md](./test-preview.md) to inspect unrendered `d2` fences in your editor.
- See the [Setup Guide](../setup/README.md) to configure your renderer.
