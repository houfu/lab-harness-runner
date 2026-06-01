---
phase: 04-completion-metrics-evaluation-and-scale-out
plan: 01
subsystem: metrics
tags: [python, pytest, benchmark-status, metrics-json, lab]
requires:
  - phase: 03-implement-nanoclaw-lq-adapter
    provides: Nanoclaw raw end_state evidence and deliverable-producing proof run
provides:
  - Benchmark-facing status derivation separate from raw adapter end_state
  - Diagnostic metrics fields for whole agent-system reporting
  - Unit coverage for timeout-with-valid-deliverables semantics
affects: [04-02-primary-benchmark-command, 04-03-aggregation, adapter-guide]
tech-stack:
  added: []
  patterns:
    - Derive benchmark_status from expected deliverable validation while preserving raw_end_state
    - Merge optional metrics diagnostics after LAB-compatible metric keys
key-files:
  created:
    - lab_harness_runner/status.py
    - tests/test_status.py
  modified:
    - lab_harness_runner/metrics.py
    - lab_harness_runner/__init__.py
    - tests/test_metrics.py
key-decisions:
  - "Timeout runs with all expected deliverables present are benchmark_status=clean while raw_end_state remains timeout."
  - "Unsafe expected deliverable names are rejected before joining with output_dir."
requirements-completed: [REQ-09, REQ-21]
duration: 42min
completed: 2026-06-01
---

# Phase 4 Plan 01: Benchmark Status Semantics and Metrics Diagnostics Summary

**Benchmark status layer that treats evaluable deliverables as benchmark-clean while preserving raw adapter timeout diagnostics in metrics.**

## Performance

- **Duration:** 42 min, including interruption recovery
- **Started:** 2026-06-01T15:27:33Z
- **Completed:** 2026-06-01T16:09:10Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `derive_benchmark_status` to combine expected-deliverable validation with raw adapter `RunResult.end_state`.
- Preserved diagnostic evidence in status output: `raw_end_state`, `terminal_status_seen`, `completion_signal`, `expected_deliverables_present`, and `missing_deliverables`.
- Extended `write_metrics` with optional diagnostic fields while preserving the old two-argument call and existing LAB metric keys.
- Added pytest coverage for mixed timeout-with-valid-output semantics, missing deliverables, unsafe deliverable paths, diagnostics writing, and backwards-compatible metrics writing.

## Task Commits

1. **Task 1: Add benchmark status derivation tests** - `d555516` (included in implementation commit)
2. **Task 2: Implement status diagnostics and metrics extension** - `d555516` (feat)
3. **Task 3: Full-suite status regression check** - no file changes; validation passed

## Files Created/Modified

- `lab_harness_runner/status.py` - Benchmark status derivation and safe deliverable validation diagnostics.
- `lab_harness_runner/metrics.py` - Optional diagnostics merge for `metrics.json` with JSON null filtering.
- `lab_harness_runner/__init__.py` - Public export for `derive_benchmark_status`.
- `tests/test_status.py` - Unit coverage for benchmark status semantics and unsafe deliverable names.
- `tests/test_metrics.py` - Diagnostics and backwards-compatibility coverage.

## Decisions Made

- Benchmark status is `clean` whenever all expected deliverables exist, regardless of raw timeout state.
- Missing deliverables preserve `timeout` for raw timeout runs and become `error` for raw agent errors.
- `completion_signal` uses `"STATUS:DONE"` for raw clean, `"STATUS:ERROR"` for raw agent error, and an empty string for timeout so metrics contain no JSON null values.

## Deviations from Plan

No functional deviations. The plan behavior and owned file scope were followed.

## Issues Encountered

- The initial RED test run failed as intended because `lab_harness_runner.status` did not exist.
- The sandbox blocked the first attempt to stage a separate RED commit by denying `.git/index.lock` creation. After the user interruption, Task 1 tests and Task 2 implementation were committed together as `d555516` rather than split into separate TDD commits.

## Validation

- `uv run pytest tests/test_status.py tests/test_metrics.py -q` - 18 passed
- `uv run pytest tests/ -q` - 62 passed

## User Setup Required

None - no external service configuration required.

## Next Plan Handoff

Plan 04-02 can call `derive_benchmark_status(...)` after adapter execution and pass the returned diagnostics into `write_metrics(..., extra_fields=diagnostics)` before scoring/reporting. Aggregation in Plan 04-03 should use `benchmark_status` for benchmark outcome and `raw_end_state` for protocol evidence.

## Self-Check: PASSED

- Created files exist: `lab_harness_runner/status.py`, `tests/test_status.py`, `.planning/phases/04-completion-metrics-evaluation-and-scale-out/04-01-SUMMARY.md`
- Modified files verified by tests: `lab_harness_runner/metrics.py`, `lab_harness_runner/__init__.py`, `tests/test_metrics.py`
- Task commit exists: `d555516`

---
*Phase: 04-completion-metrics-evaluation-and-scale-out*
*Completed: 2026-06-01*
