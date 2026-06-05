---
phase: 05-honest-unmeasured-metrics-contract
plan: 01
subsystem: testing
tags: [metrics, contract, runresult, write_metrics, null-vs-zero, con-01, con-02]

# Dependency graph
requires: []
provides:
  - "RunResult list fields (documents_read_list, documents_skipped_list) are nullable; field default is None"
  - "write_metrics serialises the eight LAB-compatible fields directly off result; None writes JSON null on disk"
  - "Diagnostic field null-stripping (extra_fields) preserved per D-03"
  - "test_metrics.py aligned with the new \"None -> null\" contract"
affects: [05-02, 05-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON null vs Python None as the unmeasured signal on disk (CON-01, CON-02)"
    - "Per-field explicit None as the contract primitive; downstream _numeric_values filter naturally excludes None (D-09)"

key-files:
  created: []
  modified:
    - lab_harness_runner/adapter.py
    - lab_harness_runner/metrics.py
    - tests/test_metrics.py
    - tests/test_fake_run.py

key-decisions:
  - "Field default is None, not field(default_factory=list) — measured-empty stays [] (D-08); unmeasured is None"
  - "write_metrics reads result.X directly and lets json.dumps native None->null behaviour take over; no explicit coercion layer"
  - "end_state remains the only required, non-nullable field; wall_clock_seconds is required float"
  - "test_fake_run.py updated to expect null for unset token fields, not 0 (the old assertion was the bug, not the test)"

patterns-established:
  - "Pattern: every RunResult metric field declared as `int | None = None` or `list[str] | None = None`; on-disk JSON `null` means \"adapter did not measure\" distinct from a measured 0 or []"
  - "Pattern: write_metrics builds the dict from direct attribute reads; _without_null_values still applies only to extra_fields (D-03 invariant)"

requirements-completed: [CON-01, CON-02]

# Metrics
duration: ~5min
completed: 2026-06-05
---

# Phase 05 Plan 01 Summary

**RunResult list fields are now nullable and write_metrics propagates `None` to JSON `null` on disk — the core of CON-01 and the on-disk half of CON-02.**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2 of 2 completed
- **Files modified:** 4 (`adapter.py`, `metrics.py`, `tests/test_metrics.py`, `tests/test_fake_run.py`)

## Accomplishments

- `RunResult.documents_read_list` and `RunResult.documents_skipped_list` are now typed `list[str] | None = None`; the `field(default_factory=list)` import is removed; the `RunResult` docstring documents the None contract.
- `write_metrics` no longer coerces `None` to `0` or `[]` for any of the eight LAB-compatible fields; the dict construction is a direct attribute read on `result` and `json.dumps` serialises `None` as `null` natively.
- `_without_null_values` is preserved and still applied to `extra_fields` (D-03 — diagnostic `None` values are still stripped, the LAB-metric null contract is independent).
- `tests/test_metrics.py` is updated to the new contract: three new tests (`test_write_metrics_unmeasured_fields_written_as_null`, `test_write_metrics_unmeasured_list_field_written_as_null`, `test_write_metrics_explicit_zero_preserved`), the no-null guard test is deleted, the safe-defaults test is replaced, and the diagnostics test is narrowed to its actual scope.
- `tests/test_fake_run.py` is updated: `FakeAdapter.run()` does not measure token usage, so under the new contract the JSON now correctly carries null for `input_tokens` / `output_tokens` — the old `== 0` assertion was the symptom of the contract bug.
- Full test suite is green: 110 tests pass.

## Task Commits

1. **Task 1: Make RunResult list fields nullable and remove None coercion in write_metrics** — `8a8f7ae` (feat)
2. **Task 2: Replace and update tests in test_metrics.py to match the new contract** — `7cc7ac8` (test)

## Files Created/Modified

- `lab_harness_runner/adapter.py` — D-07: list fields typed `list[str] | None = None`; unused `field` import removed; docstring updated.
- `lab_harness_runner/metrics.py` — D-01, D-08: `write_metrics` reads the eight LAB-compatible fields directly off `result`; no `None` coercion; docstring updated to describe the null contract and preserve D-03.
- `tests/test_metrics.py` — D-17: replaced 2 tests, added 3 tests, deleted 1 test, narrowed 1 test.
- `tests/test_fake_run.py` — assert `None` for unset token fields (the new honest contract) rather than `0` (the old coerced contract).

## Decisions Made

None — followed plan as specified. The plan's Task 1 acceptance criteria, Task 2 acceptance criteria, and `<verification>` block are all met.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 5 — Inconsistent with new contract] Updated test_fake_run.py to expect null, not 0**
- **Found during:** Task 2 (running the full test suite after the test_metrics changes)
- **Issue:** `tests/test_fake_run.py::test_fake_run_wires_task_adapter_result_dir_and_metrics` still asserted `metrics["input_tokens"] == 0` and `metrics["output_tokens"] == 0` because `FakeAdapter.run()` does not set those fields. Under the new contract, the on-disk JSON now carries `null` for them (which is the correct, honest behaviour). The plan's "Additional Code Surface" section called this out — "the behavior change is automatic and correct" — but the test was not in the plan's "files_modified" list and so was not pre-emptively updated.
- **Fix:** Updated the two assertions to `is None` with a comment explaining the new contract. Behaviour change in `fake_run.py` itself is not required (and was explicitly out of scope per the plan).
- **Files modified:** `tests/test_fake_run.py`
- **Verification:** `uv run python -m pytest -q` is green (110 passed).
- **Committed in:** `7cc7ac8` (Task 2 commit, alongside the test_metrics changes since both are part of the same "tests reflect the new contract" work item)

---

**Total deviations:** 1 auto-fixed (inconsistent with new contract)
**Impact on plan:** Auto-fix necessary for test suite to be green. No scope creep — this is the same test-aligned-with-contract work item the plan's additional-code-surface section anticipated.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `write_metrics` is the single sink for `metrics.json`; the on-disk contract is now honest (`null` = unmeasured, `0` = measured zero).
- `RunResult` distinguishes measured-empty (`[]`) from unmeasured (`None`) for both list fields.
- Plan 02 (05-02) can now build on this contract: `_batch_row` should let `None` flow through (D-14) and `build_summary` should compute the per-row `metrics_provided` boolean and top-level `unmeasured_counts` over rows that now correctly carry `None` for unmeasured fields.
- The downstream `_numeric_values` filter in `aggregation.py` already excludes `None` via its `isinstance(value, int|float)` check (verified in Phase 5 research), so the variance path needs no change for null semantics.
- No blockers.

---
*Phase: 05-honest-unmeasured-metrics-contract*
*Completed: 2026-06-05*
