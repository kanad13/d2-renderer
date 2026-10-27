# Decision Records

## Purpose

Each file records one choice: the situation, what was chosen, what was rejected, and what it costs. Accepted records are never rewritten. A changed mind becomes a new record that supersedes the old one.

## Start Here

Read in order; each is under a page.

## Contents

| Record                                                                                   | Decision                                                                             |
| :--------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| [010-eu-region-belgium.md](./010-eu-region-belgium.md)                                   | Run in Belgium (`europe-west1`) for EU data location and full free-tier eligibility. |
| [020-no-token-auth.md](./020-no-token-auth.md)                                           | No shared-secret token: URLs are public, so a token would not protect anything.      |
| [030-keyless-github-deploy.md](./030-keyless-github-deploy.md)                           | Deploy through workload identity federation, no stored keys.                         |
| [040-public-image-pulled-directly.md](./040-public-image-pulled-directly.md)             | Cloud Run pulls the public GHCR image directly.                                      |
| [050-traffic-limits-and-cost-guardrails.md](./050-traffic-limits-and-cost-guardrails.md) | Limits and a budget alert instead of a hard spending cap.                            |
| [060-offline-compile-in-empty-directory.md](./060-offline-compile-in-empty-directory.md) | Compile offline in an empty directory: no outbound requests, no imports. |
| [070-static-svg-diagrams-in-docs.md](./070-static-svg-diagrams-in-docs.md) | Show documentation diagrams as committed SVG files with their D2 source beside them. |
| [080-multi-architecture-image.md](./080-multi-architecture-image.md) | Publish `linux/amd64` and `linux/arm64` from one tag. |

## Record format

Status, date, context, decision, rejected alternatives, consequences.

## Navigation

- [Documentation index](../README.md)
