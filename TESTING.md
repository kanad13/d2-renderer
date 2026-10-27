# Testing

How to verify `d2-renderer`: what each check proves, how to run it, and when it runs. Run the automated suite after every change, and the render check at the end of every session.

## What is verified

| Outcome | Why it matters |
| :--- | :--- |
| Endpoints answer with the documented contract. | Clients depend on status codes, headers and SVG bodies. |
| Every error reply is well formed. | Strict HTTP clients such as Node's `fetch` reject a multi-line status line. |
| Compiles stay offline and isolated. | A diagram must not trigger outbound requests or read server files. |
| Every payload and diagram in the docs works. | A copied example that fails costs a reader their trust. |
| The image runs on both architectures. | Apple Silicon is a main audience. |
| Rendered pictures look right. | A `200` status does not prove labels are readable. |

## Workflow map

| Caller and entry point | Action | Expected result | Boundary crossed | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| Health probe, `GET /health` | Query the container | `200`, body `OK` | HTTP server | `test_01_health_check` |
| Markdown `<img src>`, `GET /d2/svg/<payload>` | Fetch an encoded flowchart | `200`, `image/svg+xml`, labels present | Base64, zlib, D2 subprocess | `test_02_get_simple_diagram` |
| Sketch query, `?sketch=true` | Request the hand-drawn look | `200`, output differs from the plain render | CLI flag | `test_03_get_sketch_mode` |
| Theme query, `?theme=200` | Request a dark theme | `200`, SVG returned | CLI flag | `test_04_get_theme` |
| API client, `POST /d2/svg` | Send raw D2 text | `200`, nodes and arrows present | Request body, D2 stdin/stdout | `test_05_post_raw_diagram` |
| Complex topology | Post `examples/architecture.d2` | `200`, nested containers and cylinders | Layout engine, fonts | `test_06_render_example_architecture` |
| Sequence diagram | Post `examples/sequence.d2` | `200`, actors and steps | Sequence engine | `test_07_render_example_sequence` |
| Cache | Request one diagram twice | First `X-Cache: MISS`, then `HIT` | LRU cache | `test_08_lru_caching` |
| Malformed payload | `GET` an undecodable string | `400` | Base64, zlib errors | `test_09_invalid_base64_returns_400` |
| Syntax error | Post an unclosed bracket | `400`, compiler message in body | D2 stderr capture | `test_10_invalid_d2_syntax_returns_400` |
| Unknown route | `GET /non_existent_endpoint` | `404` | Router | `test_11_unmatched_route_returns_404` |
| Oversized body | Declare a 50 MiB `POST` | `413`, body never read | Size limit | `test_12_oversized_post_returns_413` |
| Decompression bomb | `GET` a tiny payload that inflates to 5 MiB | `413` | Bounded inflate | `test_13_decompression_bomb_returns_413` |
| Slow render | Post while a stand-in `d2` sleeps, with a 1 s limit | `504` within seconds, one-line status, text body | Subprocess timeout | `test_14_slow_render_returns_504` (starts its own server) |
| Strict HTTP client | Read each error reply from a raw socket | One-line status (`Bad Request`, `Not Found`, `Payload Too Large`), `text/plain; charset=utf-8` body with the message, for GET and POST | Socket, HTTP framing | `test_15` to `test_21`, `test_26` (unsupported methods) |
| Icon URL in a diagram | Point `icon:` at a recording stand-in host | `200`, zero requests reach the host, URL kept as `<image href>` | `--bundle=false`, network | `test_22_icon_urls_trigger_no_outbound_request` |
| Private, link-local and metadata icon URLs | Post diagrams naming `127.0.0.1`, `169.254.169.254`, `metadata.google.internal` | `200` in under 5 s | `--bundle=false`, network | `test_23_private_and_metadata_icon_urls_still_render` |
| Import in a diagram | Run a stand-in `d2` that reports its flags and directory | `--bundle=false` present, working directory empty and not the server directory | Subprocess `cwd` | `test_24_compile_runs_offline_in_an_empty_directory` (starts its own server) |
| Reader copying a payload | Decode and render every payload in README.md, docs/, examples/ | `200` with SVG each; the API reference payload decodes to `examples/hello.d2` | zlib, base64, D2 | `test_25`, `test_27` |
| Reader viewing a diagram | Re-render every `.d2` under `docs/diagrams/` and `examples/`; compare embedded sources | Committed SVGs match fresh renders; embedded code matches its `.d2` file | D2 layout, fonts | `test_28_committed_diagrams_are_current` |

