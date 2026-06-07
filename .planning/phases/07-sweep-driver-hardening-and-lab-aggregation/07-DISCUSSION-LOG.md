# Phase 7: Sweep Driver Hardening And LAB Aggregation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 7-Sweep Driver Hardening And LAB Aggregation
**Areas discussed:** Failure detection for exit-code, Post-run summary scope

---

## Failure detection for exit-code

### Q1: What counts as a 'failed run'?

| Option | Description | Selected |
|--------|-------------|----------|
| Missing metrics.json | Hard crash — run_benchmark.py died before writing anything | |
| benchmark_status is not clean | Any non-clean outcome (timeout, agent_error, missing-deliverable) | |
| User clarification | No metrics.json AND no deliverables (output/ empty or absent) | ✓ |

**User's choice:** User initially pushed back on "missing metrics.json only" and clarified: a failure is when there is **neither** a `metrics.json` nor any file in `output/`. Operational outcomes like timeout (which write metrics.json) are not failures.
**Notes:** This is stricter than "missing metrics.json" — a run that crashes before writing metrics.json but after writing a deliverable is not counted as a failure. The `output/` empty-or-absent check mirrors `derive_benchmark_status`.

---

### Q2: How to track failures across parallel xargs workers?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-run marker file | `$LOG_DIR/$run_id.failed` written by `run_one`; after xargs, count markers | ✓ |
| Shared failure log (append) | Append run_id to a single file; race-safe concern on macOS | |
| You decide | Claude's discretion | |

**User's choice:** Per-run marker file.
**Notes:** Race-free approach; no shared state between parallel workers.

---

### Q3: What does 'no deliverable' mean?

| Option | Description | Selected |
|--------|-------------|----------|
| output/ empty or absent | Matches how derive_benchmark_status works — deliverable presence is the clean signal | ✓ |
| No .docx file in output/ | Hardcodes deliverable type; doesn't generalize | |
| You decide | Claude's discretion | |

**User's choice:** output/ directory empty or absent.

---

## Post-run summary scope

### Q1: What should the summary line count?

| Option | Description | Selected |
|--------|-------------|----------|
| Only tasks run in this pass | Exclude skip-on-clean tasks; reflects "how did this run go" | ✓ |
| All of results/ (cumulative) | Simpler code; inflated by prior passes on resume | |
| You decide | Claude's discretion | |

**User's choice:** Only tasks run in this sweep pass.

---

### Q2: How should run_one record attempted tasks?

| Option | Description | Selected |
|--------|-------------|----------|
| .attempted marker + .failed marker | Always write $LOG_DIR/$run_id.attempted; race-free pattern | ✓ |
| Append to shared attempted list | Simpler loop; append atomicity concern on macOS | |
| You decide | Claude's discretion | |

**User's choice:** Per-run `.attempted` marker file, reusing the same pattern as `.failed`.

---

## Claude's Discretion

- `inventory` output channel split (stdout only vs stdout paths + stderr header) — not explicitly discussed; left to planner
- `LAB_COMPARE` task-filter scope — not explicitly discussed; left to planner
- Separator format between human-readable header and machine-readable paths in `inventory`
- Whether `.attempted`/`.failed` files are cleaned up between runs

## Deferred Ideas

None — discussion stayed within phase scope.

Areas from gray area selection that the user chose not to discuss (handled via ROADMAP.md spec + Claude's discretion):
- `inventory` dual-output channel split
- `LAB_COMPARE` task-filter scope
