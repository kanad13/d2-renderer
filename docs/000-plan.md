# Active Plan

Goal: No active milestone. The last one, a local daemon script with a corrected ownership model and single-file decision records, is merged.

Acceptance: `python3 -m unittest discover -s tests -v` passes against a running server, and `python3 scripts/build-render-check.py` shows every diagram rendering in both panels.

Next action: Pick the next milestone, then record its goal and acceptance check here. To confirm the current state, run `./scripts/manage-daemon.sh up`, run the suite above, then `./scripts/manage-daemon.sh down`.

Blockers: none

Recent context:

- [x] Merged the local daemon script ([Decision 010](./060-decisions.md#decision-010---local-daemon-management-script)), single-file decisions and the scaffolding layout.
