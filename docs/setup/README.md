# Deployment and Setup Guide

## Purpose

Choose and configure the operational footprint for `d2-renderer`. The service exposes an identical HTTP API (`POST /d2/svg`, `GET /d2/svg/<payload>`) across all deployment modalities.

## Operational Footprints

| Footprint | Runtime Environment | Prerequisites | Isolation Model | Best For |
| :--- | :--- | :--- | :--- | :--- |
| [**Docker Container**](./010-docker.md) | Docker, Podman, Colima, OrbStack | Docker engine installed | Containerized sandbox; bundled D2 compiler and fonts | Fast local setup with zero local toolchain management |
| [**Native Python**](./020-local-python.md) | Local host (macOS, Linux, Windows) | Python 3.12+ (stdlib only) and `d2` in `$PATH` | Host process, runs offline in a temporary directory | Environments where Docker is restricted, CI runners, lean laptops |
| [**Google Cloud Run**](./030-cloud-run.md) | Serverless container on GCP | Google Cloud billing account, `gcloud` CLI | Ephemeral container instances with scale-to-zero | Shared team rendering, public GitHub README embeds, docs wikis |

## Contents

- [**010-docker.md**](./010-docker.md): Pulling from GHCR, port mapping, loopback binding, updating, and container troubleshooting.
- [**020-local-python.md**](./020-local-python.md): Host setup, installing D2, CLI flags (`--port`, `--bind`), and background daemon options.
- [**030-cloud-run.md**](./030-cloud-run.md): One-time GCP provisioning, keyless GitHub Actions OIDC deploy, and public access IAM toggles.

## Next Steps

- Once the service is running on any target, consult the [API Reference](../020-api-reference.md) to draw diagrams.
- Verify your renderer live with the [Visualizations Test Document](../visualizations/test-preview.md).
