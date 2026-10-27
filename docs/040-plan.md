# Delivery Plan

Phases that took `d2-renderer` from a local container to a public EU deployment, with the check that proves each one.

| Phase                 | Outcome                                                                                              | Proof                                                                           | Status |
| :-------------------- | :--------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------ | :----- |
| 1. Harden the service | Time and size limits, env-driven port, pinned D2, tests for the 413 paths                            | `python3 -m unittest discover -s tests -v` against a rebuilt container          | Done   |
| 2. Google Cloud setup | Project, identities, keyless GitHub trust, budget alert, via [gcp-setup.sh](../scripts/gcp-setup.sh) | Script finishes and prints the five GitHub variables                            | Done   |
| 3. First deploy       | Service live in an EU region with the agreed limits                                                  | Health check and diagrams return from the service address                       | Done   |
| 4. Automatic deploys  | Push to `main` tests, publishes and deploys by commit SHA                                            | The `Deploy to Cloud Run` job succeeds and the live revision runs the new image | Done   |
| 5. Documentation      | Architecture, runbook, operations, decision records                                                  | [Markdown audit](../AGENTS.md) clean                                            | Done   |
| 6. Ongoing checks     | Watch cost for a month, then revisit limits                                                          | Billing report near zero; no alert emails                                       | Open   |

## Session goal

Every coding session ends with the render check: `python3 scripts/build-render-check.py`, then look at the page. Both the local and the Cloud Run column must show real diagrams. Details in [AGENTS.md](../AGENTS.md).

## Open items

- A test for the render time limit (needs a deliberately slow diagram).
- Decide after a month of billing data whether the limits need adjusting.

## Navigation

- [Documentation index](./README.md)
- Previous: [Operations](./030-operations.md)
