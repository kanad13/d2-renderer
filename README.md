# d2-renderer: render D2 diagrams to SVG over HTTP

d2-renderer is a small HTTP service that turns [D2](https://d2lang.com) diagram text into SVG. It runs in one Docker container on your machine or on Google Cloud Run, takes Kroki-style GET URLs and POST requests, and compiles every diagram offline, so your diagram text stays in your environment.

<img src="examples/img/hello.svg" alt="A browser sends a diagram URL to d2-renderer and receives an SVG" width="560">

<!-- d2-source: examples/hello.d2 -->
<details>
<summary>D2 source</summary>

```d2
vars: {
  d2-config: {
    layout-engine: dagre
  }
}
direction: right
Browser -> d2-renderer: GET diagram URL
d2-renderer -> Browser: SVG
```

</details>

GitHub and most Markdown viewers show a `d2` fence as code, and hosted renderers receive every diagram you send. d2-renderer gives a page, a build step or an editor an `<img>` tag or an HTTP call that returns the picture, from a service you run.

## Features

| Feature                 | What it does                                                                                                        | What you gain                                                                                                                          |
| :---------------------- | :------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------- |
| Private rendering       | Compiles in your container and sends diagram text nowhere else                                                      | Architecture notes stay in your environment.                                                                                           |
| Offline compiles        | Runs `d2 --bundle=false` in an empty directory, so a compile makes no network requests and finds no files to import | A diagram cannot fetch addresses or read server files. See [decision 060](./docs/decisions/060-offline-compile-in-empty-directory.md). |
| HTTP only for clients   | Answers `GET /d2/svg/<payload>` and `POST /d2/svg`                                                                  | An `<img>` tag or one `curl` call draws a diagram. Clients need no D2 install.                                                         |
| Intel and Arm           | Serves `linux/amd64` and `linux/arm64` from one image tag                                                           | The same `docker run` works on Intel, AMD and Apple Silicon.                                                                           |
| Layouts and styles      | Passes `?sketch=true`, `?theme=<id>` and `?layout=dagre\|elk\|tala` to D2                                           | Hand-drawn style, themes and the TALA layout engine are available.                                                                     |
| In-memory cache         | Answers a repeated diagram from memory in about a millisecond (1.2 ms measured end to end on localhost)             | Pages that repeat a diagram load quickly.                                                                                              |
| Readable errors         | Sends a one-line status and a plain-text body with the full compiler message                                        | Strict clients such as Node's `fetch` read the message directly.                                                                       |
| Capped resources        | Limits input size, render time, cache size and instance count                                                       | A public instance has a bounded cost. See [architecture](./docs/030-architecture.md#limits-and-why-they-exist).                        |
| Standard-library server | Uses only the Python standard library                                                                               | One file to read, and no packages to update.                                                                                           |

## Quickstart

Start the service:

```bash
docker run -d --name d2-renderer -p 8080:8080 ghcr.io/kanad13/d2-renderer:latest
```

Render a diagram:

```bash
printf 'client -> server: request\nserver -> client: response' \
  | curl -X POST --data-binary @- http://localhost:8080/d2/svg -o hello.svg
```

Open `hello.svg` in a browser. The same image tag runs on Intel/AMD machines and on Apple Silicon Macs, with no `--platform` flag. More ways to run it are in [Run locally](./docs/010-run-locally.md).

## What D2 can draw

Each picture comes from a `.d2` file in [examples](./examples/README.md), drawn by this service. They cover light and dark themes, a hand-drawn style, and architectures with nested boxes, queues and databases.

### AWS web application

CloudFront and WAF in front, an ECS service in private subnets, and Redis, PostgreSQL and a queue behind it. Source: [aws-web-architecture.d2](./examples/aws-web-architecture.d2).

<img src="examples/img/aws-web-architecture.svg" alt="AWS architecture with Route 53, CloudFront, WAF, an ALB, ECS Fargate tasks, ElastiCache, RDS and SQS inside nested VPC subnets" width="760">

### Google Cloud data platform

Ingest, processing, warehouse and serving stages in a dark theme, with an orchestrator that spans them. Source: [gcp-data-platform.d2](./examples/gcp-data-platform.d2).

<img src="examples/img/gcp-data-platform.svg" alt="Google Cloud data platform: Pub/Sub and Cloud Storage feed Dataflow and Dataproc into BigQuery, then Looker, Cloud Run and Vertex AI" width="620">

### Checkout sequence, hand-drawn

A sequence diagram with `sketch: true`, a warm theme and a group for the failure path. Source: [checkout-sequence.d2](./examples/checkout-sequence.d2).

<img src="examples/img/checkout-sequence.svg" alt="Sequence diagram of a checkout between shopper, web app, order service, payment provider and inventory service" width="520">

### Database schema

`sql_table` shapes, primary and foreign keys, and relationships drawn as arrows. Source: [orders-schema.d2](./examples/orders-schema.d2).

<img src="examples/img/orders-schema.svg" alt="Entity relationship diagram of customers, orders, order items and products" width="760">

### CI/CD pipeline

People, repositories, a pipeline, an approval gate and a rollback path in one picture. Source: [cicd-pipeline.d2](./examples/cicd-pipeline.d2).

<img src="examples/img/cicd-pipeline.svg" alt="CI/CD pipeline from a developer push through lint, tests, build and scan to staging, approval and production" width="700">

The [examples page](./examples/README.md) lists all eight diagrams with their source and the commands that render them.

## Use it with VS Code

[Lightweight Markdown Preview](https://github.com/kanad13/lightweight-markdown-preview) draws your `d2` fences with this service as you type. Start the container, run **Markdown: Choose D2 Renderer** and pick the local Docker container.

![A VS Code window with a Markdown file on the left that holds a D2 fence, and the Markdown preview on the right that shows the drawn diagram: a web shop sends an order to an order service, which saves to a database and enqueues to a queue](https://raw.githubusercontent.com/kanad13/lightweight-markdown-preview/main/assets/readme-d2-source-and-preview.png)

<img src="docs/img/local-use.svg" alt="VS Code sends a d2 fence to the local d2-renderer container, which compiles it offline and returns an SVG" width="560">

The three projects fit together:

| Piece                                                                                    | What it does                                                                                                                                                                                                                                                     |
| :--------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Lightweight Markdown Preview](https://github.com/kanad13/lightweight-markdown-preview)  | Draws `d2` fences, Mermaid and math in VS Code. Also on [Open VSX](https://open-vsx.org/extension/KunalPathak/lightweight-markdown-preview) and the [Marketplace](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview). |
| d2-renderer                                                                              | This service: the container that draws the diagrams.                                                                                                                                                                                                             |
| [d2-architect](https://github.com/kanad13/coherent-output/tree/main/skills/d2-architect) | An agent skill that adds a checked D2 diagram under every heading of a document, without changing your text.                                                                                                                                                     |

The extension's [D2 guide](https://github.com/kanad13/lightweight-markdown-preview/blob/main/docs/d2.md) has setup steps, options and troubleshooting.

## Use it from anywhere else

- **An `<img>` tag on a page you publish:**
  - Encode the diagram into the URL, then point `src` at the service.
  - The format is in the [API reference](./docs/020-api-reference.md#get-d2svgpayload).
- **A script or build step:**
  - POST the raw text to `/d2/svg`, as in the quickstart.
- **A public instance:**
  - Deploy the same image to Google Cloud Run with the [deploy runbook](./docs/040-deploy-gcp.md), and manage its lifecycle with the [operations guide](./docs/050-operations.md#control-public-access-up-and-down).

## Security and privacy

A public instance accepts diagram text from anyone, so the service treats every diagram as untrusted input on every deployment.

| Risk                                      | What the service does                                                                                              |
| :---------------------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| A diagram that names icon URLs or imports | Compiles offline in an empty directory. Icon URLs stay references in the SVG, and no request leaves the container. |
| Huge or highly compressed input           | Rejects input over `MAX_SOURCE_BYTES` (256 KiB), as sent and after decompression, with `413`.                      |
| A diagram that never finishes             | Stops the compile after `RENDER_TIMEOUT_SECONDS` (20) with `504`.                                                  |
| A traffic flood on a public instance      | Runs one Cloud Run instance at most, with concurrency 8 and a cache of 256 entries.                                |
| Container privileges                      | Runs as a non-root user.                                                                                           |
| Credentials                               | Uses no secrets. Deploys use keyless GitHub-to-Google federation.                                                  |
| Where diagram text goes                   | Nowhere but the container that compiles it. The image sends no telemetry.                                          |

The [security policy](./SECURITY.md) explains how to report a vulnerability and lists the known limits.

## Documentation

| Read                                                   | When you want to                                           |
| :----------------------------------------------------- | :--------------------------------------------------------- |
| [Run locally](./docs/010-run-locally.md)               | Run, update, configure or troubleshoot the container.      |
| [API reference](./docs/020-api-reference.md)           | Call the service: endpoints, parameters, errors, encoding. |
| [Architecture](./docs/030-architecture.md)             | See how a request flows and why each limit exists.         |
| [Deploy to Google Cloud Run](./docs/040-deploy-gcp.md) | Run a public instance.                                     |
| [Operations](./docs/050-operations.md)                 | Manage cost, roll back, read logs, tune limits.            |
| [Decision records](./docs/decisions/README.md)         | Learn why the project is built this way.                   |
| [Examples](./examples/README.md)                       | See rendered diagrams next to their source.                |
| [Security policy](./SECURITY.md)                       | Report a vulnerability and read the known limits.          |
| [Testing](./TESTING.md)                                | Run the tests and verify a build.                          |
| [AGENTS.md](./AGENTS.md)                               | Work on the repository as a coding agent.                  |

## License

[MIT](./LICENSE)
