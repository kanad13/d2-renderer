# Example diagrams

## Purpose

Three ready-made D2 diagrams with the pictures that d2-renderer draws from them. Each picture is an SVG committed in [img/](./img/), so GitHub shows it without a running service. Open the **D2 source** block under a picture to copy the code behind it.

## Contents

| Source | Picture | Shows |
| :--- | :--- | :--- |
| [hello.d2](./hello.d2) | [hello.svg](./img/hello.svg) | The smallest useful diagram: two nodes and two labelled arrows. |
| [architecture.d2](./architecture.d2) | [architecture.svg](./img/architecture.svg) | A multi-tier service topology with containers, shapes, colours and a database layer. |
| [sequence.d2](./sequence.d2) | [sequence.svg](./img/sequence.svg) | An OAuth 2.0 authorization-code flow as a sequence diagram. |

## Hello

<img src="img/hello.svg" alt="Browser sends a diagram URL to d2-renderer and receives an SVG" width="560">

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

## Architecture

<img src="img/architecture.svg" alt="Microservice architecture: users, API gateway, internal services and a data layer" width="760">

<!-- d2-source: examples/architecture.d2 -->
<details>
<summary>D2 source</summary>

```d2
direction: right

title: Microservice Architecture

users: Web & Mobile Users {
  shape: person
}

gateway: API Gateway {
  shape: hexagon
  style.fill: "#E8F0FE"
}

services: Internal Services {
  style.stroke-dash: 3

  auth: Authentication Service {
    shape: package
  }

  billing: Billing Service {
    shape: package
  }

  renderer: D2 Rendering Service {
    shape: package
    style.fill: "#E6F4EA"
  }
}

storage: Data Layer {
  db: PostgreSQL {
    shape: cylinder
  }
  cache: Redis {
    shape: cylinder
  }
}

users -> gateway: HTTPS Requests
gateway -> services.auth: Validate Token
gateway -> services.renderer: Render Diagram (SVG)
gateway -> services.billing: Process Invoices

services.auth -> storage.db: Query Credentials
services.renderer -> storage.cache: Check Render Cache
services.billing -> storage.db: Write Transaction
```

</details>

## Sequence

<img src="img/sequence.svg" alt="OAuth 2.0 authorization code flow between browser, web app, OAuth provider and user database" width="640">

<!-- d2-source: examples/sequence.d2 -->
<details>
<summary>D2 source</summary>

```d2
shape: sequence_diagram

browser: Web Browser
app: Web App Server
auth: OAuth Provider
db: User Database

browser -> app: 1. Click "Sign in with OAuth"
app -> auth: 2. Redirect to Authorization URL
auth -> browser: 3. Prompt user consent
browser -> auth: 4. User grants permission
auth -> app: 5. Return Authorization Code
app -> auth: 6. Exchange code for Access Token
auth -> app: 7. Deliver Access Token + User Info
app -> db: 8. Upsert user record
db -> app: 9. Record confirmed
app -> browser: 10. Issue session cookie and redirect to dashboard
```

</details>

## Render an example yourself

Start the container as shown in [Run locally](../docs/010-run-locally.md), then post a file:

```bash
curl -X POST --data-binary @examples/architecture.d2 http://localhost:8080/d2/svg -o architecture.svg
```

Add query parameters for another look:

```bash
curl -X POST --data-binary @examples/architecture.d2 "http://localhost:8080/d2/svg?sketch=true&theme=200&layout=tala" -o architecture-sketch.svg
```

The [API reference](../docs/020-api-reference.md) lists every parameter and shows how to embed a diagram with an `<img>` tag.

In VS Code, paste a `.d2` file into a `d2` fence and [Lightweight Markdown Preview](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview) draws it through this service.

## Navigation

- [Project README](../README.md)
- [Documentation index](../docs/README.md)
- [Testing guide](../TESTING.md)
