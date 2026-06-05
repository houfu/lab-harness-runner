# Phase 5: Honest Unmeasured Metrics Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 5-Honest Unmeasured Metrics Contract
**Areas discussed:** Annotation shape, List-field nullability, Diagnostic null-pass-through, List-field variance

---

## Annotation shape (CON-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-row boolean (Recommended) | Top-level `metrics_provided` boolean per row + top-level `unmeasured_counts` per field. The per-field nulls stay visible in the row payload. | ✓ |
| Per-row list of unmeasured field names | `unmeasured_fields: ["input_tokens", ...]` per row, listing which fields are null. | |
| Per-field count only, no per-row flag | Top-level `unmeasured_run_count` + per-field counts only; no per-row signal. | |

**User's choice:** Per-row boolean (Recommended)
**Notes:** Matches the ROADMAP's `metrics_provided` example verbatim. The
boolean plus the per-row nulls gives consumers the same information as a
list of unmeasured fields without a third field per row.

---

## List-field nullability (CON-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add `None` as a valid unmeasured list value (Recommended) | `documents_read_list: list[str] \| None`. `None` → `null` on disk. Symmetric with int fields. | ✓ |
| No — keep list types as `list[str]` (unmeasured = empty list) | Keep the existing `field(default_factory=list)` default. Aggregation skips empties. | |

**User's choice:** Yes — add `None` as a valid unmeasured list value (Recommended)
**Notes:** Symmetry with the int fields wins. Measured-empty (`[]`) and
unmeasured (`None`) are distinguishable on disk and in `metrics_provided`.

---

## Diagnostic null-pass-through (D-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Diagnostics keep the existing `no null values` rule (Recommended) | `_without_null_values` continues to strip `None` from `extra_fields`. CON-03's visible annotation carries the unmeasured signal instead. | ✓ |
| Diagnostics may also be `null` on disk | Allow `None` diagnostics to flow through. More uniform but breaks the existing test rule. | |

**User's choice:** Diagnostics keep the existing `no null values` rule (Recommended)
**Notes:** Downstream consumers of diagnostics don't have to deal with
sudden nulls. The CON-03 annotation is the right place for the unmeasured
signal.

---

## List-field variance (CON-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — variance over list lengths for measured rows (Recommended) | `documents_read_list` variance has a `count` (measured rows) plus a `lengths` block (mean / min / max / stdev of `len(list)`). | ✓ |
| No — list fields excluded from variance | Lists don't appear in `variance`. The `documents_read` count field carries the numeric signal. | |

**User's choice:** Yes — variance over list lengths for measured rows (Recommended)
**Notes:** Pre-extraction batch results in v1.0 already used list-length
distributions as a signal; keeping the same shape is the additive move.
The `documents_read` count field stays the primary numeric metric.

---

## Claude's Discretion

- Exact wording of the docs addendum (D-15, D-16).
- Test names in D-17 / D-18.
- Migration of in-tree fixtures (e.g. `sample_run_result`) to exercise
  the unmeasured path.

## Deferred Ideas

None. The user did not mention scope-creep candidates during this
discussion.
