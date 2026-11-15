# Active Plan

Goal: No active milestone. The last one, a local daemon script with a corrected ownership model and single-file decision records, is merged.

Acceptance: `python3 -m unittest discover -s tests -v` passes against a running server (43 tests), and `python3 scripts/build-render-check.py` shows every diagram rendering in both panels.

Next action: Pick the next milestone, then record its goal and acceptance check here. To confirm the current state, run `./scripts/manage-daemon.sh up`, run the suite above, then `./scripts/manage-daemon.sh down`.

Blockers: none

Recent context:

- [x] Added `scripts/manage-daemon.sh` and `tests/test_manage_daemon.py`; fixed foreign-process kills and per-port state ([Decision 010](./060-decisions.md#decision-010---local-daemon-management-script)).
- [x] Merged the ten decision files into [060-decisions.md](./060-decisions.md).
- [x] Moved the testing guide to [tests/README.md](../tests/README.md) and the plan here.
