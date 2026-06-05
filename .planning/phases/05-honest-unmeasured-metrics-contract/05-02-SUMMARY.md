---
phase: 05-honest-unmeasured-metrics-contract
plan: 02
subsystem: aggregation
tags: [batch-summary, null-vs-zero, metrics_provided, unmeasured_counts, list-variance, run_benchmark]

# Dependency graph
requires:
  - phase: 05-honest-unmeasured-metrics-contract
    plan: 01
    provides: write_metrics writes null for unmeasured fields; RunResult list fields are nullable
provides:
  - LAB_METRIC_FIELDS / LAB_LIST_VARIANCE_FIELDS constants in aggregation.py
  - build_summary annotates rows with metrics_provided and emits top-level unmeasured_counts
  - List fields get a lengths sub-block in variance computed over measured rows only
  - write_batch_summary normalises absent LAB metric fields to None (not "")
  - scripts/run_benchmark.py::_batch_row lets a JSON-loaded null flow through for the five LAB metric fields
affects: [05-03-PLAN (test updates + docs), 05-VERIFICATION]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-tier unmeasured signal: field-level None + row-level metrics_provided boolean"
    - "Per-field default lookup in row normalisation: None for LAB metric fields, '' for ID / path fields"
    - "List-field variance as a separate lengths sub-block, kept off the numeric VARIANCE_FIELDS path"

key-files:
  created: []
  modified:
    - lab_harness_runner/aggregation.py
    - scripts/run_benchmark.py

key-decisions:
  - "LAB_METRIC_FIELDS holds eight LAB-compatible fields (token / coverage / list); single source of truth for metrics_provided and unmeasured_counts"
  - "LAB_LIST_VARIANCE_FIELDS is kept separate from VARIANCE_FIELDS so _numeric_values (which filters on isinstance(int|float)) is not asked to compute stats over a list of strings"
  - "write_batch_summary uses a per-field _default_for helper (None for LAB metric fields, '' for ID / path fields) instead of a single '' default"
  - "_batch_row drops only the '' second-arg to metrics.get; the run_summary.get fallback chain is preserved so per-run overrides still win"

patterns-established:
  - "Pattern: when a field is nullable, the row-normalisation default must be field-aware, not a uniform ''"
  - "Pattern: nullable list fields get a separate variance sub-block (lengths) so the numeric and list-statistic paths do not share an isinstance check"

requirements-completed: [CON-02, CON-03]

# Metrics
duration: 6min
completed: 2026-06-05
---

# Phase 5 Plan 2: Aggregation Path Annotations

**Per-row metrics_provided boolean + top-level unmeasured_counts + list-variance lengths block; row normalisation and _batch_row pass null through unchanged.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-05T06:25:00Z
- **Completed:** 2026-06-05T06:31:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `build_summary` annotates every row with a `metrics_provided` boolean (true iff all LAB metric fields on the row are non-null) and emits a top-level `unmeasured_counts` dict keyed by LAB metric field.
- `documents_read_list` and `documents_skipped_list` get a `lengths` sub-block in `variance`, computed over rows where the field is a list (null rows excluded); the count reflects measured rows only.
- `write_batch_summary` normalises absent LAB metric fields to `None` (not `""`) and ID / path fields to `""`, using a per-field `_default_for` helper; `_numeric_values` already filters `None` so the numeric variance path is untouched.
- `scripts/run_benchmark.py::_batch_row` lets a JSON-loaded `null` from `metrics.json` flow through to the batch row for the five LAB metric fields (`wall_clock_seconds`, `input_tokens`, `output_tokens`, `documents_read`, `total_vdr_files`); ID / path / string fields are unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add LAB_METRIC_FIELDS, metrics_provided per row, unmeasured_counts top-level, list-variance lengths block, and per-field None default in write_batch_summary** - `d76ed68` (feat)
2. **Task 2: Remove the `""` second-arg default in scripts/run_benchmark.py::_batch_row for LAB metric fields** - `8380532` (feat)

## Files Created/Modified

- `lab_harness_runner/aggregation.py` - Added `LAB_METRIC_FIELDS` and `LAB_LIST_VARIANCE_FIELDS` constants; `build_summary` now annotates rows with `metrics_provided`, emits top-level `unmeasured_counts`, and adds a `lengths` sub-block for list fields; `write_batch_summary` uses a per-field `_default_for` helper (None for LAB metric fields, "" for ID / path fields).
- `scripts/run_benchmark.py` - `_batch_row` now reads `metrics.get(key)` (single-arg) for the five LAB metric fields, so a JSON-loaded `null` flows through to the batch row unchanged.

## Decisions Made

- Kept `LAB_LIST_VARIANCE_FIELDS` as a separate tuple from `VARIANCE_FIELDS` so `_numeric_values` (which filters on `isinstance(value, int | float)`) is never asked to compute statistics over a list of strings. Verified empirically in `05-RESEARCH.md` Pattern 2.
- Used a `_default_for(field)` helper inside `write_batch_summary` rather than splitting `REQUIRED_ROW_FIELDS` into two groups; the helper reads cleaner in place and keeps `REQUIRED_ROW_FIELDS` as the single source of truth for the row schema.
- Dropped only the `""` second-arg to `metrics.get` in `_batch_row` (per D-14 / Pitfall 2), leaving the outer `run_summary.get(key, metrics.get(key))` chain intact. The `run_summary.get` fallback still wins when the per-run summary has the key explicitly, so per-run overrides are preserved.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `tests/test_aggregation.py::test_build_summary_includes_rows_and_variance_fields` and `tests/test_aggregation.py::test_write_batch_summary_is_metadata_only_under_results_batches` fail after Task 1 because they assert the pre-Phase-5 shape (`rows` equals the input list, no `metrics_provided` / `unmeasured_counts` fields). This is expected: the plan's success criteria explicitly note "The full test suite is green after Plan 03 updates the test assertions to match the new shape." Plan 03 owns the test updates. The acceptance-criteria inline checks for Task 1 (`build_summary` returns `unmeasured_counts["input_tokens"] == 1` and `rows[0]["metrics_provided"] is False`) all pass.
- `tests/test_run_benchmark.py` (17 tests) is fully green after Task 2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 Plan 3 (test updates + docs addendum) can now run: it owns updating `tests/test_aggregation.py` to assert the new `metrics_provided` / `unmeasured_counts` / `lengths` shape, adding the mixed-measured-and-unmeasured coverage per D-18, and updating `docs/adapter-guide.md` per D-15 / D-16.
- The `metrics_provided` boolean plus per-row nulls plus top-level `unmeasured_counts` shape matches the D-04 / D-05 / D-06 Code Example in `05-RESEARCH.md` and the locked decisions in `05-CONTEXT.md`.
- No blockers; all plan success criteria met at the code level. Test-suite green is the Plan 03 deliverable.

---
*Phase: 05-honest-unmeasured-metrics-contract*
*Completed: 2026-06-05*
