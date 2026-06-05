---
phase: 05-honest-unmeasured-metrics-contract
plan: 03
subsystem: testing
tags: [metrics, contract, aggregation, null-vs-zero, metrics_provided, unmeasured_counts, docs, doc-test, con-01, con-02, con-03]

# Dependency graph
requires:
  - phase: 05-honest-unmeasured-metrics-contract
    plan: 01
    provides: RunResult list fields are nullable; write_metrics writes null for unmeasured fields
  - phase: 05-honest-unmeasured-metrics-contract
    plan: 02
    provides: build_summary annotates rows with metrics_provided and emits top-level unmeasured_counts; list-field lengths block
provides:
  - "tests/test_aggregation.py updated to assert metrics_provided annotation on the rows in payload; existing rows==rows equality replaced with annotated-row copy"
  - "Four new aggregation tests covering mixed measured+unmeasured rows, unmeasured_counts zero case, list-field lengths skipping null rows, and per-row metrics_provided boolean semantics"
  - "docs/adapter-guide.md RunResult field list shows input_tokens / output_tokens / documents_read / total_vdr_files / documents_skipped / documents_read_list / documents_skipped_list as nullable with the explicit 'None means unmeasured' wording"
  - "docs/adapter-guide.md 'Metrics And Status Semantics' addendum explains the null-vs-zero distinction for the eight LAB metric fields and points downstream consumers to the unmeasured-row count"
  - "tests/test_docs.py::test_adapter_guide_documents_null_vs_zero_distinction regression doc test guards the new wording so a future edit cannot quietly drop the contract"
affects: [05-VERIFICATION]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-row `metrics_provided` annotation is verified in tests by comparing payload['rows'] to a dict-copied expected row with `metrics_provided` set explicitly; the helper pattern keeps the assertion tight without depending on aggregation internals"
    - "Doc tests use a 'is the new wording present' assertion shape so a future doc edit cannot remove the contract surface without breaking the test"

key-files:
  created: []
  modified:
    - tests/test_aggregation.py
    - tests/test_docs.py
    - docs/adapter-guide.md

key-decisions:
  - "Used a `_merge(base, overrides)` helper in test_aggregation.py to overlay overrides onto a base row dict; the helper uses dict.update so callers may set keys that already exist in the base (e.g. input_tokens=None) without the 'multiple values for keyword argument' error that dict(base, **kwargs) raises"
  - "The plan's 'all LAB metric fields are non-null' assertion for the existing rows==rows test required extending the fixture rows to set documents_skipped / documents_read_list / documents_skipped_list — these are the three LAB_METRIC_FIELDS that were not in the pre-Phase-5 REQUIRED_ROW_FIELDS row schema"
  - "The new doc test asserts the explanatory phrase 'list[str] | None`; `None` means unmeasured' as the strong contract signal rather than trying to forbid the old 'optional document lists' phrase (the substring still legitimately appears in the new sentence)"

patterns-established:
  - "Pattern: when a row fixture needs to assert a 'measured' shape for the new contract, set every LAB metric field (8 fields) explicitly; absence of a field defaults to None via build_summary, which makes metrics_provided False"
  - "Pattern: when a doc test needs to assert a wording change, anchor on a unique explanatory phrase (e.g. 'list[str] | None`; `None` means unmeasured') rather than on the absence of the old wording — the old wording may still legitimately appear in the new sentence"

requirements-completed: [CON-01, CON-02, CON-03]

# Metrics
duration: 16min
completed: 2026-06-05
---

# Phase 5 Plan 3: Test Updates + Docs Addendum

**Aggregation tests assert the new `metrics_provided` / `unmeasured_counts` / list-`lengths` shape; the adapter guide documents the null-vs-zero contract and a regression doc test guards the new wording.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-06-05T06:41:28Z
- **Completed:** 2026-06-05T06:57:30Z
- **Tasks:** 2 of 2 completed
- **Files modified:** 3 (`tests/test_aggregation.py`, `tests/test_docs.py`, `docs/adapter-guide.md`)

## Accomplishments

