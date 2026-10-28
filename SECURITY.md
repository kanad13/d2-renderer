# Security Policy

d2-renderer compiles diagram text that anyone can send, so it treats every diagram as untrusted. This page says how to report a problem, what the service protects, and which limits remain.

## Report a vulnerability

- **Use GitHub's private reporting:**
  - Open the [Security tab](https://github.com/kanad13/d2-renderer/security/advisories/new) of the repository and choose **Report a vulnerability**.
  - Include the diagram text or request that reproduces the problem and the image tag you ran.
- **Supported versions:**
  - The latest image on `ghcr.io/kanad13/d2-renderer` receives fixes.

## What the service protects

| Risk                                      | Protection                                                                                                  | Evidence                                                                                   |
| :---------------------------------------- | :---------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------- |
| A diagram that names icon URLs or imports | Each compile runs `d2 --bundle=false` in a fresh empty directory, so it makes no request and finds no files | [Decision 060](./docs/decisions/060-offline-compile-in-empty-directory.md), tests 22 to 24 |
| Huge or highly compressed input           | Input over `MAX_SOURCE_BYTES` (256 KiB) gets `413`, checked as sent and while inflating                     | Tests 12 and 13                                                                            |
| A compile that never ends                 | The compile stops after `RENDER_TIMEOUT_SECONDS` (20) and the reply is `504`                                | Test 14                                                                                    |
| A traffic flood on Cloud Run              | One instance at most, concurrency 8, a cache of 256 entries, and a Tier 1 EU region                         | [Decision 050](./docs/decisions/050-traffic-limits-and-cost-guardrails.md)                 |
| Container privileges                      | The image runs as a non-root user                                                                           | [Dockerfile](./Dockerfile)                                                                 |
| Credentials                               | The service uses no secrets, and deploys use keyless GitHub-to-Google federation                            | [Decision 030](./docs/decisions/030-keyless-github-deploy.md)                              |
| Telemetry                                 | None. The server imports only the Python standard library and makes no outbound requests                    | [server.py](./server.py)                                                                   |

## Known limits

- **The service has no authentication.**
  - Anyone who can reach a running instance can render diagrams, up to the limits above. [Decision 020](./docs/decisions/020-no-token-auth.md) records why. The Cloud Run service stays private by default, and [operations](./docs/050-operations.md#control-public-access-up-and-down) says how to open and close it.
- **Replies allow any origin (`Access-Control-Allow-Origin: *`).**
  - A web page you visit can ask a container on your machine to render a diagram. The service stores nothing and holds no secrets, so a page can use its compute and nothing else. Stop the container when you do not use it.
- **Docker publishes the port on every network interface by default.**
  - Other machines on your network can reach a container started with `-p 8080:8080`. [Run locally](./docs/010-run-locally.md#keep-it-on-your-machine) shows how to limit it to your machine.
- **Icons do not load.**
  - A diagram's icon URLs stay as references in the SVG, and browsers do not load them through an `<img>` tag. Use a renderer built for hosted icons, such as Kroki, when you need them.
- **D2 is pinned.**
  - The image uses D2 v0.9.0. A vulnerability in D2 itself reaches this service until the pin moves, so report it to D2 and open an issue here.
