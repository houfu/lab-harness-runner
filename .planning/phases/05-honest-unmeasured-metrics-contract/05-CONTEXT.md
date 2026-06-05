# Phase 5: Honest Unmeasured Metrics Contract - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

## Phase Boundary

Make `RunResult` distinguish "adapter measured 0" from "adapter did not measure",
and have `write_metrics` and the aggregation layer propagate that distinction
honestly (null for unmeasured; skip nulls in mean / sum / variance; annotate
unmeasured rows in the batch summary). This is a contract change, not a
behavioral change for the adapter itself. End_state remains the only mandatory,
non-null field.

## Implementation Decisions

### Null-vs-zero on disk (CON-01, CON-02)

- **D-01:** `write_metrics` writes the underlying value unchanged when it is
  `None` / `int` / `list` rather than coercing `None` to `0` / `[]`. The
  previous "no null values in JSON" guarantee
  (`test_write_metrics_no_null_values`) is replaced by an explicit
  "unmeasured fields are written as `null`" guarantee, except for `end_state`
  and any caller-supplied diagnostic field.
- **D-02:** `end_state` is the only required, non-nullable field. Everything
  else (int fields + list fields) may be `None` (= unmeasured).
- **D-03:** Diagnostics passed via `extra_fields` keep the existing
  `_without_null_values` rule (a `None` diagnostic is still stripped, not
  written as `null`). The contract change applies to the LAB-compatible
  token / coverage fields only; the visible "unmeasured" annotation
  (CON-03) carries the unmeasured signal for diagnostics.

### Unmeasured annotation shape (CON-03)

- **D-04:** Each row in `summary.json` carries a top-level `metrics_provided`
  boolean — `true` when all LAB-compatible metric fields on the row are
  measured (i.e. non-null), `false` when any of them are null. The
  per-field nulls remain visible in the row payload itself.
- **D-05:** `summary.json` carries a top-level `unmeasured_counts` object
  keyed by metric field, with the count of rows where that field is `null`.
  A consumer that only wants the batch-level picture reads
  `unmeasured_counts`; a consumer that wants per-row unmeasured rows reads
  `metrics_provided` and the row's nulls.
- **D-06:** Per-row annotation is the boolean, not a per-field list of
  unmeasured field names. The boolean plus the per-row null values gives
  downstream consumers the same information without a third field on every
  row.

### List field nullability (CON-01)

- **D-07:** `documents_read_list` and `documents_skipped_list` on `RunResult`
  are nullable: their existing `field(default_factory=list)` default is
  changed to `None`. An adapter that measures zero reads still reports
  `documents_read_list=[]` (measured empty list); an adapter that did not
  measure reports `documents_read_list=None` (unmeasured). The on-disk
  representation of unmeasured is `null`; the on-disk representation of
  measured-empty is `[]`.
- **D-08:** A list field that is `None` is written as `null` on disk (not
  `[]`). A list field that is `[]` is written as `[]` on disk. The
  distinction matters because `metrics_provided: false` is set when the
  list is `None`, not when it is `[]`.

### Variance computation (CON-02)

- **D-09:** `build_summary` and `summarize_variance` skip `null` entries
  in mean / min / max / sum / stdev computations, exactly as they already
  skip non-numeric values via `_numeric_values` (no change in the numeric
  code path; the type filter naturally excludes `None`).
- **D-10:** The variance payload records the actual count of measured rows,
  not the row count, for each field. A field with `count: 2` of `10` rows
  means 8 of those rows had `null` for that field.
