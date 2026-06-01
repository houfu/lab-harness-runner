# Phase 4: Completion, Metrics, Evaluation, And Scale-Out - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01T03:35:10Z
**Phase:** 04-completion-metrics-evaluation-and-scale-out
**Areas discussed:** Mixed run outcome semantics, Primary command shape, Batch and variance output, Adapter contract documentation

---

## Mixed Run Outcome Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Strict terminal state + artifact flags | Keep `end_state: "timeout"` and add fields like `expected_deliverables_present: true`, `terminal_status_seen: false`. | |
| New partial-success state | Add a new state like `partial` or `output_without_status` when deliverables exist but status is missing. | |
| Clean if deliverables pass validation | Treat valid expected outputs as clean even without `STATUS:DONE`. | ✓ |

**User's choice:** Clean if deliverables pass validation.
**Notes:** User emphasized that adapter failures can come from several independent systems. Benchmark reporting should be loose as long as the end product exists and LAB can evaluate it. Diagnostic/protocol evidence should still be captured separately.

---

## Primary Command Shape

| Option | Description | Selected |
|--------|-------------|----------|
| One primary command with flags | A single workflow command runs, scores, reports, and aggregates based on flags. | ✓ |
| Separate composable commands | Separate run, score, report, aggregate commands. | |
| Both: composable internals, one wrapper command | Separate functions/scripts internally, with one wrapper as the user path. | |

**User's choice:** One primary command.
**Notes:** The command should optimize for a straightforward benchmark workflow while preserving flags for optional scoring/reporting.

---

## Batch And Variance Output

| Option | Description | Selected |
|--------|-------------|----------|
| Per-run directories plus aggregate summary | Preserve each run as LAB-compatible `results/<run-id>/`; add an aggregate summary referencing those runs. | ✓ |
| One combined benchmark directory | Put everything under a single batch tree. | |
| Only per-run outputs for now | Loop over tasks/seeds and rely only on individual outputs. | |

**User's choice:** Preserve LAB compatibility.
**Notes:** User confirmed expectation that results are saved in the LAB folder. Aggregate metadata should not move or replace LAB-compatible run directories.

---

## Adapter Contract Documentation

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal implementer spec | Interface, fields, status behavior, and examples. | |
| Practical adapter guide | Interface plus examples, failure semantics, deliverable validation, metrics fields, and second-adapter guidance. | ✓ |
| Full public docs | Polished tutorial/API/contribution documentation. | |

**User's choice:** Practical adapter guide.
**Notes:** Enough depth for future community harnesses without expanding into full public documentation.

---

## the agent's Discretion

- Exact script filename and flag names.
- Whether aggregate metadata lives in `results/batches/<batch-id>/summary.json` or a flat `results/<batch-id>-aggregate.json`, as long as LAB compatibility is preserved.
- Exact field names for raw/protocol status, provided they distinguish benchmark-facing status from terminal signal evidence.

## Deferred Ideas

- Full public docs and contribution guide.
- Additional adapter implementations beyond nanoclaw-lq.