- `tests/test_aggregation.py`: the two pre-Plan-02 tests that asserted `summary["rows"] == rows` / `payload["rows"] == [row]` are updated to compare against an annotated-row copy with `metrics_provided` set, and the first test gains assertions on the new top-level `unmeasured_counts` field and on the expanded variance key set (the list-field `lengths` blocks added in Plan 02). The two pre-existing fixture rows are extended to set every LAB metric field so `metrics_provided` is `True` on both rows.
- Four new aggregation tests cover the D-18 contract:
  - `test_build_summary_mixed_measured_and_unmeasured_rows` — variance counts exclude unmeasured rows; `unmeasured_counts` reflects the per-field null tally; per-row `metrics_provided` is `True` / `False` accordingly.
  - `test_build_summary_unmeasured_counts_zero_for_all_measured_rows` — an all-measured batch has an `unmeasured_counts` dict with eight keys and every value `0`, and `metrics_provided` is `True` on every row.
  - `test_build_summary_list_field_lengths_skip_null_rows` — list-field `lengths` variance is computed over measured rows only; null rows are excluded.
  - `test_build_summary_metrics_provided_false_when_any_field_null` — a single null LAB metric field makes `metrics_provided` `False`; all non-null makes it `True`.
- `docs/adapter-guide.md`: the RunResult field list now shows `input_tokens` / `output_tokens` / `documents_read` / `total_vdr_files` / `documents_skipped` as nullable (`None` means unmeasured, `0` means measured zero) and `documents_read_list` / `documents_skipped_list` as `list[str] | None` (`None` means unmeasured, `[]` means measured zero). A new paragraph appended to "Metrics And Status Semantics" explains the null-vs-zero distinction and points downstream consumers at the unmeasured-row count.
- The "Results are whole agent-system outcomes" sentence at the end of "Scoring And Report Preservation" is unchanged (Phase 5 exit criterion — additive, not a rewrite of `end_state` semantics).
- `tests/test_docs.py::test_adapter_guide_documents_null_vs_zero_distinction` is a regression guard: it asserts the new wording (`null`, `unmeasured`, `measured zero`, `list[str] | None`, the nullability clause) is present in `docs/adapter-guide.md` so a future edit cannot quietly drop the contract.
- Full test suite is green: 115 tests pass.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update existing test_aggregation.py assertions and add new tests for the null-vs-zero contract** - `db8d5e9` (test)
2. **Task 2: Update docs/adapter-guide.md and add a doc test that the null-vs-zero wording is present** - `b52e09c` (docs)

## Files Created/Modified

- `tests/test_aggregation.py` - Two existing tests updated to assert the new `metrics_provided` annotation and the `unmeasured_counts` field; four new tests for mixed measured/unmeasured, unmeasured_counts zero case, list-field lengths, and per-row `metrics_provided` boolean semantics. A `_merge(base, overrides)` helper overlays the base row dict with overrides; an `_all_measured_metric_kwargs()` helper builds the eight LAB metric fields in a measured shape so fixtures can be expressed compactly.
- `tests/test_docs.py` - New `test_adapter_guide_documents_null_vs_zero_distinction` doc test that asserts the new contract wording is present in `docs/adapter-guide.md` (null, unmeasured, measured zero, list[str] | None, the nullability clause).
- `docs/adapter-guide.md` - RunResult field list updated to show nullability for all eight LAB metric fields with the "None means unmeasured, 0 means measured zero" / "None means unmeasured, [] means measured zero" wording. New paragraph appended to "Metrics And Status Semantics" explaining the null-vs-zero contract for downstream consumers and `build_summary`. The "Results are whole agent-system outcomes" invariant is preserved verbatim.

## Decisions Made

