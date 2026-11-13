# Run with Docker

Run the `d2-renderer` container on your local machine, keep it current, and configure its limits. The container bundles Python 3.12, the pinned `d2` CLI compiler, and required system fonts.

## Quickstart

Start the prebuilt multi-architecture container from GitHub Container Registry:

```bash
docker run -d --name d2-renderer -p 8080:8080 ghcr.io/kanad13/d2-renderer:latest
```

Docker automatically selects the matching architecture:
- `linux/amd64` for Intel and AMD machines
- `linux/arm64` for Apple Silicon and Arm hosts

Verify the service is healthy:

```bash
curl http://localhost:8080/health
```

The reply is `OK`. The container image defines a Docker health check that calls the same endpoint, so `docker ps` reports `healthy` after several seconds.

## Daily Operations

| Task | Command |
| :--- | :--- |
| **Stop** | `docker stop d2-renderer` |
| **Start** | `docker start d2-renderer` |
| **Restart on login/reboot** | `docker update --restart unless-stopped d2-renderer` |
| **View logs** | `docker logs -f d2-renderer` |
| **Remove container** | `docker rm -f d2-renderer` |

## Updating the Image

Pull the newest build, remove the old container, and start a fresh container:

```bash
docker pull ghcr.io/kanad13/d2-renderer:latest
docker rm -f d2-renderer
docker run -d --name d2-renderer -p 8080:8080 ghcr.io/kanad13/d2-renderer:latest
```

To pin a specific release, use a commit SHA tag from the [GitHub Packages page](https://github.com/kanad13/d2-renderer/pkgs/container/d2-renderer) instead of `latest`.

## Configuration Options

Configure the container using environment variables passed with `-e`:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8080` | Port the HTTP service listens on inside the container. |
| `MAX_SOURCE_BYTES` | `262144` (256 KiB) | Maximum diagram payload size accepted, as received or after decompression. |
| `RENDER_TIMEOUT_SECONDS` | `20` | Maximum time allowed for a single render before aborting with `504`. |

Example: Run on host port 9090 with a 1 MiB payload limit:

```bash
docker run -d --name d2-renderer -p 9090:8080 -e MAX_SOURCE_BYTES=1048576 ghcr.io/kanad13/d2-renderer:latest
```

## Security: Restricting Access to Localhost

By default, `-p 8080:8080` binds to all host network interfaces (`0.0.0.0`), allowing devices on the local network to reach the renderer. To restrict incoming connections strictly to your machine, bind to the loopback interface:

```bash
docker run -d --name d2-renderer -p 127.0.0.1:8080:8080 ghcr.io/kanad13/d2-renderer:latest
```

## Building From Source

To build and run from a local checkout:

```bash
docker build -t d2-renderer:local .
docker run -d --name d2-renderer -p 8080:8080 d2-renderer:local
```

## Troubleshooting

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| `port is already allocated` | Another local process uses port 8080. | Publish to a different host port (e.g. `-p 9090:8080`). |
| `container name "/d2-renderer" is already in use` | An old container remains stopped. | Remove it with `docker rm -f d2-renderer` and re-run. |
| `curl` cannot connect | Container is stopped or starting. | Run `docker ps` and inspect output with `docker logs d2-renderer`. |
| Diagram returns `400 Bad Request` | D2 script contains syntax errors. | Inspect response body for compiler line and column markers. |
| Diagram returns `413 Payload Too Large` | Diagram exceeds `MAX_SOURCE_BYTES`. | Increase `-e MAX_SOURCE_BYTES=...` or split the diagram. |

## Navigation

- [Setup Guide Index](./README.md)
- [Native Python Setup](./020-local-python.md)
- [Cloud Run Deployment](./030-cloud-run.md)
