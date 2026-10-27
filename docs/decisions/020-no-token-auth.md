# 020. No shared-secret token

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

An optional token (header or `?token=`) was proposed to reject bots cheaply. The intended use is `<img src>` tags on public pages, which cannot send headers.

## Decision

No authentication. The service is open and protects itself with size and time limits ([050](./050-traffic-limits-and-cost-guardrails.md)).

## Rejected

- **Token in the URL:** visible to anyone who views the page source, so it only stops crawlers that never read the page. It also lands in request logs.
- **Cloud Run IAM (private service):** browsers cannot authenticate image requests. A signing proxy would add moving parts for a personal service.
- **Cloud Armor or a load balancer:** real protection, but not free.

## Consequences

- Anyone can render diagrams, up to the limits and one instance.
- Abuse shows up as cost or cache churn; the budget alert is the signal.
- If abuse appears later, revisit this with a new record (for example allowlisting origins at an edge proxy).

## Navigation

- [Decision index](./README.md)
