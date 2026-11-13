# 060. Compile offline, in an empty directory

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

D2 bundles `icon:` and image assets by downloading them while it compiles, and it resolves imports (`...@name`) against the working directory. On a public, open service ([020](./020-no-token-auth.md)) that meant a diagram could make the container request any address it named. A measured probe against the deployed service reached the Cloud Run metadata server and received its `403` reply. Imports could read `.d2` files next to the server.

The service's main local use is the VS Code extension, which draws every diagram through an `<img>` tag.

## Decision

- Run `d2` with `--bundle=false`. The compiler makes no network requests; icon and image URLs stay in the SVG as `<image href>` references.
- Run each compile in a fresh empty temporary directory. Imports see nothing.
- Describe this as a property of the image: renders are self-contained, deterministic and private. Diagrams that need hosted icons use a renderer built for that, such as Kroki.

## Rejected

- **`ICON_HOSTS` allowlist with address checks:** keeps icons drawn, but D2 performs the download itself, so Python cannot police DNS results or redirects from outside. It needs a pre-fetch layer or an egress proxy, and a setting to maintain.
- **Rewriting the SVG to delete image tags:** extra code that changes compiler output, with no safety gain over never fetching.
- **Egress firewall on Cloud Run:** protects one deployment only, and costs money and configuration.

## Consequences

- No outbound request can be triggered by a diagram, on any host that runs the image.
- A diagram with an icon compiles in milliseconds instead of failing when an icon host is slow or returns an error.
- Browsers do not load external resources inside an SVG shown through `<img>`, so icon positions show the browser's placeholder there. Diagrams without icons are unaffected.
- Tests: `TestOfflineCompile` in [test_server.py](../../tests/test_server.py).

## Navigation

- [Decision index](./README.md)
