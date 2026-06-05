# Phase 5: Honest Unmeasured Metrics Contract - Research

**Researched:** 2026-06-05
**Domain:** Contract change — null vs. zero propagation through the metrics write path and the batch summary path
**Confidence:** HIGH (all 18 locked decisions validated against source; `_numeric_values` behavior empirically verified; all call sites enumerated)

## Summary

Phase 5 is a **contract change**, not a behavior change. The work is well-scoped and low-risk because the dataclass typing (`int | None`) and the numeric filter (`_numeric_values`) already do the right thing; the change is removing the explicit `None → 0` / `None → []` coercions in `write_metrics` and updating one row-normalization default in `aggregation.py`. The downstream `_numeric_values` filter is verified to skip `None` naturally (D-09 confirmed empirically — see "Validated D-09" below). The per-row `metrics_provided` boolean + top-level `unmeasured_counts` are additive annotation; they extend the existing two-tier pattern (raw protocol signal + deliverable-derived reporting state).

**Primary recommendation:** The phase is well-prepared for planning. There is **no additional code surface beyond the four files already named in CONTEXT.md** (with one micro-extension — see "Additional code surface"). The plan should be split into three task groups mirroring the three change boundaries: (1) `RunResult` + `write_metrics` (D-01, D-07, D-08); (2) `aggregation.py` + `_batch_row` (D-09–D-12, D-14); (3) `build_summary` annotation + tests + docs (D-04–D-06, D-15–D-18).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `write_metrics` writes the underlying value unchanged when it is `None` / `int` / `list` rather than coercing `None` to `0` / `[]`. The previous "no null values in JSON" guarantee (`test_write_metrics_no_null_values`) is replaced by an explicit "unmeasured fields are written as `null`" guarantee, except for `end_state` and any caller-supplied diagnostic field.
- **D-02:** `end_state` is the only required, non-nullable field. Everything else (int fields + list fields) may be `None` (= unmeasured).
- **D-03:** Diagnostics passed via `extra_fields` keep the existing `_without_null_values` rule (a `None` diagnostic is still stripped, not written as `null`). The contract change applies to the LAB-compatible token / coverage fields only; the visible "unmeasured" annotation (CON-03) carries the unmeasured signal for diagnostics.
- **D-04:** Each row in `summary.json` carries a top-level `metrics_provided` boolean — `true` when all LAB-compatible metric fields on the row are measured (i.e. non-null), `false` when any of them are null. The per-field nulls remain visible in the row payload itself.
- **D-05:** `summary.json` carries a top-level `unmeasured_counts` object keyed by metric field, with the count of rows where that field is `null`. A consumer that only wants the batch-level picture reads `unmeasured_counts`; a consumer that wants per-row unmeasured rows reads `metrics_provided` and the row's nulls.
- **D-06:** Per-row annotation is the boolean, not a per-field list of unmeasured field names. The boolean plus the per-row null values gives downstream consumers the same information without a third field on every row.
- **D-07:** `documents_read_list` and `documents_skipped_list` on `RunResult` are nullable: their existing `field(default_factory=list)` default is changed to `None`. An adapter that measures zero reads still reports `documents_read_list=[]` (measured empty list); an adapter that did not measure reports `documents_read_list=None` (unmeasured). The on-disk representation of unmeasured is `null`; the on-disk representation of measured-empty is `[]`.
- **D-08:** A list field that is `None` is written as `null` on disk (not `[]`). A list field that is `[]` is written as `[]` on disk. The distinction matters because `metrics_provided: false` is set when the list is `None`, not when it is `[]`.
- **D-09:** `build_summary` and `summarize_variance` skip `null` entries in mean / min / max / sum / stdev computations, exactly as they already skip non-numeric values via `_numeric_values` (no change in the numeric code path; the type filter naturally excludes `None`).
- **D-10:** The variance payload records the actual count of measured rows, not the row count, for each field. A field with `count: 2` of `10` rows means 8 of those rows had `null` for that field.
- **D-11:** List fields (`documents_read_list`, `documents_skipped_list`) appear in `summary.json` variance as a `lengths` block: a count of measured rows plus mean / min / max / stdev of `len(list)` over those rows. Null rows are excluded from the length statistics (the count is the number of rows where the field is a list, not the row count). The `documents_read` / `documents_skipped` count fields keep their existing numeric variance shape (the leverage for "how many documents were read"); the `_list` length statistics are additive.
- **D-12:** The existing `REQUIRED_ROW_FIELDS` in `aggregation.py` keeps the same keys, but the row-normalization default changes from `""` to `None` for the LAB metric fields (`input_tokens`, `output_tokens`, `documents_read`, `total_vdr_files`, `wall_clock_seconds`). Strings stay as `""` for the ID/path fields. The downstream `_numeric_values` filter already handles the `None` correctly — the change is just to stop coercing unmeasured-but-present fields to empty strings.
- **D-13:** `metrics.json` continues to be LAB-compatible. The change is that the LAB-compatible fields are now nullable on disk; the field NAMES and positions are unchanged. `LAB-01` (output compatible with LAB's existing batch-summary tool) is preserved — LAB's consumer either ignores `null` or treats it the same as a missing key.
- **D-14:** `_batch_row` in `scripts/run_benchmark.py` continues to read the metric fields via `metrics.get(...)` — the JSON-loaded value of a `null` field is `None`, which flows through to the batch row unchanged. The `or ""` default in `run_summary.get("input_tokens", metrics.get("input_tokens", ""))` is removed for the LAB metric fields (per D-12).
- **D-15:** `docs/adapter-guide.md` gets a one-paragraph addendum to the "Metrics And Status Semantics" section noting that token / coverage fields are now nullable in `metrics.json` and that a `null` means "not measured", not "zero". The "Results are whole agent-system outcomes" sentence in the doc is unchanged (Phase 5 exit criterion — additive, not a rewrite of `end_state` semantics).
- **D-16:** `docs/adapter-guide.md` "RunResult" field list is updated to reflect that the list fields are now `list[str] | None` and that `None` is a valid unmeasured value.
- **D-17:** `tests/test_metrics.py` adds: a test that `None` for any token / coverage / list field writes `null` on disk (not `0` / `[]`); a test that explicit `0` is preserved (replacing the existing `test_write_metrics_preserves_explicit_zero_values` semantics for the same assertion); a test that `documents_read_list=None` writes `null` not `[]`. The existing `test_write_metrics_no_null_values` is replaced by `test_write_metrics_unmeasured_fields_written_as_null`.
- **D-18:** `tests/test_aggregation.py` adds: a test that mixed measured + unmeasured rows report per-field variance counts that exclude unmeasured rows; a test that `unmeasured_counts` is present in the summary; a test that list-field length statistics skip null rows. A test that the per-row `metrics_provided` boolean reflects whether any LAB metric field on that row is `None`.

### Claude's Discretion

- The exact wording of the docs addendum (D-15, D-16) is Claude's discretion as long as the contract change is reflected.
- The test names in D-17 / D-18 are illustrative; the planner / executor may use any names that satisfy the assertions.
- The migration of any in-tree `metrics.json` fixtures (e.g. `tests/conftest.py`'s `sample_run_result` fixture) from `documents_read_list=[]` to `documents_read_list=None` to exercise the unmeasured path is Claude's discretion; the existing fixture is already a "measured" example and may stay that way if a new fixture covers the unmeasured case.

### Deferred Ideas (OUT OF SCOPE)

None. No todos were folded; cross-reference step reported no pending todos matched to phase 5. The user did mention "per-task token / duration histogram in sweep driver" earlier (per PROJECT.md deferred section), which is correctly parked in the v1.0 deferred list and not part of Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CON-01 | `RunResult` distinguishes "adapter measured 0" from "adapter did not measure". An adapter that did not measure a field must be representable in `RunResult` and `metrics.json` as distinct from a field whose value is genuinely zero. | D-01, D-02, D-07, D-08; one `lab_harness_runner/adapter.py` field-default change + five `write_metrics` lines in `lab_harness_runner/metrics.py`. |
| CON-02 | `write_metrics` writes `null` (not `0`) for unmeasured fields; aggregation (`build_summary`, `summarize_variance`, `write_batch_summary`) skips null entries in mean / sum / variance computations. | D-01, D-09, D-10, D-11, D-12, D-14; verified empirically that `_numeric_values` already filters `None`. |
| CON-03 | Aggregation results that include unmeasured entries are visibly annotated in the batch summary and any per-row metric output, so a downstream reader can tell which entries were measured vs. unmeasured. | D-04, D-05, D-06; new `build_summary` per-row `metrics_provided` boolean + top-level `unmeasured_counts` keyed by field. |
</phase_requirements>

## Architectural Responsibility Map

Phase 5 touches the on-disk persistence + batch aggregation tier only. There is no harness, no protocol, no runtime change.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `RunResult` dataclass nullability | API / Backend (package core) | — | `adapter.py` is the typed boundary between adapter code and the package; D-07 changes two field defaults there. |
| `write_metrics` on-disk coercion | API / Backend (package core) | — | `metrics.py` is the single sink for `metrics.json`. All `None → 0` / `None → []` coercions live in this one function. |
| `_batch_row` JSON pass-through | CLI / scripts (orchestration) | API / Backend | `scripts/run_benchmark.py::_batch_row` is the only bridge from `metrics.json` to batch rows. D-14 removes the `or ""` default for the five LAB metric fields. |
| `build_summary` annotation | API / Backend (package core) | — | The new `metrics_provided` per-row boolean and `unmeasured_counts` top-level field are produced by `build_summary` (D-04, D-05). |
| `summarize_variance` numeric path | API / Backend (package core) | — | No code change needed; the `isinstance(value, int|float)` filter in `_numeric_values` already excludes `None` (verified empirically). |
| `_without_null_values` for diagnostics | API / Backend (package core) | — | D-03 keeps it as-is for `extra_fields`. No behavior change. |
| Docs (adapter-guide.md) | Documentation | — | D-15, D-16 are addendum to existing sections. |

**Sanity check:** All seven capabilities map to a single tier (Backend/package core + CLI scripts). No capability belongs in the harness adapter, the deliverable validator, or the LAB integration. The phase is "pure contract work" in the runner — appropriate for the "runner stays thin" lock in PROJECT.md.

## Standard Stack

No new external packages are required for Phase 5. The phase is a refactor of the existing code with the standard library only.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.13 (project) | Serializing `None` to `null` on disk | Already used; `json.dumps` natively serializes `None` as `null` — no work needed. |
| Python stdlib `statistics` | 3.13 (project) | `mean` / `stdev` for `summarize_variance` | Already used; `statistics.stdev` raises on n<2 — covered by the existing single-element branch. |
| Python stdlib `dataclasses` | 3.13 (project) | `RunResult` field defaults | Already used; `default=None` for list fields is a one-character change. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | (project test dep) | New tests in `test_metrics.py` and `test_aggregation.py` | Already used. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-row `metrics_provided` boolean + top-level `unmeasured_counts` (D-04, D-05) | A per-field "unmeasured" flag on every row | CONTEXT.md D-06: rejected; the boolean plus the per-row null values already gives consumers the same information without a third field per row. |
| `list[str] | None` for `documents_read_list` (D-07) | Keep `list[str]` with `[]` as the unmeasured sentinel | CONTEXT.md D-07: rejected; measured-empty (`[]`) and unmeasured (`None`) must be distinguishable on disk and in `metrics_provided`. |
| Variance over list lengths (D-11) | No variance for list fields | CONTEXT.md D-11: rejected; the `documents_read` count field stays the primary numeric metric; list-length variance is additive. |

**Installation:** None required — the phase uses only the existing standard library and project test dependencies.

**Version verification:** No new packages to verify.

## Package Legitimacy Audit

> **Skipped** — Phase 5 introduces no new external packages. All changes are to existing source files (`adapter.py`, `metrics.py`, `aggregation.py`, `scripts/run_benchmark.py`, `docs/adapter-guide.md`, `tests/test_metrics.py`, `tests/test_aggregation.py`) and use only the Python standard library + existing pytest test dep.

## Architecture Patterns

### System Architecture Diagram

The data flow after Phase 5 is unchanged in shape; only the on-disk serialization changes:

```
+-------------------+    +-----------------+    +----------------------+
|  NanoclawAdapter  |--->|   RunResult     |--->|   write_metrics()    |
|  (Ephemeral/fixed)|    |   (int | None   |    |   lab_harness_runner/|
+-------------------+    |    list | None) |    |   metrics.py         |
                         +-----------------+    +----------+-----------+
                                                          |
                                                          v
                                                 +--------+----------+
                                                 |   metrics.json    |
                                                 |  end_state (req)  |
                                                 |  input_tokens:    |
                                                 |    100 | null     |
                                                 |  documents_       |
                                                 |  read_list:       |
                                                 |    [...] | null   |
                                                 +--------+----------+
                                                          |
                                                          v (read by)
                                            +-------------+-----------+
                                            |  _batch_row() in        |
                                            |  scripts/               |
                                            |  run_benchmark.py       |
                                            +-------------+-----------+
                                                          |
                                                          v
                                            +-------------+-----------+
                                            |   build_summary()       |
                                            |   aggregation.py        |
                                            |   - variance (existing) |
                                            |   - metrics_provided    |
                                            |     (per row, NEW)      |
                                            |   - unmeasured_counts   |
                                            |     (top-level, NEW)    |
                                            +-------------+-----------+
                                                          |
                                                          v
                                                 +--------+----------+
                                                 |   summary.json     |
                                                 +-------------------+
```

### Recommended Project Structure

No structural changes. The phase modifies four files in place:

```
lab_harness_runner/
├── adapter.py         # D-07: change two field defaults (list -> None)
├── metrics.py         # D-01, D-08: remove None -> 0/[] coercions
└── aggregation.py     # D-09, D-10, D-11, D-12, D-04, D-05: add annotations; fix defaults

scripts/
└── run_benchmark.py   # D-14: remove or "" defaults in _batch_row

tests/
├── test_metrics.py    # D-17: replace one test, add three
└── test_aggregation.py  # D-18: add four tests

docs/
└── adapter-guide.md   # D-15, D-16: addendum to "RunResult" and "Metrics And Status Semantics"
```

### Pattern 1: Two-tier unmeasured signal

**What:** The contract change extends the existing two-tier diagnostics pattern (`end_state` is the raw protocol signal; `benchmark_status` is the deliverable-derived reporting state) with a "raw" unmeasured signal at the field level (`None`) plus a "summary" unmeasured signal at the row level (`metrics_provided: false`).

**When to use:** Whenever a field can be either measured-with-a-value or unmeasured, prefer carrying `None` for the unmeasured case at the field level and aggregating into a single boolean at the row level. This avoids a third field per row that would be redundant with the field-level nulls.

**Example:** See D-04 in CONTEXT.md; the boolean plus the per-row null values is the same information as a per-field list of unmeasured field names (D-06).

### Pattern 2: `_numeric_values` as a natural null-skipping filter

**What:** The existing `_numeric_values` helper in `aggregation.py` uses `isinstance(value, int | float)` to filter input — this naturally excludes `None` without any explicit `None` check.

**When to use:** When the aggregation code path needs to skip unmeasured values, the `isinstance` check already does the work. No code change is needed in the numeric path; the change is upstream in `write_metrics` (stop coercing to `0`) and in `REQUIRED_ROW_FIELDS` row normalization (stop coercing to `""`).

**Validated D-09 empirically** (run from this research session):

```python
from lab_harness_runner.aggregation import _numeric_values
_numeric_values([None, 100, None, 200, None])  # => [100.0, 200.0]
_numeric_values([None, None, None])             # => []
_numeric_values([])                              # => []
```

The count of measured rows flows through `summarize_variance` correctly: `summarize_variance([100.0, 200.0])` returns `{"count": 2, "mean": 150.0, ...}` — confirming D-10 ("variance payload records the actual count of measured rows, not the row count").

### Anti-Patterns to Avoid

- **Anti-pattern: Coercing `None` to `0` at the write layer.** This is exactly the current bug Phase 5 fixes. The aggregation layer's `_numeric_values` filter is the right place to handle missing values — not the serialization layer.
- **Anti-pattern: Using `or ""` to coalesce None to empty string in `_batch_row`.** This silently hides the unmeasured signal. D-14 removes it for the five LAB metric fields.
- **Anti-pattern: A per-field "unmeasured" flag on every row.** CONTEXT.md D-06 rejected this; the per-row `metrics_provided` boolean plus the per-row null values is sufficient.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Skip `None` in numeric aggregation | A custom `is not None` loop in `summarize_variance` | The existing `isinstance(value, int|float)` filter in `_numeric_values` | `None` is naturally excluded by the type check — verified empirically. No new code needed. |
| Serialize `None` as JSON `null` | A custom `null_value = "null"` sentinel pass | `json.dumps(..., default=None)` (the default) | Python's stdlib `json` already serializes `None` as `null`; no work needed. |
| Track unmeasured counts | A separate per-field counter thread | The `unmeasured_counts` dict computed inside `build_summary` | The dict is computed once from the same row list that drives `metrics_provided`; no separate pass over the rows. |

**Key insight:** The contract change is mostly about **stopping** code rather than adding it. The new code is the `metrics_provided` boolean + `unmeasured_counts` dict in `build_summary` (small additions), and the typed-field default change in `RunResult` (a one-line change per field).

## Additional Code Surface (Beyond the Four Files in CONTEXT.md)

The CONTEXT.md "Source code" section names four files: `lab_harness_runner/adapter.py`, `lab_harness_runner/metrics.py`, `lab_harness_runner/aggregation.py`, `scripts/run_benchmark.py`. After auditing every call site, **no additional production files need to be modified** for the contract change. The following files are tangentially related but require **no change** for Phase 5:

| File | Relationship to Phase 5 | Required Action |
|------|------------------------|-----------------|
| `scripts/lab_probe.py` | Has its own local `write_metrics` (line 88) that hard-codes `input_tokens: 0`, `output_tokens: 0`, `documents_read: 0`, `documents_read_list: []`, etc. This is a dry-run skeleton writer, not the production `write_metrics` from `lab_harness_runner.metrics`. | **No action required for Phase 5.** This is a probe tool with its own schema; the values it writes are honest "0 means a dry-run skeleton with no measured metrics" rather than the production contract. If the planner wants strict consistency, it can be flagged as a follow-up — but D-01 explicitly says "the contract change applies to the LAB-compatible token / coverage fields only" and the probe writes a different schema (it adds `task_title`, uses `end_state: "dry-run"`). |
| `scripts/fake_run.py` | Calls `write_metrics` (line 120) with a `RunResult` that has unset token/coverage fields. After D-01, the `metrics.json` written by `fake_run.py` will contain `null` for those fields — which is the **correct** new behavior. | **No code change required**; the behavior change is automatic and correct. |
| `scripts/nanoclaw_run.py` | Compatibility wrapper for `run_benchmark.py`; reads `metrics_path` from the summary dict. | **No code change required.** |
| `scripts/sweep.sh` | Reads `benchmark_status` from `metrics.json` for skip-on-clean logic. The contract change does not affect `benchmark_status`. | **No code change required.** Phase 7 handles sweep.sh changes. |
| `lab_harness_runner/nanoclaw_adapter.py` | The `NanoclawAdapter.run()` method returns `RunResult(...)` with only `end_state` and `wall_clock_seconds` populated; all token/coverage fields are unset (`None`). After D-07, `documents_read_list` will be `None` by default — which is the **correct** unmeasured signal. | **No code change required.** |
| `lab_harness_runner/__init__.py` | Re-exports `write_metrics` and friends. | **No code change required.** |
| `tests/test_run_benchmark.py` | The `_batch_row` integration test at line 320+ already constructs batch rows with `input_tokens=10, output_tokens=20` etc. — explicit non-null values. After D-14, the `or ""` default is removed, so explicit `None` would flow through. | **Optional:** planner may add a test case for an unmeasured row. Not strictly required. |
| `tests/test_docs.py` | Required-contract-terms test (line 18+). The terms list does not need new entries; D-15, D-16 are doc text additions, not new contract terms. | **No code change required** unless planner adds a "null vs zero" doc test. |

**Net summary:** CONTEXT.md's four-file scope is accurate. The phase is genuinely small.

## Common Pitfalls

### Pitfall 1: Forgetting to update `documents_read_list` / `documents_skipped_list` field defaults in `RunResult`
**What goes wrong:** If the field default in `adapter.py` stays `field(default_factory=list)`, every adapter that does not set the field will report `[]` (measured-empty), not `None` (unmeasured) — defeating D-07. The downstream `metrics_provided` boolean will incorrectly report `true` for those rows.
**Why it happens:** D-07's wording "nullable" can be misread as "the type annotation can be `None`" without remembering to also change the field default.
**How to avoid:** Change `field(default_factory=list)` to `default=None` for both list fields. Update the type annotation to `list[str] | None`. Add a test that a `RunResult` constructed without those fields writes `null` on disk.
**Warning signs:** A test that constructs `RunResult(end_state="...", wall_clock_seconds=1.0)` and checks `metrics_provided: true` would pass with the bug present; the warning sign is `documents_read_list: []` on disk for an unmeasured run.

### Pitfall 2: Leaving the `or ""` default in `_batch_row`
**What goes wrong:** Even after `write_metrics` writes `null` to `metrics.json`, `JSON.loads` returns Python `None` for the `null` field. The `metrics.get("input_tokens", "")` default would still produce a value (the `""` only triggers on a missing key, not on a present `None`). But the explicit `or ""` in `run_summary.get("input_tokens", metrics.get("input_tokens", ""))` would coalesce a `None` to `""`, which `_numeric_values` then treats as "unmeasured" (not a number) — close to correct, but the on-disk `summary.json` would show `""` rather than `null`, which is wrong by D-12.
**Why it happens:** D-14's wording "remove the `or ""` default for the LAB metric fields" is subtle. The `metrics.get("input_tokens", "")` second-arg default is for the missing-key case; the `or ""` is for the `None`-value case. Only the `or ""` is the bug.
**How to avoid:** D-14 says: "The `or ""` default in `run_summary.get("input_tokens", metrics.get("input_tokens", ""))` is removed for the LAB metric fields (per D-12)." Change to `run_summary.get("input_tokens", metrics.get("input_tokens"))` so a `None` from `metrics.get` flows through unchanged. Combined with D-12's `None` default in `REQUIRED_ROW_FIELDS`, the value reaches `build_summary` as `None` and `_numeric_values` skips it.
**Warning signs:** A test that constructs a `metrics.json` with `"input_tokens": null` and checks the corresponding batch row's `input_tokens` value: should be `None` (Python), not `""`.

### Pitfall 3: Forgetting the `documents_skipped` field (only in `REQUIRED_ROW_FIELDS`? No — but worth checking)
**What goes wrong:** `documents_skipped` appears on `RunResult` and in `write_metrics` but **not** in `VARIANCE_FIELDS` and **not** in `REQUIRED_ROW_FIELDS`. Verified by inspection: `VARIANCE_FIELDS = ('score', 'wall_clock_seconds', 'input_tokens', 'output_tokens', 'documents_read', 'total_vdr_files')` — `documents_skipped` is missing. This is a pre-existing gap, not a Phase 5 issue.
**Why it happens:** Phase 4 decided variance over the fields the LAB aggregator already consumed; `documents_skipped` was added later but never got into the variance set.
**How to avoid:** Out of scope for Phase 5. The CONTEXT.md D-09/D-10/D-11 list is exhaustive for what Phase 5 touches. The planner should not silently expand the variance field set.
**Warning signs:** A test that checks `summary["variance"]["documents_skipped"]` would currently fail. Do not add such a test in Phase 5.

### Pitfall 4: Forgetting the list-field `lengths` block in `build_summary`
**What goes wrong:** D-11 requires `documents_read_list` and `documents_skipped_list` to appear in the variance block as a `lengths` sub-block, not as a regular numeric variance. If the planner adds them to `VARIANCE_FIELDS`, `_numeric_values` will try to compute numeric statistics over a list of strings, which will all be filtered out by `isinstance(value, int|float)`, and the variance block will be `{"count": 0}` — silent data loss.
**Why it happens:** D-11's wording "appear in `summary.json` variance as a `lengths` block" is easy to mis-implement as "add to `VARIANCE_FIELDS`".
**How to avoid:** Implement D-11 as a **separate** variance block, e.g. `variance["documents_read_list"]["lengths"]` containing `{"count": N, "mean": M, "min": m, "max": x, "stdev": s}` where N is the number of measured rows (list is not None) and M/m/x/s are computed over `len(list)` for those rows. A new `LAB_LIST_VARIANCE_FIELDS` tuple (or similar) in `aggregation.py` keeps the list variance separate from `VARIANCE_FIELDS`.
**Warning signs:** A test that checks `summary["variance"]["documents_read_list"]["lengths"]["count"] == 2` for two rows of `["a.pdf", "b.pdf"]` and `None` would fail if list fields were naively added to `VARIANCE_FIELDS`.

### Pitfall 5: Drift between docs and code
**What goes wrong:** `docs/adapter-guide.md` line 33-36 currently lists the optional document lists without nullability: "documents_read_list, documents_skipped_list: optional document lists." A future adapter author reading the doc would not know `None` is valid.
**Why it happens:** D-16 is a small but easy-to-miss doc edit.
**How to avoid:** Update the line to: "documents_read_list, documents_skipped_list: optional document lists; `None` means unmeasured, `[]` means measured zero." The change is one sentence in the doc.
**Warning signs:** `tests/test_docs.py::test_adapter_guide_documents_required_contract_terms` does not currently assert "null" appears in the doc. The planner may add a doc test for the new wording.

### Pitfall 6: Test name collision with replaced test
**What goes wrong:** `tests/test_metrics.py::test_write_metrics_no_null_values` is **replaced** by `test_write_metrics_unmeasured_fields_written_as_null` per D-17. If the planner keeps the old test, it will fail (the new contract permits `null` in JSON for unmeasured fields).
**Why it happens:** D-17's wording "is replaced by" is easy to miss.
**How to avoid:** Delete the old test in the same commit that adds the new one. The new test should assert the **opposite** of the old test: that unmeasured fields DO write `null` on disk.
**Warning signs:** Running `pytest tests/test_metrics.py` after the change — the old test will fail on `assert "null" not in raw_text`.

## Code Examples

Verified patterns from source:

### D-01: `write_metrics` writes None as null
```python
# Source: lab_harness_runner/metrics.py (after Phase 5)
metrics = {
    "input_tokens": result.input_tokens,           # may be None -> null
    "output_tokens": result.output_tokens,         # may be None -> null
    "wall_clock_seconds": result.wall_clock_seconds,
    "documents_read": result.documents_read,       # may be None -> null
    "total_vdr_files": result.total_vdr_files,     # may be None -> null
    "documents_skipped": result.documents_skipped, # may be None -> null
    "documents_read_list": result.documents_read_list,         # may be None -> null
    "documents_skipped_list": result.documents_skipped_list,   # may be None -> null
    "end_state": result.end_state,                 # required, non-null
}
if extra_fields:
    metrics.update(_without_null_values(extra_fields))  # D-03: diagnostics still strip None
```

### D-04, D-05: `build_summary` per-row `metrics_provided` + top-level `unmeasured_counts`
```python
# Source: lab_harness_runner/aggregation.py (after Phase 5) — illustrative
LAB_METRIC_FIELDS = (
    "input_tokens", "output_tokens", "wall_clock_seconds",
    "documents_read", "total_vdr_files", "documents_skipped",
    "documents_read_list", "documents_skipped_list",
)

def build_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    batch_id = str(rows[0]["batch_id"]) if rows else ""
    json_rows = []
    unmeasured_counts: dict[str, int] = {f: 0 for f in LAB_METRIC_FIELDS}
    for row in rows:
        row_metrics_provided = True
        for field in LAB_METRIC_FIELDS:
            if row.get(field) is None:
                row_metrics_provided = False
                unmeasured_counts[field] += 1
        # Annotate row with the boolean; do not strip the nulls.
        annotated = dict(row)
        annotated["metrics_provided"] = row_metrics_provided
        json_rows.append(_jsonable(annotated))
    variance = {
        field: summarize_variance(_numeric_values(row.get(field) for row in rows))
        for field in VARIANCE_FIELDS
    }
    # D-11: list-field length variance, separate from numeric variance
    for list_field in ("documents_read_list", "documents_skipped_list"):
        lengths = [
            float(len(row[list_field]))
            for row in rows
            if isinstance(row.get(list_field), list)
        ]
        variance[list_field] = {"lengths": summarize_variance(lengths)}
    return {
        "batch_id": batch_id,
        "row_count": len(rows),
        "unmeasured_counts": unmeasured_counts,  # D-05
        "rows": json_rows,                       # each row has metrics_provided (D-04)
        "variance": variance,
    }
```

### D-12: `REQUIRED_ROW_FIELDS` row normalization default
```python
# Source: lab_harness_runner/aggregation.py (after Phase 5) — illustrative
# The default for LAB metric fields is None (per D-12). Strings stay as "".
# This is a refactor of the existing line:
#   normalized = {field: row.get(field, "") for field in REQUIRED_ROW_FIELDS}
# Implementation choice: split into two groups with different defaults,
# or use a sentinel-based lookup. Planner picks the cleanest.
```

### D-14: `_batch_row` removes the `or ""` default
```python
# Source: scripts/run_benchmark.py::_batch_row (after Phase 5) — illustrative
# Old:
"input_tokens": run_summary.get("input_tokens", metrics.get("input_tokens", "")),
# New (D-14): the `or ""` is removed; if metrics has "input_tokens": null,
# the JSON-loaded value is None, which flows through to the batch row.
"input_tokens": run_summary.get("input_tokens", metrics.get("input_tokens")),
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `write_metrics` coerces `None` to `0` / `[]` | `write_metrics` writes the underlying value unchanged | Phase 5 (D-01, D-08) | `null` on disk is distinguishable from `0` or `[]`. |
| No `metrics_provided` or `unmeasured_counts` annotation | Per-row `metrics_provided` boolean + top-level `unmeasured_counts` | Phase 5 (D-04, D-05) | Consumers can read unmeasured signal at batch level or per row. |
| `list[str]` with `field(default_factory=list)` for `documents_read_list` / `documents_skipped_list` | `list[str] \| None` with `default=None` | Phase 5 (D-07) | Unmeasured list is `None`, not `[]`; measured-empty stays `[]`. |
| Row normalization default is `""` for all REQUIRED_ROW_FIELDS | Default is `None` for LAB metric fields; `""` for strings | Phase 5 (D-12) | Unmeasured-but-present fields flow through as `None`, not `""`. |
| `_batch_row` uses `or ""` to coalesce `None` to `""` | `_batch_row` lets `None` flow through | Phase 5 (D-14) | The row's `input_tokens` etc. can be `None` (Python) in `summary.json`. |

**Deprecated/outdated:**
- `test_write_metrics_no_null_values`: replaced by `test_write_metrics_unmeasured_fields_written_as_null` (D-17). The old test asserts `"null" not in raw_text`; the new test asserts the opposite (unmeasured fields DO write `null`).
- The `None → 0` / `None → []` coercions in `write_metrics`: removed; `json.dumps` natively serializes `None` as `null` (D-01, D-08).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `json.dumps` natively serializes Python `None` as JSON `null` | Code Examples / State of the Art | Negligible risk — this is a documented stdlib behavior. If wrong, the entire Phase 5 plan needs rework. |
| A2 | `_numeric_values` filters `None` via the `isinstance(value, int|float)` check | Pattern 2 / "Validated D-09 empirically" | Verified empirically in this research session. If the filter were ever changed to `is not None and isinstance(...)`, the D-09 claim would still hold. |
| A3 | The Python dataclass `default=None` on a `list[str] | None` field is sufficient — no `field(default_factory=...)` needed | Common Pitfall 1 | Verified by Python language semantics: `default=None` is the canonical way to express "may be unset, defaults to None" on a dataclass field. The change is straightforward. |
| A4 | `LAB_LIST_VARIANCE_FIELDS` is a reasonable name for the new list-variance fields set | Code Examples / Common Pitfall 4 | Planner's discretion per Claude's Discretion in CONTEXT.md. The exact name is not locked. |
| A5 | `metrics_provided` should be `True` when **all** LAB metric fields are non-null, and `False` when **any** are null | D-04, Code Examples | CONTEXT.md D-04: "true when all LAB-compatible metric fields on the row are measured (i.e. non-null), false when any of them are null." Locked. |
| A6 | The `unmeasured_counts` dict is keyed by the same LAB_METRIC_FIELDS set used for `metrics_provided` | D-05, Code Examples | CONTEXT.md D-05: "keyed by metric field." The exact field set is Claude's discretion; the example uses the full set. |
| A7 | The `lengths` sub-block uses the same `summarize_variance` shape (count, mean, min, max, stdev) | D-11, Code Examples | Locked per D-11: "a count of measured rows plus mean / min / max / stdev of `len(list)`". The shape matches `summarize_variance` directly. |
| A8 | The list-field `lengths` block should be a sub-dict of `variance[list_field]`, not a top-level field on the row | D-11, Code Examples | Planner's discretion. The example shows `variance["documents_read_list"]["lengths"]`; another valid shape is `variance["documents_read_list_lengths"]` (flattened). |
| A9 | The `tests/test_run_benchmark.py::test_batch_execution_runs_each_task_seed_and_writes_metadata_summary` test (line 320+) does not need to be modified for Phase 5 | Additional Code Surface | The test's `fake_single` returns rows with all metric fields set to non-null values (input_tokens=10, etc.), so the new `metrics_provided` boolean will be `True` for all rows — no change needed. If the planner wants a test for an unmeasured row, add it as a new test. |

**If this table is empty:** All claims would have been verified or cited — no user confirmation needed. In this research, the locked decisions in CONTEXT.md cover most of the design choices; the open items above are implementation details within Claude's discretion.

## Open Questions (RESOLVED)

1. **Exact name and shape of the list-field variance block** — RESOLVED: Use the nested form `variance["documents_read_list"]["lengths"]` and `variance["documents_skipped_list"]["lengths"]`. The block contains `{"count", "mean", "min", "max", "stdev"}` from `summarize_variance` over `len(list)` for measured rows. Encoded in Plan 02.

2. **Should `documents_skipped` be added to `VARIANCE_FIELDS`?** — RESOLVED: No. Out of scope for Phase 5. Pre-existing gap, not introduced by the contract change. Planner should not silently fix it. Recorded as a follow-up consideration in RESEARCH.md "Pitfall 3".

3. **Should `sample_run_result` in `tests/conftest.py` be updated?** — RESOLVED: Leave the existing fixture as-is (it's a "measured" example). New unmeasured tests construct `RunResult(...)` inline with `input_tokens=None`, etc. Encoded in Plan 01 and Plan 03.

4. **Should the `metrics_provided` boolean be computed in `build_summary` or upstream?** — RESOLVED: Compute in `build_summary` — it is the single sink for the `summary.json` payload and already iterates over rows. Encoded in Plan 02.

5. **Should the on-disk `summary.json` row carry the boolean via `metrics_provided` key?** — RESOLVED: Use `metrics_provided` as the key, as locked in CONTEXT.md D-04 and ROADMAP.md. Encoded in Plan 02.

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified). Phase 5 has no external tools, services, runtimes, or CLI utilities beyond the project's own code and Python stdlib.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| (none) | — | — | — | — |

**No new dependencies to install.** The phase uses the Python stdlib (`json`, `statistics`, `dataclasses`) and the existing pytest test dep. All changes are to source files in the repo.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project test dep, in `pyproject.toml`) |
| Config file | `pyproject.toml` (no dedicated pytest config; default discovery) |
| Quick run command | `uv run --quiet python -m pytest tests/test_metrics.py tests/test_aggregation.py tests/test_run_benchmark.py -q` |
| Full suite command | `uv run --quiet python -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CON-01 | `RunResult` distinguishes "measured 0" from "not measured" | unit | `pytest tests/test_metrics.py -q` | exists, needs updates |
| CON-01 | List fields are nullable on `RunResult` and write `null` on disk | unit | `pytest tests/test_metrics.py -q` | exists, needs new tests |
| CON-01 | Explicit `0` for a token field writes `0`, not `null` | unit | `pytest tests/test_metrics.py -q` | exists, kept with updated docstring |
| CON-02 | `write_metrics` writes `null` for unmeasured fields, not `0` | unit | `pytest tests/test_metrics.py -q` | exists, **replace** `test_write_metrics_no_null_values` |
| CON-02 | `build_summary` / `summarize_variance` skip `null` in mean / sum / variance | unit | `pytest tests/test_aggregation.py -q` | exists, needs new tests |
| CON-02 | Variance `count` reflects measured rows only | unit | `pytest tests/test_aggregation.py -q` | exists, needs new test |
| CON-02 | List-field `lengths` block excludes null rows | unit | `pytest tests/test_aggregation.py -q` | exists, needs new test |
| CON-03 | Per-row `metrics_provided` boolean reflects whether any LAB metric field is `None` | unit | `pytest tests/test_aggregation.py -q` | exists, needs new test |
| CON-03 | Top-level `unmeasured_counts` is present in `summary.json` | unit | `pytest tests/test_aggregation.py -q` | exists, needs new test |
| D-14 | `_batch_row` passes through `None` for unmeasured metric fields | unit | `pytest tests/test_run_benchmark.py -q` | exists, may need new test |
| D-15, D-16 | `docs/adapter-guide.md` reflects the nullability change | unit (doc test) | `pytest tests/test_docs.py -q` | exists, may need new test |

### Sampling Rate
- **Per task commit:** `uv run --quiet python -m pytest tests/test_metrics.py tests/test_aggregation.py tests/test_run_benchmark.py tests/test_docs.py -q`
- **Per wave merge:** `uv run --quiet python -m pytest -q` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

The existing test infrastructure covers the phase requirements in principle; the work is updating assertions, not adding test framework code.

- [ ] **`tests/test_metrics.py` updates**: Replace `test_write_metrics_no_null_values` with `test_write_metrics_unmeasured_fields_written_as_null`; update `test_write_metrics_none_int_fields_default_to_zero` to assert the opposite (None writes null, not 0); update `test_write_metrics_safe_defaults` similarly; add a new test for `documents_read_list=None` writing `null` not `[]`. Update docstrings to reflect the new contract.
- [ ] **`tests/test_aggregation.py` additions**: Add tests for mixed measured + unmeasured rows; for `unmeasured_counts` presence; for list-field `lengths` block; for per-row `metrics_provided` boolean.
- [ ] **`docs/adapter-guide.md` updates**: Update `RunResult` field list (D-16); add paragraph to "Metrics And Status Semantics" (D-15).
- [ ] No framework config, no shared fixtures, no framework install needed.

*(If no gaps: "None — existing test infrastructure covers all phase requirements.")*

## Security Domain

> Required when `security_enforcement` is enabled. The `.planning/config.json` does not have a `security_enforcement` key; absent = enabled. The phase has no security-relevant changes.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | The phase does not introduce new input handling; the changes are to existing serialization and aggregation code that operates on already-validated Python objects. |
| V6 Cryptography | no | — |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| (none) | — | The phase is a contract refactor. No new attack surface. The existing `metrics.json` and `summary.json` files are local-only artifacts in the LAB checkout (per `result_builder.py` and `aggregation.py`); no network access, no auth, no secret material. |

**Security gate:** Pass. The phase does not introduce or modify any security-relevant code.

## Sources

### Primary (HIGH confidence)
- `/Users/houfu/Projects/lab-harness-runner/lab_harness_runner/metrics.py` (read in full) — confirmed the `None → 0` / `None → []` coercions in `write_metrics` and the `_without_null_values` helper for diagnostics.
- `/Users/houfu/Projects/lab-harness-runner/lab_harness_runner/aggregation.py` (read in full) — confirmed `_numeric_values` filter, `summarize_variance` shape, `VARIANCE_FIELDS`, `REQUIRED_ROW_FIELDS`, and the `""` default in row normalization.
- `/Users/houfu/Projects/lab-harness-runner/lab_harness_runner/adapter.py` (read in full) — confirmed `RunResult` field defaults and `int | None` typing.
- `/Users/houfu/Projects/lab-harness-runner/scripts/run_benchmark.py` (read in full) — confirmed the `or ""` default in `_batch_row` for the five LAB metric fields.
- `/Users/houfu/Projects/lab-harness-runner/scripts/lab_probe.py` (read in full) — confirmed the dry-run skeleton writer is a separate code path, not the production `write_metrics`.
- `/Users/houfu/Projects/lab-harness-runner/scripts/fake_run.py` (read in full) — confirmed the call site is just `write_metrics(run_dir=run_dir, result=result)` with no coercion logic.
- `/Users/houfu/Projects/lab-harness-runner/tests/test_metrics.py` (read in full) — confirmed the test list and the `test_write_metrics_no_null_values` test that D-17 replaces.
- `/Users/houfu/Projects/lab-harness-runner/tests/test_aggregation.py` (read in full) — confirmed the test list and the existing test_build_summary_includes_rows_and_variance_fields.
- `/Users/houfu/Projects/lab-harness-runner/tests/test_run_benchmark.py` (read partially, lines 1-120 and 300-400) — confirmed the integration test for `_batch_row` and its current "all measured" fixtures.
- `/Users/houfu/Projects/lab-harness-runner/docs/adapter-guide.md` (read in full) — confirmed the field list and "Metrics And Status Semantics" sections that D-15, D-16 update.
- `/Users/houfu/Projects/lab-harness-runner/tests/conftest.py` (read in full) — confirmed the `sample_run_result` fixture is a "measured" example.
- `/Users/houfu/Projects/lab-harness-runner/.planning/REQUIREMENTS.md` (read in full) — confirmed CON-01, CON-02, CON-03 are the binding requirements for Phase 5.
- `/Users/houfu/Projects/lab-harness-runner/.planning/ROADMAP.md` (read in full) — confirmed Phase 5 Goal / Context / Deliverables / Exit Criteria.
- `/Users/houfu/Projects/lab-harness-runner/.planning/STATE.md` (read in full) — confirmed project state and session log.

### Secondary (MEDIUM confidence)
- `/Users/houfu/Projects/lab-harness-runner/.planning/phases/05-honest-unmeasured-metrics-contract/05-CONTEXT.md` (read in full) — 18 locked decisions; binding for this research.
- `/Users/houfu/Projects/lab-harness-runner/.planning/phases/05-honest-unmeasured-metrics-contract/05-DISCUSSION-LOG.md` (read in full) — audit trail; rejected alternatives.
- Python stdlib `json` documentation: `json.dumps` serializes `None` as `null` by default — well-documented stdlib behavior.
- Python stdlib `dataclasses` documentation: `default=None` on a typed field is the canonical way to express "may be unset" — well-documented stdlib behavior.

### Tertiary (LOW confidence)
- (none) — All claims in this research were verified by reading the source files or by empirical test of the stdlib behavior. No WebSearch findings were used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; the phase is stdlib-only.
- Architecture: HIGH — every change site is identified and located in source.
- Pitfalls: HIGH — six pitfalls identified, each with a specific warning sign and prevention strategy. The `_numeric_values` filter behavior (Pitfall 4 / Pattern 2) is empirically verified.

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (30 days; the phase is contract-only, no external API surface to drift)
