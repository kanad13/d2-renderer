# 090. On-demand Cloud Run deployment and IAM perimeter control

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The Cloud Run deployment operates as a technology demonstrator and on-demand personal utility, not an always-on public daemon. Diagram URLs are embedded in public pages or VS Code previews only during active testing or demonstrations.

Coupling Cloud Run deployments to everyday Git pushes created operational friction:

- Every push to `main` triggered a full Cloud Run redeployment that forced public access (`--allow-unauthenticated`), reopening the service even when the maintainer intentionally kept it offline.
- Attempting to pause deploys with repository variables (`DEPLOY_ENABLED`) introduced split-brain state between GitHub and Google Cloud IAM, caused silent CI skips, and complicated operations.

## Decision

- **Decouple deployment from everyday pushes:**
  - Pushes to `main` test the code and publish multi-architecture images (`linux/amd64`, `linux/arm64`) to GitHub Container Registry (`ghcr.io`).
  - The `deploy` job runs only on manual dispatch (`workflow_dispatch`), e.g. via `gh workflow run ci.yml`.
- **Deploy safely without unilateral exposure:**
  - Cloud Run deployments pass `--no-allow-unauthenticated`. Deploying code updates never exposes the service to the internet automatically.
- **Control service lifecycle via 1-command IAM toggle:**
  - Public access is controlled on demand directly at the Google edge:
    - Bring UP: `gcloud run services add-iam-policy-binding d2-renderer ... --member=allUsers --role=roles/run.invoker`
    - Take DOWN: `gcloud run services remove-iam-policy-binding d2-renderer ... --member=allUsers --role=roles/run.invoker`
- **Zero repository pause switches:**
  - The repository maintains no deploy-pause variables. Git pushes and Cloud Run runtime state are completely independent.

## Rejected

- **Auto-deploying on every push with `--allow-unauthenticated`:** forces the service online on every commit, overriding intentional shutdowns.
- **Auto-deploying on every push with `--no-allow-unauthenticated`:** strips public access on every commit even when the maintainer intentionally opened it for a demonstration.
- **Pausing deploys with repository variables (`DEPLOY_ENABLED`):** creates split-brain state, silent skips in CI, and multi-step manual overhead.
- **Setting `max-instances=0`:** rejected by Knative and Google Cloud Run control planes, which require `maxScale >= 1`.

## Consequences

- Everyday commits, refactors, and doc improvements build and publish container images without touching live Cloud Run instances.
- When taken offline, requests return `403 Forbidden` at Google Frontend without reaching Cloud Run, ensuring 0 instances run and $0 is billed.
- A new maintainer or fork author can push code freely without accidental cloud deployments.

## Navigation

- [Decision index](./README.md)
