# API reference

The service has three endpoints. Examples use `http://localhost:8080`; replace it with your own address.

| Method and path         | Purpose                                                |
| :---------------------- | :----------------------------------------------------- |
| `POST /d2/svg`          | Render D2 text sent in the request body.               |
| `GET /d2/svg/<payload>` | Render D2 text encoded into the URL, for `<img>` tags. |
| `GET /health`           | Report that the service is running.                    |

All responses carry `Access-Control-Allow-Origin: *`, and `OPTIONS` requests answer the CORS pre-flight, so browser scripts can call the service from any page.

## POST /d2/svg

Send the D2 text as the request body. The reply is the SVG.

```bash
printf 'User -> Service: Call API' \
  | curl -X POST --data-binary @- http://localhost:8080/d2/svg -o diagram.svg
```

- **Request:**
  - Send a `Content-Length` header. Standard clients add it for a fixed body.
  - An empty body returns `400`.
  - A body larger than `MAX_SOURCE_BYTES` returns `413` before the service reads it.
- **Reply:**
  - Status `200` with `Content-Type: image/svg+xml; charset=utf-8`.
  - `Cache-Control: public, max-age=31536000, immutable`.
  - `X-Cache: HIT` when the cache answered, otherwise `MISS`.

## GET /d2/svg/{payload}

The path carries the diagram, so an `<img src>` tag can show it. The reply matches `POST /d2/svg`.

### Query parameters

| Parameter | Values                                | Default | Effect                       |
| :-------- | :------------------------------------ | :------ | :--------------------------- |
| `sketch`  | `true`, `1`, `yes`                    | off     | Draw with a hand-drawn look. |
| `theme`   | a D2 theme ID such as `0`, `1`, `200` | `0`     | Apply a D2 colour theme.     |
| `layout`  | `dagre`, `elk`, `tala`                | `dagre` | Choose the layout engine.    |

Query parameters work on `POST /d2/svg` too. The service ignores a `theme` or `layout` value that contains anything besides letters, digits, `_` and `-`.

### Encode a diagram

The payload is the D2 text, compressed with zlib (deflate, level 9) and written as URL-safe Base64.

Python:

```bash
python3 -c "import sys, base64, zlib; print(base64.urlsafe_b64encode(zlib.compress(sys.stdin.read().encode('utf-8'), 9)).decode('ascii'))" < diagram.d2
```

Node.js:

```javascript
const zlib = require("zlib");

function encodeD2(code) {
  const compressed = zlib.deflateSync(Buffer.from(code, "utf-8"), { level: 9 });
  return compressed.toString("base64").replace(/\+/g, "-").replace(/\//g, "_");
}
```

Both produce the same string for the same text. The service accepts the trailing `=` padding.

### Example

Source:

<img src="../examples/img/hello.svg" alt="A browser sends a diagram URL to d2-renderer and receives an SVG" width="560">

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

The encoder turns that source into this URL:

```html
<img
  src="http://localhost:8080/d2/svg/eNpNjDsOwkAMBXuf4l1gG0oXFEgoDRW_fhWbxRJ4JWcJQih3JxEUlE_zZsYcA-NNgKxSX_1i5TuBW37VR0vqxVwZkkvoDCaaSCy0b1adEVaujTZRn4MG0nrphLpoaDC67RFis5nvOO139AeX709jHM4dfQAnciyf"
  alt="Browser to d2-renderer round trip"
/>
```

Add `?sketch=true&theme=200` to the same URL for a hand-drawn dark variant.

## GET /health

Returns `200` with the body `OK`. Container platforms call it to confirm the service runs.

## Errors

Every error reply has a one-line status and a `text/plain; charset=utf-8` body with the full message. Strict HTTP clients such as Node's `fetch` read these replies directly.

| Status | Reason            | Cause                                                                                 | Body                                                   |
| :----- | :---------------- | :------------------------------------------------------------------------------------ | :----------------------------------------------------- |
| `400`  | Bad Request       | D2 syntax error, an undecodable payload, an empty body or an invalid `Content-Length` | The message. For a D2 error it is the compiler output. |
| `404`  | Not Found         | A path the service does not serve                                                     | A hint naming the valid paths.                         |
| `413`  | Payload Too Large | Text above `MAX_SOURCE_BYTES`, as sent or after decompression                         | The limit.                                             |
| `504`  | Gateway Timeout   | The render ran past `RENDER_TIMEOUT_SECONDS`                                          | The limit.                                             |

A D2 syntax error looks like this:

```text
HTTP/1.0 400 Bad Request
Content-Type: text/plain; charset=utf-8

D2 Compilation Error:
err: failed to compile -: -:1:1: connection missing destination
err: -:1:6: connection missing source
err: -:1:11: maps must be terminated with }
```

## Rendering rules

- **Offline compile:**
  - D2 runs with `--bundle=false` in an empty directory, so a diagram cannot trigger a download or read a server file.
  - `icon:` and image URLs stay in the SVG as `<image href>` references.
  - Rationale: [decision 060](./decisions/060-offline-compile-in-empty-directory.md).
- **Caching:**
  - The service keeps the 256 most recently used renders in memory.
  - The one-year `Cache-Control` header lets browsers keep a diagram without asking again.
- **Limits:**
  - See [architecture](./030-architecture.md#limits-and-why-they-exist).

## Navigation

- [Documentation index](./README.md)
- Previous: [Run locally](./010-run-locally.md) · Next: [Architecture](./030-architecture.md)
