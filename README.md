# d2-renderer

Turn [D2](https://d2lang.com) diagram text into SVG with one `docker run`.

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

## The problem

D2 describes a diagram as plain text, and a compiler turns that text into a picture. The picture is the hard part to deliver:

- **Markdown previews, blogs and wikis:**
  - They show text and images, and they cannot run the D2 compiler.
  - GitHub shows a `d2` code fence as code, not as a diagram.
- **Hosted renderers:**
  - They draw the diagram for you.
  - They also receive every diagram you send, including private architecture notes.
- **Installing D2 on every machine:**
  - It works for one person and breaks down for a team, a CI job or a public page.

## What d2-renderer does

d2-renderer wraps the `d2` compiler in a small HTTP service inside one container. You send diagram text and receive an SVG back. You run the container on your own machine or on a cloud host you control, so your diagram text stays with you.

<img src="docs/img/local-use.svg" alt="VS Code sends a d2 fence to the local d2-renderer container, which compiles it offline and returns an SVG" width="560">

<!-- d2-source: docs/diagrams/local-use.d2 -->
<details>
<summary>D2 source</summary>

```d2
direction: right

editor: VS Code {
  md: "Markdown file\nwith a d2 fence"
  ext: Lightweight Markdown Preview
  md -> ext
}

box: Your machine {
  container: d2-renderer container {
    server: HTTP service
    d2: d2 compiler\n(offline, empty directory)
    server -> d2: source text
    d2 -> server: SVG
  }
}

editor.ext -> box.container.server: "img src = localhost:8080/d2/svg/..."
box.container.server -> editor.ext: SVG diagram
```

</details>

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

## Why use it

| You get                     | How                                                                                                                                                                                                                                                       |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Private rendering**       | The compiler runs in your container. Diagram text goes nowhere else.                                                                                                                                                                                      |
| **Offline, safe compiles**  | Each compile makes no network requests and runs in an empty directory, so a diagram cannot fetch addresses or read server files. Icon URLs stay as references in the SVG. See [decision 060](./docs/decisions/060-offline-compile-in-empty-directory.md). |
| **No D2 install**           | Clients need only an HTTP call or an `<img>` tag.                                                                                                                                                                                                         |
| **Native on Intel and Arm** | One tag serves `linux/amd64` and `linux/arm64`.                                                                                                                                                                                                           |
| **Fast repeats**            | An in-memory cache answers a repeated diagram in about a millisecond (1.2 ms measured end to end on localhost).                                                                                                                                           |
| **Readable errors**         | Every error reply has a one-line status and a plain-text body with the full compiler message, so strict clients such as Node's `fetch` read it directly.                                                                                                  |
| **Layouts and styles**      | `?sketch=true`, `?theme=<id>` and `?layout=dagre\|elk\|tala` pass straight to D2.                                                                                                                                                                         |
| **Safe to publish**         | Input size, render time, cache size and instance count are all capped. See [architecture](./docs/030-architecture.md#limits-and-why-they-exist).                                                                                                          |
| **Standard-library server** | The Python service has no dependencies beyond the standard library.                                                                                                                                                                                       |

## Use it with VS Code

Lightweight Markdown Preview draws your ```d2 fences with this service. Start the container, run **Markdown: Choose D2 Renderer** and pick the local Docker container.

- [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=KunalPathak.lightweight-markdown-preview)
- [Open VSX](https://open-vsx.org/extension/KunalPathak/lightweight-markdown-preview)
- [GitHub](https://github.com/kanad13/lightweight-markdown-preview)
- [D2 guide](https://github.com/kanad13/lightweight-markdown-preview/blob/main/docs/d2.md)

## Use it from anywhere else

- **An `<img>` tag on a page you publish:**
  - Encode the diagram into the URL, then point `src` at the service.
  - The format is in the [API reference](./docs/020-api-reference.md#get-d2svgpayload).
- **A script or build step:**
  - POST the raw text to `/d2/svg`, as in the quickstart.
- **A public instance:**
  - Deploy the same image to Google Cloud Run with the [deploy runbook](./docs/040-deploy-gcp.md). A push to `main` tests, publishes and deploys.

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
| [Testing](./TESTING.md)                                | Run the tests and verify a build.                          |
| [AGENTS.md](./AGENTS.md)                               | Work on the repository as a coding agent.                  |

## License

[MIT](./LICENSE)