- Used a `_merge(base, overrides)` helper in `test_aggregation.py` rather than `dict(base, **overrides)` because Python raises on key collisions and the new tests need to set the same key (`input_tokens=None` for the null case) that already exists in the base helper. The helper uses `dict.update` semantics so the same key may be overridden.
- Extended the pre-existing fixture rows in `test_build_summary_includes_rows_and_variance_fields` and `test_write_batch_summary_is_metadata_only_under_results_batches` to set every LAB metric field. The plan's task description for the rows==rows fix said "metrics_provided is True because all LAB metric fields are non-null", and `build_summary` computes `metrics_provided` over the eight `LAB_METRIC_FIELDS` (not the five `REQUIRED_ROW_FIELDS` that the fixtures were based on). Adding `documents_skipped` / `documents_read_list` / `documents_skipped_list` keeps the assertion shape the plan asked for.
- Anchored the new doc test on the explanatory phrase `list[str] | None`; \`None\` means unmeasured` (a unique contract signal) rather than forbidding the old "optional document lists" phrase (the substring legitimately appears in the new sentence). This makes the test robust to minor wording rewordings while still failing if the nullability clause is removed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 5 — Inconsistent with new contract] Extended pre-existing fixture rows to set every LAB metric field**
- **Found during:** Task 1 (running the updated tests after the metrics_provided annotation was applied)
- **Issue:** The plan's "rows==rows" fix said "metrics_provided is True because all LAB metric fields are non-null". `build_summary` computes `metrics_provided` over the eight `LAB_METRIC_FIELDS`, but the pre-Phase-5 fixture rows only set the five LAB metric fields that were in `REQUIRED_ROW_FIELDS` (`input_tokens`, `output_tokens`, `documents_read`, `total_vdr_files`, `wall_clock_seconds`). After the metric_provided annotation, those rows would have `metrics_provided: False` because `documents_skipped` / `documents_read_list` / `documents_skipped_list` are not set (they default to `None`).
- **Fix:** Extended the two pre-existing test fixtures to set `documents_skipped=0`, `documents_read_list=[...]`, `documents_skipped_list=[]` so every LAB metric field is non-null and the `metrics_provided` boolean is `True` as the plan intended. The new test fixtures (the four D-18 tests) also use the `_all_measured_metric_kwargs()` helper that sets all eight fields for the same reason.
- **Files modified:** `tests/test_aggregation.py`
- **Verification:** `uv run python -m pytest tests/test_aggregation.py -q` is green (9 passed).
- **Committed in:** `db8d5e9` (Task 1 commit)

**2. [Rule 1 — Blocker] Used a `_merge` helper to avoid `dict(base, **overrides)` key-collision error**
- **Found during:** Task 1 (writing the four new tests)
- **Issue:** The plan suggested building fixture rows with `dict(base, **overrides)` for readability. Python raises `TypeError: dict() got multiple values for keyword argument 'X'` when the same key is in `base` and in `overrides` (e.g. setting `input_tokens=None` for the null test). The new tests need exactly this pattern.
- **Fix:** Added a `_merge(base, overrides)` helper that uses `dict.update` semantics so callers can override keys that already exist in `base`. The plan's "KEEP unchanged" / "ADD a new test" structure was preserved.
- **Files modified:** `tests/test_aggregation.py`
- **Verification:** The four new tests pass with the helper.
- **Committed in:** `db8d5e9` (Task 1 commit, same deviation item is two parts of the same "make new tests work" work item)

**3. [Rule 5 — Inconsistent with line-wrapped doc text] Anchored doc test on explanatory phrase, not on the old wording**
- **Found during:** Task 2 (writing the new doc test)
- **Issue:** The plan suggested asserting "the phrase `optional document lists` is NOT followed by just a period and a newline; assert the new phrase `optional document lists of type` IS present". The doc line-wraps the new sentence: "optional document lists\n  of type `list[str] | None`". A literal substring check for "optional document lists of type" does not match because of the line break.
- **Fix:** The doc test asserts the explanatory phrase "list[str] | None`; `None` means unmeasured" (a unique contract signal that is on a single line in the doc) plus the two halves of the new wording ("of type" and "list[str] | None") so the test is robust to minor line-wrap reformatting.
- **Files modified:** `tests/test_docs.py`
- **Verification:** `uv run python -m pytest tests/test_docs.py -q` is green (5 passed).
- **Committed in:** `b52e09c` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 inconsistent-with-new-contract / blocker)
**Impact on plan:** All three auto-fixes are mechanical — the plan's intent is preserved and no scope was added. The full test suite is green (115 passed) and the "Results are whole agent-system outcomes" invariant is preserved.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 5 deliverables are complete: `RunResult` distinguishes measured-empty from unmeasured (Plan 01), `write_metrics` writes `null` for unmeasured fields (Plan 01), `build_summary` annotates rows with `metrics_provided` and emits top-level `unmeasured_counts` (Plan 02), `_batch_row` lets a JSON-loaded `null` flow through (Plan 02), the aggregation tests assert the new shape and the four D-18 scenarios are covered (Plan 03), and the docs reflect the contract change with a regression doc test (Plan 03).
- The full test suite is green (115 tests pass) — the verification posture called for in `05-VALIDATION.md` ("Phase 5 closes on unit tests against the contract change. No live nanoclaw run is required") is met.
- No blockers. Phase 5 is ready for the wave-2 verification step.

---
*Phase: 05-honest-unmeasured-metrics-contract*
*Completed: 2026-06-05*
