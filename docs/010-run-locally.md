# Run locally

Run the d2-renderer container on your own machine, keep it current, and change its settings. The service listens on port 8080 inside the container.

## Start the container

You need [Docker](https://docs.docker.com/get-docker/). Then run:

```bash
docker run -d --name d2-renderer -p 8080:8080 ghcr.io/kanad13/d2-renderer:latest
```

Docker selects the image that matches your CPU: `linux/amd64` for Intel and AMD, `linux/arm64` for Apple Silicon and other Arm hosts. Do not add a `--platform` flag.

Check that the service is up:

```bash
curl http://localhost:8080/health
```

The reply is `OK`. The image also declares a Docker health check that calls the same endpoint, so `docker ps` shows `healthy` after a few seconds.

## Daily use

| Task                           | Command                                              |
| :----------------------------- | :--------------------------------------------------- |
| Stop                           | `docker stop d2-renderer`                            |
| Start again                    | `docker start d2-renderer`                           |
| Start at every login or reboot | `docker update --restart unless-stopped d2-renderer` |
| Read logs                      | `docker logs d2-renderer`                            |
| Remove                         | `docker rm -f d2-renderer`                           |

## Update to the newest image

Pull the image, remove the old container, and start a new one:

```bash
docker pull ghcr.io/kanad13/d2-renderer:latest
docker rm -f d2-renderer
docker run -d --name d2-renderer -p 8080:8080 ghcr.io/kanad13/d2-renderer:latest
```

To stay on one build, use a commit tag from the [package page](https://github.com/kanad13/d2-renderer/pkgs/container/d2-renderer) in place of `latest`.

## Change the port or limits

The service reads three environment variables. Pass them with `-e`:

| Variable                 | Default  | Effect                                                    |
| :----------------------- | :------- | :-------------------------------------------------------- |
| `PORT`                   | `8080`   | Port the service listens on inside the container.         |
| `MAX_SOURCE_BYTES`       | `262144` | Largest accepted diagram, as sent or after decompression. |
| `RENDER_TIMEOUT_SECONDS` | `20`     | Time one render may take before the reply is `504`.       |

Example: publish the service on host port 9090 and allow larger diagrams.

```bash
docker run -d --name d2-renderer -p 9090:8080 -e MAX_SOURCE_BYTES=1048576 ghcr.io/kanad13/d2-renderer:latest
```

To choose a different host port, change only the left number of `-p`. Then enter `http://localhost:9090` wherever you configure the renderer URL.

## Build the image from source

Clone the repository, then build and run your build:

```bash
docker build -t d2-renderer:local .
docker run -d --name d2-renderer -p 8080:8080 d2-renderer:local
```

## Run without Docker

Install the [D2 compiler](https://d2lang.com/tour/install) (for example `brew install d2`), then start the service from the repository root:

```bash
python3 server.py
```

The service listens on `http://localhost:8080`. It needs only the Python standard library.

## Troubleshooting

| Symptom                                           | Cause                                                                                                                            | Fix                                                                                               |
| :------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------ |
| `port is already allocated`                       | Another program uses port 8080.                                                                                                  | Use `-p 9090:8080`, or stop the other program.                                                    |
| `container name "/d2-renderer" is already in use` | An earlier container has that name.                                                                                              | Run `docker rm -f d2-renderer`, then start again.                                                 |
| `curl` cannot connect                             | The container is stopped or still starting.                                                                                      | Run `docker ps`, then `docker logs d2-renderer`.                                                  |
| A diagram returns `400`                           | The D2 text has a syntax error.                                                                                                  | Read the reply body. It holds the compiler message with the line and column.                      |
| A diagram returns `413`                           | The text exceeds `MAX_SOURCE_BYTES`.                                                                                             | Shorten the diagram or raise the limit.                                                           |
| A diagram returns `504`                           | The render took longer than `RENDER_TIMEOUT_SECONDS`.                                                                            | Simplify the diagram or raise the limit.                                                          |
| An icon position shows a placeholder image        | Browsers do not load external files inside an SVG shown through `<img>`. The compiler leaves icon URLs as references on purpose. | Draw the diagram without icons, or render it with a service built for hosted icons such as Kroki. |

## Navigation

- [Documentation index](./README.md)
- Next: [API reference](./020-api-reference.md)
