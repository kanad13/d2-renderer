# 030. Deploy with keyless workload identity federation

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

GitHub Actions must deploy to Cloud Run. The repository and workflow are public, so any stored credential is a leak risk.

## Decision

Use workload identity federation. GitHub signs a short-lived token for each run; Google accepts it only when it claims `<owner>/<repo>` on `refs/heads/main`. The condition is set on the identity provider, because IAM bindings cannot test token claims such as the branch. The deployer account holds `run.admin` on the project and `serviceAccountUser` on the runtime account only. The container runs as a separate account with no roles.

## Rejected

- **Service account JSON key stored as a GitHub secret:** long-lived, leaks silently, needs rotation.
- **Granting the deployer `serviceAccountUser` on the whole project:** wider than needed.

## Consequences

- Forks and pull requests cannot deploy: their tokens fail the condition.
- A fork owner repeats the setup with their own repository name ([runbook](../020-deploy-gcp.md)).
- A leaked workflow file reveals identifiers but grants nothing.

## Navigation

- [Decision index](./README.md)
