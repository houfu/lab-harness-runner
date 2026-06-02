---
phase: 03-implement-nanoclaw-lq-adapter
plan: "02"
subsystem: nanoclaw-adapter
tags: [adapter, dispatch, subprocess, sqlite, mounts, node-shim]
dependency_graph:
  requires: ["03-01"]
  provides: ["NanoclawAdapter.run()", "scripts/send-lab-message.ts", "scripts/nanoclaw_run.py"]
  affects: ["lab_harness_runner/nanoclaw_adapter.py", "tests/test_nanoclaw_adapter.py"]
tech_stack:
  added: []
  patterns:
    - "subprocess list-form dispatch to Node shim (no shell=True)"
    - "sqlite3 open/operate/close per op (one-writer invariant)"
    - "AdditionalMountConfig JSON written to container_configs before wake"
    - "UUID4 message IDs from Python; shim returns sessionId + outboundDbPath as JSON stdout"
key_files:
  created:
    - /Users/houfu/Projects/nanoclaw-lq/scripts/send-lab-message.ts
    - scripts/nanoclaw_run.py
  modified:
    - lab_harness_runner/nanoclaw_adapter.py
    - tests/test_nanoclaw_adapter.py
decisions:
  - "Mount configuration uses two hardcoded relative containerPaths (lab-documents, lab-output) — no caller-controlled paths (T-03-04/T-03-06)"
  - "Central DB path is nanoclaw_dir/data/v2.db (confirmed from nanoclaw-lq/src/index.ts)"
  - "Shim JSON stdout carries both sessionId and outboundDbPath so adapter needs no path reconstruction"
  - "Dispatch test uses a minimal stub container_configs table in tmp_path; no daemon needed"
metrics:
  duration: "~480 seconds"
  completed: "2026-05-31"
  tasks_completed: 3
  files_created_or_modified: 4
---

# Phase 3 Plan 02: Nanoclaw Dispatch and Mount Wiring Summary

**One-liner:** Node shim dispatches LAB tasks via nanoclaw session-manager + wakeContainer; Python adapter configures two hardcoded mounts before wake and polls outbound.db for STATUS: signal.

## What Was Built

### Task 1: Node Dispatch Shim (external repo)
Created `/Users/houfu/Projects/nanoclaw-lq/scripts/send-lab-message.ts`.
The shim imports `resolveSession`, `writeSessionMessage`, `writeSessionRouting`, `outboundDbPath`
from `../src/session-manager.js` and `wakeContainer` from `../src/container-runner.js` (the
nanoclaw-lq repo's ESM/tsx module style). It parses `--group-id`, `--message-id`, and
`--content` from argv; exits nonzero with a stderr message on missing flags; calls the full
session lifecycle sequence; and prints `{"sessionId": ..., "outboundDbPath": ...}` to stdout.

Type-checking: `pnpm exec tsc --noEmit` passes with zero errors.
Missing-flag guard: confirmed exits 1 with stderr message.
Note: `tsx --check` is not available (Node 22 rejects `.ts` extension under `--input-type`);
`tsc --noEmit` was used as the equivalent type-check.

**This file lives in the nanoclaw-lq repo and was NOT committed to lab-harness-runner.**

### Task 2: NanoclawAdapter.run() — mounts, dispatch, poll, result
Replaced the `NotImplementedError` stub in `lab_harness_runner/nanoclaw_adapter.py`.
The four-step sequence: (1) configure `additional_mounts` in `container_configs` (sqlite3
UPDATE open/commit/close), (2) dispatch via subprocess list-form to `send-lab-message.ts`,
(3) poll outbound.db with `_poll_for_status()`, (4) return `RunResult`. Mounts precede
dispatch (Pitfall 4). Only `task_spec.documents_dir` and `output_dir` are written as
hostPaths (T-03-04). containerPaths are bare relative names (T-03-06). Explicit list-form
subprocess with no `shell=True` (T-03-05). Central DB located at `nanoclaw_dir/data/v2.db`.

Commit: `0127b61`

### Task 3: nanoclaw_run.py CLI and dispatch unit test
`scripts/nanoclaw_run.py` mirrors `scripts/fake_run.py` exactly but substitutes
`NanoclawAdapter` and adds `--nanoclaw-dir` (required), `--group-id` (required), and
`--timeout` (float, default 600.0) args. `--group-id` is validated via
`_reject_unsafe_relative_path`.

`tests/test_nanoclaw_adapter.py` extended with `test_dispatch_calls_shim_and_returns_clean`:
patches `lab_harness_runner.nanoclaw_adapter.subprocess.run`, returns a MagicMock whose
`stdout` is a JSON line pointing at the `outbound_db` fixture (pre-inserted STATUS: DONE),
stubs `container_configs` via a minimal SQLite DB in tmp_path. Asserts command contains
`send-lab-message.ts` and `--group-id`, and that `run()` returns `end_state == "clean"`.

Full suite: 53 tests pass. black clean on all files.

Commit: `2eee1a6`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tsx --check` unavailable on Node 22 — used `tsc --noEmit` instead**
- **Found during:** Task 1 verification
- **Issue:** `pnpm exec tsx --check scripts/send-lab-message.ts` fails with
  `ERR_UNKNOWN_FILE_EXTENSION` under Node 22 because `--check` invokes Node's built-in
  syntax checker, which cannot handle `.ts` extensions.
- **Fix:** Used `pnpm exec tsc --noEmit` which passes cleanly (zero output = zero errors).
  This is equivalent: tsc type-checks the full project including the new shim.
- **Files modified:** none (verification approach only)

**2. [Rule 1 - Bug] Dispatch test assert used `in` on list — shim path is `scripts/send-lab-message.ts`**
- **Found during:** Task 3 test run
- **Issue:** `assert "send-lab-message.ts" in cmd` fails because the full element is
  `"scripts/send-lab-message.ts"`.
- **Fix:** Changed to `any("send-lab-message.ts" in arg for arg in cmd)`.

## Daemon/Docker Integration Checks — Deferred to Plan 03

Per checkpoint guidance, these verifications require the running nanoclaw-lq daemon and Docker
and are explicitly deferred to Plan 03's human checkpoint:

| Check | Why Deferred |
|-------|-------------|
| Shim creates a session and prints JSON stdout with real daemon | Daemon must be running |
| Documents appear at /workspace/extra/lab-documents inside container | Docker required |
| Output appears at /workspace/extra/lab-output inside container | Docker required |
| `nanoclaw_run.py` end-to-end with real task and group | Daemon + Docker + LAB group setup |

## Known Stubs

None. All code paths are fully implemented. The run() method no longer contains
`NotImplementedError`.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust
boundaries were introduced beyond what was planned in the threat model. All T-03-04 through
T-03-SC mitigations are in place per the plan.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| /Users/houfu/Projects/nanoclaw-lq/scripts/send-lab-message.ts | FOUND |
| lab_harness_runner/nanoclaw_adapter.py | FOUND |
| scripts/nanoclaw_run.py | FOUND |
| tests/test_nanoclaw_adapter.py | FOUND |
| Commit 0127b61 (NanoclawAdapter.run()) | FOUND |
| Commit 2eee1a6 (nanoclaw_run.py + dispatch test) | FOUND |
