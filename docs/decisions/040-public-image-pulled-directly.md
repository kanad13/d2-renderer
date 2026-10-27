# 040. Cloud Run pulls the public GHCR image directly

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

CI already publishes the image to GitHub Container Registry. Mirroring it into Artifact Registry would add a repository, storage cost and setup steps.

## Decision

Keep the package public and deploy `ghcr.io/<owner>/<repo>:<full commit SHA>`. Cloud Run supports public GHCR images, and a unique tag per build avoids its image caching.

## Rejected

- **Artifact Registry remote repository:** needed only for private images; Google also suggests it for availability.
- **Tagging deploys with `latest`:** Cloud Run may serve a cached older image for up to an hour.

## Consequences

- No registry credentials anywhere.
- Deploys depend on GHCR availability.
- The image must stay public. A private package would need the remote repository route.

## Navigation

- [Decision index](./README.md)
