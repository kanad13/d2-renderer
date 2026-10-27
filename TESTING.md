# Test Strategy & Verification Guide

This document defines the testing strategy, test harness, and behavioral verification procedures for `d2-renderer` in accordance with the `test-strategist` protocol.

---

## 1. Scope & Verification Baseline

`d2-renderer` is an HTTP microservice that decodes compressed D2 strings or raw D2 text and generates vector SVG diagrams via the D2 CLI.

Verification ensures:
1. **API Contracts:** `GET /health`, `GET /d2/svg/<encoded>`, and `POST /d2/svg` adhere strictly to HTTP standards.
2. **Layout Engine Integrity:** The D2 binary runs correctly inside the container with proper font metric support (`fontconfig`, `fonts-dejavu-core`), rendering labels without overlapping or clipping.
3. **Styling & Option Flags:** Query parameters (`?sketch=true`, `?theme=<id>`) correctly pass through to the D2 engine.
4. **Performance & Reliability:** Duplicate diagram requests hit the in-memory LRU cache (`X-Cache: HIT`).
5. **Defect Sensitivity:** Malformed payloads or invalid D2 code trigger explicit HTTP 400 errors with actionable diagnostic messages instead of crashing the process or hanging.

---

## 2. Workflows & Observable Evidence

| Caller & Entry Point | Action | Expected Result | System Boundaries | Evidence / Test Case |
| :--- | :--- | :--- | :--- | :--- |
| **Health Probe** (`GET /health`) | Query container health | `200 OK`, body `"OK"` | HTTP Server | `test_01_health_check` |
| **Markdown `<img src>`** (`GET /d2/svg/<encoded>`) | Fetch encoded flowchart | `200 OK`, `image/svg+xml`, contains SVG tags and labels | Base64 decode, zlib decompress, D2 subprocess | `test_02_get_simple_diagram` |
| **Sketch Query** (`?sketch=true`) | Request hand-drawn aesthetic | `200 OK`, rough SVG paths distinct from standard render | CLI flag propagation (`--sketch`) | `test_03_get_sketch_mode` |
| **Theme Query** (`?theme=200`) | Request dark theme | `200 OK`, theme colors applied to SVG elements | CLI flag propagation (`--theme=200`) | `test_04_get_theme` |
| **API Client** (`POST /d2/svg`) | Submit raw D2 script body | `200 OK`, SVG with nodes and arrows | Request body stream, D2 stdin/stdout | `test_05_post_raw_diagram` |
| **Complex Topology** (`POST /d2/svg`) | Submit containerized architecture | `200 OK`, complex nested containers & cylinder shapes | D2 layout engine, font metrics | `test_06_render_example_architecture` |
| **Sequence Diagram** (`POST /d2/svg`) | Submit OAuth sequence flow | `200 OK`, lifelines, actor boxes, step numbering | D2 sequence diagram engine | `test_07_render_example_sequence` |
| **Caching Check** (Duplicate GET) | Request identical diagram URL twice | Second request headers contain `X-Cache: HIT` | Memory LRU cache | `test_08_lru_caching` |
| **Malformed Payload** (`GET /d2/svg/invalid!!`) | Submit un-decodable string | `400 Bad Request`, error details in body | Base64/zlib error handling | `test_09_invalid_base64_returns_400` |
| **Syntax Error** (`POST /d2/svg` bad syntax) | Submit unclosed bracket | `400 Bad Request`, compiler stderr in body | D2 subprocess error capture | `test_10_invalid_d2_syntax_returns_400` |
| **Missing Route** (`GET /unknown`) | Request non-existent path | `404 Not Found` | Router fallthrough | `test_11_unmatched_route_returns_404` |
| **Oversized Body** (`POST` with huge `Content-Length`) | Declare a 50 MiB body | `413`, body never read | Size limit | `test_12_oversized_post_returns_413` |
| **Decompression Bomb** (`GET` tiny payload, 5 MiB inflated) | Submit highly compressed text | `413` | Bounded inflate | `test_13_decompression_bomb_returns_413` |
| **Slow Render** (`POST` while `d2` hangs) | Run a server whose `d2` sleeps, with a 1 s limit | `504` within seconds | Subprocess timeout | `test_14_slow_render_returns_504` (starts its own server; no Docker needed) |

---

## 3. How to Run Tests

### Running Against the Docker Container (Recommended)

1. **Build the container:**
   ```bash
   docker build -t d2-renderer:test .
   ```

2. **Run the container locally:**
   ```bash
   docker run -d --name d2-test-instance -p 8080:8080 d2-renderer:test
   ```

3. **Execute the automated test suite:**
   ```bash
   python3 -m unittest discover -s tests -v
   ```

4. **Tear down test container:**
   ```bash
   docker rm -f d2-test-instance
   ```

### Running Locally (Native Python without Docker)

If you have `d2` installed locally on your host (`brew install d2`):

1. **Start the local server:**
   ```bash
   python3 server.py &
   SERVER_PID=$!
   ```

2. **Run the test suite:**
   ```bash
   python3 -m unittest discover -s tests -v
   ```

3. **Stop the server:**
   ```bash
   kill $SERVER_PID
   ```

---

## 4. Visual Verification

### Render check page (end of every session)

Status codes do not prove a diagram looks right. Generate a page that shows every sample diagram from the local container and, optionally, the deployed service:

```bash
RENDERER_REMOTE_URL=<SERVICE_URL> python3 scripts/build-render-check.py
python3 -m http.server -d render-check <PORT>
```

Open `http://localhost:<PORT>/`, check that every image appears in each column with readable labels, and that sketch, theme and layout variants visibly differ from the plain ones. Omit `RENDERER_REMOTE_URL` to check only the local column.

### Saved SVG files

The test suite automatically writes rendered SVG artifacts into `tests/output/`:

* `tests/output/01_simple_diagram.svg`
* `tests/output/02_sketch_mode.svg`
* `tests/output/03_theme_200.svg`
* `tests/output/04_post_rendered.svg`
* `tests/output/05_architecture.svg`
* `tests/output/06_sequence.svg`

Open these files in a browser to visually verify that text labels are rendered cleanly with DejaVu fonts, arrows align properly, and sketch mode displays the intended hand-drawn look.

---

## Navigation

- [Back to Project README](./README.md)
- [Example Diagrams](./examples/README.md)
