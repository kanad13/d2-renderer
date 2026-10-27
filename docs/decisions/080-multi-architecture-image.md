# 080. Publish `linux/amd64` and `linux/arm64`

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The main local use is a container on a developer machine, and many of those machines are Apple Silicon Macs. An amd64-only image failed to pull there with "no matching manifest for linux/arm64/v8". Cloud Run needs amd64.

## Decision

- Build one manifest list with both platforms, using QEMU and buildx in the publish job.
- Fail the publish job unless `docker buildx imagetools inspect` lists both platforms.
- Keep deploying the commit-SHA tag; Cloud Run selects the amd64 entry.

## Rejected

- **Other architectures (arm/v7, 386, riscv64, ppc64le, s390x):** the `d2lang/d2` image publishes only amd64 and arm64, so each would need D2 built from source.
- **Separate tags per architecture:** users would have to choose, and the quickstart would need a flag.

## Consequences

- One `docker run` command works on Intel, AMD and Arm hosts.
- The publish job runs longer because the arm64 build is emulated.
- Both platforms render the bundled TALA layout; the arm64 image was run natively on an Apple Silicon Mac.

## Navigation

- [Decision index](./README.md)
