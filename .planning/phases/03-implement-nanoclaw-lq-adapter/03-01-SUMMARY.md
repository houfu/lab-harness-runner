---
phase: 03-implement-nanoclaw-lq-adapter
plan: "01"
subsystem: nanoclaw-adapter
tags: [adapter, sqlite, polling, tdd, security]
dependency_graph:
  requires: []
  provides:
    - lab_harness_runner.nanoclaw_adapter.NanoclawAdapter
    - tests/test_nanoclaw_adapter.py
    - tests/conftest.py outbound_db fixture
  affects:
    - lab_harness_runner/nanoclaw_adapter.py
tech_stack:
  added: []
  patterns:
    - open/read/close per SQLite iteration (one-writer invariant)
    - TDD RED/GREEN for adapter logic
    - _reject_unsafe_relative_path for group_id path safety
key_files:
  created:
    - lab_harness_runner/nanoclaw_adapter.py
    - tests/test_nanoclaw_adapter.py
  modified:
    - tests/conftest.py
decisions:
  - "NanoclawAdapter.run() stubbed with NotImplementedError — dispatch wired in Plan 02"
  - "outbound_db fixture appended to conftest.py (not inline in test file) for shared use"
  - "TDD RED commit (597f790) precedes GREEN commit (fdca0a7) — gate compliance preserved"
metrics:
  duration_seconds: 157
  completed_date: "2026-05-31"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
requirements_satisfied:
  - REQ-STATUS
  - REQ-TIMEOUT
  - REQ-ENDSTATE
  - REQ-DELIVERABLE
---

# Phase 03 Plan 01: NanoclawAdapter Core Logic and Tests Summary

NanoclawAdapter class with STATUS: poll loop, end-state mapping (clean/agent_error/timeout), D-04/D-05 message footer builder, and group_id path safety — all unit-proven against a synthetic outbound.db fixture without a daemon or Docker.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add synthetic outbound_db fixture to conftest.py | 3cf5223 | tests/conftest.py |
| 2 TDD-RED | Add failing tests for NanoclawAdapter | 597f790 | tests/test_nanoclaw_adapter.py |
| 2 TDD-GREEN | Implement NanoclawAdapter poll loop, end-state, footer | fdca0a7 | lab_harness_runner/nanoclaw_adapter.py, tests/test_nanoclaw_adapter.py, tests/conftest.py |

## What Was Built

### `lab_harness_runner/nanoclaw_adapter.py`

`NanoclawAdapter` class with:

- `__init__(nanoclaw_dir, group_id, timeout_seconds=600.0, poll_interval=5.0)` — calls `_reject_unsafe_relative_path(group_id, "group_id")` to enforce path safety (T-03-01 mitigated)
- `_poll_for_status(outbound_db_path, timeout_seconds, poll_interval) -> str` — wall-clock deadline loop; opens/reads/closes SQLite per iteration (T-03-02 mitigated); parses `messages_out.content` JSON; maps `STATUS: DONE` -> `"clean"`, any other `STATUS:` -> `"agent_error"`; missing/locked DB silently retried; returns `"timeout"` after deadline
- `_build_message_content(task_spec) -> str` — appends D-04/D-05 footer to `task_spec.instructions` with `/workspace/extra/lab-output/` output path, required filenames, `STATUS: DONE` / `STATUS: ERROR` signals; returns JSON-encoded message
- `run(task_spec, output_dir) -> RunResult` — stub raises `NotImplementedError("dispatch wired in Plan 02")`

### `tests/test_nanoclaw_adapter.py`

7 unit tests covering all required behaviors:
- `test_poll_status_done_returns_clean` (REQ-STATUS, REQ-ENDSTATE)
- `test_poll_status_error_returns_agent_error` (REQ-STATUS, REQ-ENDSTATE)
- `test_poll_non_done_status_returns_agent_error` (REQ-STATUS, REQ-ENDSTATE)
- `test_poll_timeout_returns_timeout` (REQ-TIMEOUT)
- `test_poll_missing_db_does_not_raise` (REQ-TIMEOUT)
- `test_build_message_content_includes_contract` (REQ-DELIVERABLE)
- `test_unsafe_group_id_rejected` (T-03-01)

### `tests/conftest.py`

Added `outbound_db(tmp_path)` fixture that creates a real SQLite `outbound.db` under `v2-sessions/ag-test/sess-test/` with the `messages_out (seq AUTOINCREMENT, content TEXT)` schema, mirroring nanoclaw's data directory layout.

## Verification

- `uv run pytest tests/ -q` — 52 tests passed in 0.71s (7 new + 45 existing)
- `uv run black --check` — all 3 files unchanged after formatting
- `NanoclawAdapter` imports cleanly; all three methods present
- `conn.close()` appears inside poll loop before `time.sleep` (no persistent connections)
- `_reject_unsafe_relative_path(group_id` and `ORDER BY seq` confirmed in source

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED | 597f790 | `test(03-01): add failing tests for NanoclawAdapter (TDD RED)` |
| GREEN | fdca0a7 | `feat(03-01): implement NanoclawAdapter poll loop, end-state mapping, and footer` |

RED gate verified: tests failed with `ModuleNotFoundError` before implementation.

## Deviations from Plan

None - plan executed exactly as written. Task 3 (full test file) was created as part of the TDD RED phase for Task 2 since the test file is the artifact for both tasks.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes beyond what was planned. Threat mitigations T-03-01 and T-03-02 were implemented as specified.

## Self-Check: PASSED

Files verified:
- lab_harness_runner/nanoclaw_adapter.py: FOUND
- tests/test_nanoclaw_adapter.py: FOUND
- tests/conftest.py: FOUND (modified)

Commits verified:
- 3cf5223 (feat: outbound_db fixture): FOUND
- 597f790 (test: TDD RED): FOUND
- fdca0a7 (feat: implementation GREEN): FOUND
