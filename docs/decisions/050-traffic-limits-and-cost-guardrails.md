# 050. Traffic limits and a budget alert, not a hard cap

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The service is public and each uncached render starts a process. Google Cloud has no built-in hard spending cap; budgets only send email. The only automatic stop detaches billing from the project, which takes everything down, may lag, and can delete resources.

## Decision

- Cloud Run: one instance maximum, minimum zero, concurrency 8, request timeout 30 s, 1 vCPU and 512 MiB.
- Service: 20 s render limit, 256 KiB input limit, 256-entry cache (see [architecture](../010-architecture.md)).
- A budget alert at 50% and 100% of a small amount.

## Rejected

- **Automatic billing shutoff:** too blunt for a hobby service, and not instantaneous.
- **Concurrency 40 and a 10 s timeout:** 40 parallel D2 processes risk running out of memory; 10 s may clip large diagrams.
- **Always-on instance:** costs money while idle.

## Consequences

- Worst-case cost is bounded in rate but not in monthly total. A sustained flood would be noticed through the alert, not stopped.
- Normal personal use stays far inside the free allowance.
- Limits are env-tunable without a rebuild ([operations](../030-operations.md#tuning-limits)).

## Navigation

- [Decision index](./README.md)
