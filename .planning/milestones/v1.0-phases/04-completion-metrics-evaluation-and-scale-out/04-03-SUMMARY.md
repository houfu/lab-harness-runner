---
phase: 04-completion-metrics-evaluation-and-scale-out
plan: 03
subsystem: aggregation
tags: [python, argparse, pytest, lab, batch, variance]
requires:
  - phase: 04-completion-metrics-evaluation-and-scale-out
    provides: Primary benchmark command and run_single_benchmark metadata from Plan 04-02
provides:
  - Metadata-only batch summaries under LAB results/batches/<batch-id>/summary.json
  - Task x seed batch expansion around normal LAB results/<run-id>/ folders
  - Variance summaries for score and operational metrics before performance claims
affects: [04-04-adapter-guide, phase-4-verification]
tech-stack:
  added: []
  patterns:
    - Keep aggregate metadata separate from per-run LAB result folders
    - Treat seed as batch metadata only, not deterministic adapter control
    - Use stdlib statistics for count/mean/min/max/sample-stdev summaries
key-files:
  created:
    - lab_harness_runner/aggregation.py
    - tests/test_aggregation.py
  modified:
    - lab_harness_runner/__init__.py
    - scripts/run_benchmark.py
    - tests/test_run_benchmark.py
key-decisions:
  - "Batch summaries are written only as results/batches/<batch-id>/summary.json; no aggregate scores.json is created."
  - "Seeds are recorded in aggregate rows and passed through batch metadata without claiming deterministic adapter seeding."
  - "A fixed --run-id is rejected when batch expansion would produce multiple runs to prevent LAB path collisions."
patterns-established:
  - "Batch rows include run_id, run_dir, output_dir, metrics_path, scores_path, report_path, task, seed, adapter, benchmark status, raw end_state, deliverable validation, and variance inputs."
  - "Batch CLI accepts repeated --task, --tasks files, --seeds comma lists, and --batch-id while preserving single-run behavior."
requirements-completed: [REQ-15, REQ-21, REQ-22]
duration: 5min
completed: 2026-06-01
---

# Phase 4 Plan 03: Multi-task Multi-seed Aggregation and Variance Reporting Summary

**Metadata-only LAB batch summaries with task x seed execution rows and variance over score, timing, token, and document-coverage metrics.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-01T16:18:29Z
- **Completed:** 2026-06-01T16:22:59Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `lab_harness_runner.aggregation` with `summarize_variance`, `build_summary`, and `write_batch_summary`.
- Extended `scripts/run_benchmark.py` with repeated `--task`, `--tasks`, `--seeds`, and `--batch-id` support.
- Preserved every adapter run under normal LAB `results/<run-id>/` folders and wrote only metadata to `results/batches/<batch-id>/summary.json`.
- Added tests covering metadata-only summary placement, no aggregate `scores.json`, variance fields, parser flags, task x seed expansion, and fixed-run-id collision protection.

## Task Commits

1. **Task 1: Add aggregation and variance tests** - `7521f75` (test)
2. **Task 2: Implement aggregation helpers and batch CLI loop** - `b36ae2b` (feat)
3. **Task 3: Full-suite aggregation regression check** - no file changes; validation passed

## Files Created/Modified

- `lab_harness_runner/aggregation.py` - Batch summary construction, variance helpers, and metadata-only summary writer.
- `lab_harness_runner/__init__.py` - Public exports for aggregation helpers.
- `scripts/run_benchmark.py` - Batch task/seed expansion and summary writing around the existing single-run path.
- `tests/test_aggregation.py` - Unit coverage for variance and metadata-only summary paths.
- `tests/test_run_benchmark.py` - Parser and batch orchestration coverage.

## Decisions Made

- Batch summaries use the preferred LAB-compatible path `results/batches/<batch-id>/summary.json`.
- Batch runs without an explicit seed use `"default"` as metadata; seed values are not treated as deterministic adapter controls.
- Batch rows fill unavailable optional score/report/operational fields with empty strings rather than JSON nulls.
- `--run-id` remains allowed for one run but is rejected when task x seed expansion would create more than one run.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Issues Encountered

- RED tests failed as intended because `lab_harness_runner.aggregation` did not exist.
- `black` emitted a Python target-version warning while formatting but completed successfully; tests passed afterward.

## Validation

- `uv run pytest tests/test_aggregation.py tests/test_run_benchmark.py -q` - 19 passed
- `uv run pytest tests/ -q` - 86 passed
- `uv run python scripts/run_benchmark.py --help` - passed
- `uv run python -c "from pathlib import Path; raise SystemExit(1 if any(Path('/Users/houfu/Projects/harvey-labs/results').glob('batches/*/scores.json')) else 0)"` - passed

## User Setup Required

None - no external service configuration required for mocked/unit validation. Live batch scoring still depends on the LAB judge and nanoclaw runtime environment.

## Next Plan Handoff

Plan 04-04 can document the adapter contract and batch semantics now that the primary command supports single runs, LAB report preservation, task x seed loops, metadata-only aggregate summaries, and variance reporting. The guide should explicitly state that seed is recorded as metadata unless a future adapter implements deterministic seeding.

## Self-Check: PASSED

- Created files exist: `lab_harness_runner/aggregation.py`, `tests/test_aggregation.py`, `.planning/phases/04-completion-metrics-evaluation-and-scale-out/04-03-SUMMARY.md`
- Task commits exist: `7521f75`, `b36ae2b`
- Validation commands passed: targeted tests, full suite, CLI help smoke, and LAB batch pollution guard

---
*Phase: 04-completion-metrics-evaluation-and-scale-out*
*Completed: 2026-06-01*
