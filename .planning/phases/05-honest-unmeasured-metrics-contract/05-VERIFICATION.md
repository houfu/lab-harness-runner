---
phase: 05-honest-unmeasured-metrics-contract
verified_at: 2026-06-05
verdict: PASS
---

# Phase 5 Verification: Honest Unmeasured Metrics Contract

## Verdict

**PASS.** All three Phase 5 requirements (CON-01, CON-02, CON-03) are
satisfied. The full test suite is green (115 passed) and the new contract is
regression-protected by both unit tests and a doc test.

## Goal Recap

Make `RunResult` distinguish "adapter measured 0" from "adapter did not
measure", and have `write_metrics` and the aggregation layer propagate that
distinction honestly (null for unmeasured; skip nulls in mean / sum /
variance; annotate unmeasured rows in the batch summary).

## Requirement Cross-Reference

| Req ID  | PLAN frontmatter appearances               | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                              |
| ------- | ------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| CON-01  | 05-01, 05-03 (mentioned in 05-02 + 05-03)  | **PASS**   | `RunResult.documents_read_list` and `documents_read_list` are now `list[str] \| None = None` (adapter.py L39-40). `write_metrics` reads the eight LAB-compatible fields directly off `result` with no `None` coercion (metrics.py L35-45). `tests/test_metrics.py` has `test_write_metrics_unmeasured_fields_written_as_null`, `test_write_metrics_unmeasured_list_field_written_as_null`, `test_write_metrics_explicit_zero_preserved` covering the contract. |
| CON-02  | 05-01, 05-02, 05-03                        | **PASS**   | On-disk half: `write_metrics` writes `null` for unmeasured fields, `0` for measured zero, `[]` for measured empty (verified by 6 unit tests in `test_metrics.py` and the runtime check below). Aggregation half: `build_summary`'s `summarize_variance` path filters `None` via `isinstance(int \| float)` (aggregation.py L68-75). The 4 new aggregation tests in `test_aggregation.py` cover the mixed measured/unmeasured + zero-stdev case (L258-398). |
| CON-03  | 05-02, 05-03                               | **PASS**   | `build_summary` annotates every row with a `metrics_provided` boolean (true iff all LAB metric fields are non-null) and emits a top-level `unmeasured_counts` dict keyed by all eight LAB metric fields (aggregation.py L100-128). `write_batch_summary` row-normalises absent LAB metric fields to `None` (L143-152) so the boolean and counts work for callers that don't pre-populate. `test_aggregation.py` covers the four D-18 scenarios. |

All three requirement IDs declared in PLAN frontmatter (CON-01 in 05-01 and
05-03; CON-02 in 05-01, 05-02, 05-03; CON-03 in 05-02 and 05-03) are
accounted for. **No requirement IDs in the frontmatter are missing from
REQUIREMENTS.md, and no REQUIREMENTS.md IDs declared in Phase 5 (CON-01/02/03)
are unaccounted for.**

## Must-Haves Audit

### Plan 05-01 (CON-01, CON-02 source code + test_metrics.py)

