# 090. Pause deploys with a repository variable

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

Taking the public service offline (removing public access) is undone by the next deploy, because the deploy job passes `--allow-unauthenticated`. A maintainer who wants the service down needs pushes to keep testing and publishing images without reopening it.

## Decision

- The deploy job runs only while the repository variable `DEPLOY_ENABLED` is not `false`.
- Tests and the image publish keep running on every push.
- Resuming means deleting the variable and re-running the workflow.

## Rejected

- **Disabling the whole workflow:** also stops tests and image publishing.
- **Deleting the `GCP_*` variables:** loses configuration that is hard to recover, and any push after that silently skips deploys.
- **Deleting the Cloud Run service:** removes configuration and the service address that public pages embed.

## Consequences

- One command pauses deploys and one resumes them, with no change to the workflow file.
- A forgotten `DEPLOY_ENABLED=false` makes deploys skip silently; the job shows as skipped in the run list.
- The default, with the variable unset, keeps the existing behavior.

## Navigation

- [Decision index](./README.md)