## Run the automated suite

Build and start the container, then run the tests against it. `--add-host` lets the icon test reach the host from inside the container:

```bash
docker build -t d2-renderer:test .
docker run -d --name d2-test -p 8080:8080 --add-host=host.docker.internal:host-gateway d2-renderer:test
python3 -m unittest discover -s tests -v
docker rm -f d2-test
```

- **`TEST_TARGET_URL`:** the server under test. Default `http://127.0.0.1:8080`.
- **`TEST_STANDIN_HOST`:** the test machine as the server sees it. Default `host.docker.internal`. Set it when the server runs outside Docker Desktop.
- **Without Docker:** install D2 (`brew install d2`), run `python3 server.py` in the background, then run the same test command.
- **CI:** the `test` job in [ci.yml](./.github/workflows/ci.yml) runs this suite on every push and pull request.

## Sabotage checks

A check that cannot fail proves nothing. These deliberate breaks each make a named test fail, and the code is restored afterward:

| Break | Failing test |
| :--- | :--- |
| Send errors through `send_error` with the message as the reason | `test_15` to `test_21` |
| Remove `--bundle=false` | `test_22`, `test_24` |
| Remove `cwd=` from the compile call | `test_24` |
| Corrupt one payload in a doc | `test_25` |
| Edit a `.d2` file without regenerating its SVG | `test_28` |

## Visual verification

A `200` status does not prove a diagram looks right. Generate a page that shows every sample diagram from the local container and, optionally, the deployed service:

```bash
RENDERER_REMOTE_URL=<SERVICE_URL> python3 scripts/build-render-check.py
python3 -m http.server -d render-check <PORT>
```

Open `http://localhost:<PORT>/` and confirm for every image:

- **Presence:** each image appears in each column, with no broken-image icon.
- **Legibility:** labels are readable, not clipped or overlapping.
- **Variants:** sketch, theme and layout variants visibly differ from the plain render.

Omit `RENDERER_REMOTE_URL` to check only the local column. The generated page is git-ignored.

The suite also writes SVGs to `tests/output/` (git-ignored). Open them in a browser to check fonts, arrows and the hand-drawn look.

## Compare two builds

Run the probe against each target, then compare the tables. It is read-only and sends about a dozen small requests:

```bash
python3 scripts/probe-behavior.py <BASE_URL>
```

It reports status-line shape, error content type, tala support, Node `fetch` parsing, and how icon URLs are handled. Use it before and after a deploy.

## Multi-architecture image

- **Local build:** `docker buildx build --platform linux/amd64,linux/arm64 .`
- **Published image:** `docker buildx imagetools inspect ghcr.io/<OWNER>/d2-renderer:latest` lists both platforms. The publish job fails when either is missing.
- **Native check:** on an Apple Silicon Mac, `docker pull` the published image without `--platform`, run it, then render a diagram with `?layout=tala`.

## Documentation diagrams

- **Rebuild:** `python3 scripts/build-doc-diagrams.py` with the container running.
- **Verify:** `python3 scripts/build-doc-diagrams.py --check`. `test_28` runs the same check.
- **Look:** open the page that shows the diagram, for example the README, in a browser. Confirm the image has a width and its text is readable.

## Navigation

- [Back to Project README](./README.md)
- [Examples](./examples/README.md)
- [Documentation index](./docs/README.md)