| Truth / Artifact                                                                                          | Status | Evidence                                                                                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RunResult` constructed without token / coverage / list fields reports those fields as `None`            | PASS   | `adapter.py` L34-40: `input_tokens: int \| None = None` etc.; runtime: `RunResult(run_id='x', end_state='clean', wall_clock_seconds=1.0).input_tokens is None` → `True`.                                                                                                                                |
| `write_metrics` serialises a `None` LAB-compatible field as JSON `null` on disk                          | PASS   | `metrics.py` L35-45 builds dict via direct attribute reads; `json.dumps` serialises `None` as `null` natively. Verified by `test_write_metrics_unmeasured_fields_written_as_null` + on-disk text assertion `'"input_tokens": null' in raw_text`.                                                     |
| `write_metrics` serialises an explicit `0` token field as JSON `0` (preserved)                            | PASS   | `test_write_metrics_preserves_explicit_zero_values` + `test_write_metrics_explicit_zero_preserved` + runtime check.                                                                                                                                                                                  |
| `write_metrics` serialises a list field that is `None` as `null` and one that is `[]` as `[]`              | PASS   | `test_write_metrics_unmeasured_list_field_written_as_null` + `test_write_metrics_empty_list_fields`.                                                                                                                                                                                                |
| Diagnostics passed via `extra_fields` still strip `None`                                                  | PASS   | `test_write_metrics_writes_diagnostic_fields_without_null_values` narrowed to scope; `_without_null_values` recursion is preserved in `metrics.py` L9-20, 46-47.                                                                                                                                     |
| `adapter.py` contains `documents_read_list: list[str] \| None = None`                                    | PASS   | L39.                                                                                                                                                                                                                                                                                                |
| `adapter.py` contains no `default_factory=list`                                                            | PASS   | `grep` returns no matches.                                                                                                                                                                                                                                                                          |
| `metrics.py` has no `if result.* is not None else` coercion                                               | PASS   | `grep` returns no matches.                                                                                                                                                                                                                                                                          |
| `metrics.py` reads the eight LAB fields directly off `result`                                              | PASS   | L35-45.                                                                                                                                                                                                                                                                                             |
| `tests/test_metrics.py` has `test_write_metrics_unmeasured_fields_written_as_null`                        | PASS   | Present.                                                                                                                                                                                                                                                                                            |
| Old `test_write_metrics_no_null_values` and `test_write_metrics_none_int_fields_default_to_zero` removed  | PASS   | `grep` returns no matches.                                                                                                                                                                                                                                                                          |
| `tests/test_metrics.py` is green under the new contract                                                    | PASS   | `uv run python -m pytest tests/test_metrics.py -q` → 11 passed.                                                                                                                                                                                                                                     |

### Plan 05-02 (CON-02 aggregation, CON-03 annotation)

| Truth / Artifact                                                                                                          | Status | Evidence                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `build_summary` annotates every row with a `metrics_provided` boolean                                                       | PASS   | `aggregation.py` L98-110; verified by `test_build_summary_metrics_provided_false_when_any_field_null` and 3 other new tests.                                                                                                                            |
| `build_summary` emits a top-level `unmeasured_counts` dict keyed by LAB metric field                                        | PASS   | L100, L125; verified by `test_build_summary_mixed_measured_and_unmeasured_rows` (5 assertions) and `test_build_summary_unmeasured_counts_zero_for_all_measured_rows` (8 keys asserted).                                                                  |
| `build_summary` emits a list-variance `lengths` block under `variance['documents_read_list']['lengths']` etc.             | PASS   | L115-121; verified by `test_build_summary_list_field_lengths_skip_null_rows` (6 length assertions).                                                                                                                                                     |
| `build_summary`'s numeric variance path skips null rows                                                                   | PASS   | `_numeric_values` filters `None` via `isinstance(int \| float)` (L68-75); verified by `test_build_summary_mixed_measured_and_unmeasured_rows::summary["variance"]["input_tokens"]["count"] == 1`.                                                       |
| `write_batch_summary` normalises absent LAB metric fields to `None`                                                       | PASS   | L143-152 `_default_for` helper; L154 `build_summary(normalized_rows)`.                                                                                                                                                                                  |
| `_batch_row` in `scripts/run_benchmark.py` lets a JSON-loaded `null` flow through for the five LAB metric fields           | PASS   | L247-261: each of the five `metrics.get("X")` calls uses single-arg form (`grep` confirms 5 matches, no `metrics.get("X", "")` matches).                                                                                                                |
| `lab_harness_runner/aggregation.py` contains `LAB_METRIC_FIELDS = (`                                                        | PASS   | L44.                                                                                                                                                                                                                                                   |
| `lab_harness_runner/aggregation.py` contains `LAB_LIST_VARIANCE_FIELDS = (`                                                | PASS   | L55.                                                                                                                                                                                                                                                   |
| `lab_harness_runner/aggregation.py` contains `"lengths": summarize_variance`                                              | PASS   | L121.                                                                                                                                                                                                                                                   |
| `scripts/run_benchmark.py` has `metrics.get("input_tokens")` (single-arg) for the five LAB metric fields                  | PASS   | L248, 251, 254, 257, 260.                                                                                                                                                                                                                              |

### Plan 05-03 (test updates, doc addendum, doc test)

| Truth / Artifact                                                                                                                                    | Status | Evidence                                                                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_aggregation.py` covers mixed measured + unmeasured rows                                                                                        | PASS   | `test_build_summary_mixed_measured_and_unmeasured_rows` (L258-305) asserts all the D-18 invariants (unmeasured_counts per field, variance count == 1, metrics_provided per row).                                                                     |
| `test_aggregation.py` covers `unmeasured_counts` zero case                                                                                          | PASS   | `test_build_summary_unmeasured_counts_zero_for_all_measured_rows` (L308-330) asserts 8 keys all == 0 and both rows `metrics_provided is True`.                                                                                                       |
| `test_aggregation.py` covers list-field `lengths` block skipping null rows                                                                           | PASS   | `test_build_summary_list_field_lengths_skip_null_rows` (L333-375) asserts count=1, mean=3.0, etc.                                                                                                                                                   |
| `test_aggregation.py` covers per-row `metrics_provided` boolean semantics                                                                            | PASS   | `test_build_summary_metrics_provided_false_when_any_field_null` (L378-398) and the per-row assertions in the other three new tests.                                                                                                                   |
| `test_aggregation.py` existing `rows == rows` assertion updated to compare against annotated rows                                                  | PASS   | `_annotate_expected_rows` helper (L37-48) used in `test_build_summary_includes_rows_and_variance_fields` (L115-116); `test_write_batch_summary_is_metadata_only_under_results_batches` updated at L198-200.                                          |
| `docs/adapter-guide.md` adds a one-paragraph addendum to 'Metrics And Status Semantics' noting null = unmeasured, not zero                          | PASS   | L132-141: a new paragraph added after the timeout-with-valid-deliverables paragraph, explains the null contract and points to `build_summary`'s unmeasured-row count.                                                                              |
| `docs/adapter-guide.md` updates the 'RunResult' field list to show `documents_read_list` / `documents_skipped_list` as `list[str] \| None`         | PASS   | L37-39: new wording `optional document lists of type list[str] \| None; None means unmeasured, [] means measured zero`.                                                                                                                              |
| `docs/adapter-guide.md` 'Results are whole agent-system outcomes' sentence UNCHANGED (Phase 5 exit criterion)                                       | PASS   | L165 still present (exactly one `grep` match).                                                                                                                                                                                                       |
| `tests/test_docs.py` has `test_adapter_guide_documents_null_vs_zero_distinction`                                                                    | PASS   | L73-103. Asserts `null`, `unmeasured`, `measured zero`, `list[str] \| None`, and the explanatory phrase `list[str] \| None`; \`None\` means unmeasured` are all present in the guide.                                                              |
| `tests/test_aggregation.py` contains the four new tests                                                                                            | PASS   | `grep` confirms one match each for all four test names.                                                                                                                                                                                              |

## Runtime Verification

Test suite: `uv run --quiet python -m pytest -q` → **115 passed in 1.19s**.

Module-level test suite: `uv run --quiet python -m pytest tests/test_metrics.py tests/test_aggregation.py tests/test_docs.py tests/test_run_benchmark.py -q` → **43 passed**.

Manual contract sanity check:

- `RunResult(run_id='x', end_state='clean', wall_clock_seconds=1.0)` (no metric
  fields) → `metrics.json` contains `"input_tokens": null` and
  `"documents_read_list": null` (not `0` / `[]`).
- Same with `input_tokens=0, documents_read_list=[]` → JSON contains
  `"input_tokens": 0` and `"documents_read_list": []` (preserved).
- `build_summary` on two rows (one measured, one all-None LAB fields) returns
  `unmeasured_counts['input_tokens'] == 1`,
  `variance['input_tokens']['count'] == 1`, and
  `rows[0]['metrics_provided'] is False` (the test row omits the new
  `documents_skipped` / `documents_read_list` / `documents_skipped_list`
  fields, so the boolean is correctly `False` for both rows under the new
  contract — this matches the D-04 / D-18 behaviour and is why the new tests
  use the `_all_measured_metric_kwargs()` helper).

## On-Disk Evidence

- `lab_harness_runner/adapter.py` L34-40: list fields nullable.
- `lab_harness_runner/metrics.py` L35-45: direct attribute reads, no
  coercion.
- `lab_harness_runner/aggregation.py` L44-55, L98-128, L143-152: new
  constants, annotation, list-variance block, per-field default.
- `scripts/run_benchmark.py` L247-261: `_batch_row` lets JSON nulls
  flow through.
- `docs/adapter-guide.md` L33-39 (RunResult field list), L132-141
  (null-vs-zero addendum), L165 (invariant sentence preserved).
- `tests/test_metrics.py` L58-96, L99-122, L143-163, L181-216: new
  contract tests.
- `tests/test_aggregation.py` L258-398: four new D-18 tests.
- `tests/test_docs.py` L73-103: regression doc test.

## Requirements Closure

The traceability table in `REQUIREMENTS.md` (L102-105) currently shows
`CON-01 / CON-02 / CON-03` as `pending`. After verification, all three
should be marked **Complete** by the milestone-tracking step that follows
phase verification.

## Conclusion

The phase goal is met. The contract is honest end-to-end: `RunResult` can
represent "did not measure" as `None`, `write_metrics` writes that as JSON
`null` on disk (distinct from a measured `0` / `[]`), `build_summary`
annotates the unmeasured rows visibly with `metrics_provided` and a
per-field `unmeasured_counts` tally, the numeric variance path skips nulls
naturally, and `docs/adapter-guide.md` documents the new contract with a
regression doc test that prevents a future edit from quietly dropping the
wording. The Phase 5 exit criterion that the "Results are whole agent-system
outcomes" sentence remains unchanged is met. No live nanoclaw run was
required, matching the `05-VALIDATION.md` posture for Phase 5.