- **D-11:** List fields (`documents_read_list`, `documents_skipped_list`)
  appear in `summary.json` variance as a `lengths` block: a count of
  measured rows plus mean / min / max / stdev of `len(list)` over those
  rows. Null rows are excluded from the length statistics (the count is
  the number of rows where the field is a list, not the row count).
  The `documents_read` / `documents_skipped` count fields keep their
  existing numeric variance shape (the leverage for "how many documents
  were read"); the `_list` length statistics are additive.

### Aggregation schema compat (CON-03, LAB-01)

- **D-12:** The existing `REQUIRED_ROW_FIELDS` in `aggregation.py` keeps
  the same keys, but the row-normalization default changes from `""` to
  `None` for the LAB metric fields (`input_tokens`, `output_tokens`,
  `documents_read`, `total_vdr_files`, `wall_clock_seconds`). Strings
  stay as `""` for the ID/path fields. The downstream `_numeric_values`
  filter already handles the `None` correctly — the change is just to
  stop coercing unmeasured-but-present fields to empty strings.
- **D-13:** `metrics.json` continues to be LAB-compatible. The change is
  that the LAB-compatible fields are now nullable on disk; the field
  NAMES and positions are unchanged. `LAB-01` (output compatible with
  LAB's existing batch-summary tool) is preserved — LAB's consumer
  either ignores `null` or treats it the same as a missing key.
- **D-14:** `_batch_row` in `scripts/run_benchmark.py` continues to read
  the metric fields via `metrics.get(...)` — the JSON-loaded value of
  a `null` field is `None`, which flows through to the batch row
  unchanged. The `or ""` default in
  `run_summary.get("input_tokens", metrics.get("input_tokens", ""))`
  is removed for the LAB metric fields (per D-12).

### Docs

- **D-15:** `docs/adapter-guide.md` gets a one-paragraph addendum to the
  "Metrics And Status Semantics" section noting that token / coverage
  fields are now nullable in `metrics.json` and that a `null` means "not
  measured", not "zero". The "Results are whole agent-system outcomes"
  sentence in the doc is unchanged (Phase 5 exit criterion — additive,
  not a rewrite of `end_state` semantics).
- **D-16:** `docs/adapter-guide.md` "RunResult" field list is updated to
  reflect that the list fields are now `list[str] | None` and that
  `None` is a valid unmeasured value.

### Tests

- **D-17:** `tests/test_metrics.py` adds: a test that `None` for any
  token / coverage / list field writes `null` on disk (not `0` / `[]`);
  a test that explicit `0` is preserved (replacing the existing
  `test_write_metrics_preserves_explicit_zero_values` semantics for the
  same assertion); a test that `documents_read_list=None` writes `null`
  not `[]`. The existing `test_write_metrics_no_null_values` is
  replaced by `test_write_metrics_unmeasured_fields_written_as_null`.
- **D-18:** `tests/test_aggregation.py` adds: a test that mixed
  measured + unmeasured rows report per-field variance counts that
  exclude unmeasured rows; a test that `unmeasured_counts` is present
  in the summary; a test that list-field length statistics skip
  null rows. A test that the per-row `metrics_provided` boolean
  reflects whether any LAB metric field on that row is `None`.

### Claude's Discretion

- The exact wording of the docs addendum (D-15, D-16) is Claude's
  discretion as long as the contract change is reflected.
- The test names in D-17 / D-18 are illustrative; the planner /
  executor may use any names that satisfy the assertions.
- The migration of any in-tree `metrics.json` fixtures (e.g.
  `tests/conftest.py`'s `sample_run_result` fixture) from
  `documents_read_list=[]` to `documents_read_list=None` to exercise
  the unmeasured path is Claude's discretion; the existing fixture
  is already a "measured" example and may stay that way if a new
  fixture covers the unmeasured case.

### Folded Todos

No todos were folded. Cross-reference step reported no pending todos
matched to phase 5.

## Canonical References

Downstream agents MUST read these before planning or implementing.

### Project-level
- `.planning/PROJECT.md` — v1.1 milestone goal, the "runner stays thin"
  lock, and the "no aggregation tool in the runner" lock (both bind
  Phase 5's deliverable boundaries).
- `.planning/REQUIREMENTS.md` v1.1 — CON-01, CON-02, CON-03 are the
  binding requirements for this phase.
- `.planning/ROADMAP.md` v1.1 — Phase 5 Goal / Context / Deliverables
  / Exit Criteria; the verification posture ("Phase 5 closes on unit
  tests against the contract change. No live nanoclaw run is required")
  sets the no-live-run expectation for the verifier.

### Source code (the contract surface)
- `lab_harness_runner/adapter.py` — `RunResult` dataclass; the
  `int | None` typing on token / coverage fields and the
  `list[str] = field(default_factory=list)` typing on the list
  fields are the starting point. D-07 changes the list-field default
  to `None`.
- `lab_harness_runner/metrics.py` — `write_metrics`; the explicit
  `None → 0` / `None → []` coercions are the lines to replace
  (per D-01, D-07, D-08). `_without_null_values` stays as-is and
  continues to be used for diagnostics (per D-03).
- `lab_harness_runner/aggregation.py` — `_numeric_values`,
  `summarize_variance`, `build_summary`, `write_batch_summary`,
  `VARIANCE_FIELDS`, `REQUIRED_ROW_FIELDS`. The `_numeric_values`
  filter already skips `None` — that is the natural leverage
  point. `REQUIRED_ROW_FIELDS`'s `""` default for the metric
  fields needs the change in D-12.
- `scripts/run_benchmark.py` — `_batch_row` reads
  `metrics.get("input_tokens", "")`; the `or ""` default needs
  removal per D-14 so the JSON-loaded `None` flows through.

### Tests (the test surface to update)
- `tests/test_metrics.py` — replace `test_write_metrics_no_null_values`
  with the new `null`-passing assertion (D-17).
- `tests/test_aggregation.py` — add mixed measured + unmeasured
  coverage (D-18).

### Docs
- `docs/adapter-guide.md` — "RunResult" field list (D-16) and
  "Metrics And Status Semantics" (D-15). The
  "Results are whole agent-system outcomes" sentence at the bottom
  of the file is the invariant Phase 5 must NOT touch.

## Existing Code Insights

### Reusable Assets
- `_numeric_values` in `aggregation.py` — already filters to
  `int | float` and skips `bool`. `None` is naturally excluded by
  the type check, so the variance code path needs no change for
  the `null` semantics — only the upstream "did we coerce to 0"
  question needs to be answered.
- `_without_null_values` in `metrics.py` — kept and still applied
  to `extra_fields` (D-03). The helper is not used for the
  LAB-compatible fields after the contract change.

### Established Patterns
- "Two-tier diagnostics" — `RunResult.end_state` is the raw
  protocol signal; `benchmark_status` is the deliverable-derived
  reporting state. The new `metrics_provided` boolean extends
  the same pattern: a "raw" unmeasured signal at the field level
  (`None`) plus a "summary" unmeasured signal at the row level
  (`metrics_provided: false`).
- "Add, don't rewrite" — Phase 5's deliverables are explicit
  about the contract being additive: the existing tests for
  explicit zero / measured fields are kept; only the
  `None → 0` coercion and the unmeasured annotation are new.

### Integration Points
- `write_metrics` is the single sink for the on-disk `metrics.json`
  payload — the contract change happens there.
- `write_batch_summary` → `build_summary` is the single sink for
  the on-disk `summary.json` payload — the annotation and the
  per-field unmeasured counts are added in `build_summary`.
- `scripts/run_benchmark.py::_batch_row` is the bridge that
  reads `metrics.json` into batch rows; the row's `None` values
  must propagate to `build_summary` unchanged (D-14).

## Specific Ideas

- The per-row boolean plus per-field nulls is the same shape as
  the user's "row visibly annotated in summary.json" requirement
  in CON-03 — no third field needed.
- The `unmeasured_counts` top-level field mirrors the variance
  `count` semantics: it answers "how many rows had this field as
  `null`?" without making the consumer scan the rows array.
- The list-field `lengths` block keeps variance comparable across
  runs (a useful pre-extraction signal in v1.0 Phase 4 batch
  results where `documents_read` was a count) without conflating
  "did not measure" with "measured zero documents".

## Deferred Ideas

None — discussion stayed within phase scope. The user did mention
"per-task token / duration histogram in sweep driver" earlier
(per PROJECT.md deferred section), which is correctly parked
in the v1.0 deferred list and not part of Phase 5.

---

*Phase: 5-Honest Unmeasured Metrics Contract*
*Context gathered: 2026-06-05*
