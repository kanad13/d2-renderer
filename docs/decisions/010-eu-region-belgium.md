# 010. Run in Belgium (`europe-west1`)

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The service should process requests in the EU. Cloud Run's free allowance is calculated at Tier 1 prices, so a Tier 2 region (Frankfurt, London, Zurich, Berlin) would use it up faster.

## Decision

Deploy to `europe-west1` (Belgium), a Tier 1 EU region. The region is a parameter in the setup script and workflow variables, so forks can choose another.

## Rejected

- **Iowa (`us-central1`):** the usual free-tier example, but not in the EU.
- **Frankfurt:** closer to many EU users, but Tier 2 pricing.

## Consequences

- Processing and request logs stay in the EU. This is data location, not full GDPR compliance; request logs contain diagram URLs.
- Free-tier outbound data (1 GiB) covers North America only, so EU egress is billed. Volume is small.
- Latency is higher for users far from Belgium.
- The container image is pulled from GitHub, which is outside the EU. It holds code, not user data.

## Navigation

- [Decision index](./README.md)
