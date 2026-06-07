---
phase: 07-sweep-driver-hardening-and-lab-aggregation
plan: 02
subsystem: infra
tags: [bash, sweep, xargs, marker-files, ci, exit-code]

# Dependency graph
requires:
  - phase: 07-sweep-driver-hardening-and-lab-aggregation
    provides: "sweep.sh with hardened TIMEOUT, dual-output inventory, resumable parallel run_one (07-01)"
provides:
  - "Per-run .attempted/.failed marker files written by run_one after every real run attempt"
  - "tally_summary() function printing D-06 summary line from .attempted markers + benchmark_status"
  - "check_failures() function printing failed log paths to stderr and exiting non-zero"
  - "Stale marker cleanup before each sweep pass"
  - "CI-actionable exit code: sweep exits 1 when any .failed marker exists"
affects: [sweep-driver, ci, lab-aggregation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-file marker pattern: touch $LOG_DIR/$run_id.ext for xargs-safe parallel state tracking"
    - "Bash glob no-match guard: [ -f marker ] || continue to handle empty glob expansion"
    - "Failure detection D-01: no metrics.json AND no output/ files = hard crash"

key-files:
  created: []
  modified:
    - scripts/sweep.sh

key-decisions:
  - "Marker-file approach over shared state: each xargs worker writes its own per-run file; no contention (T-07-04)"
  - "D-01 failure condition tests both metrics.json absence AND empty/absent output/ directory"
  - "Skipped tasks (is_clean early return) write no markers — excluded from summary (D-04)"
  - "check_failures returns non-zero via [ failed -eq 0 ] idiom; main() uses check_failures || exit 1"
  - "Stale marker cleanup with 2>/dev/null || true to handle empty LOG_DIR silently"

patterns-established:
  - "Glob no-match guard pattern: for marker in dir/*.ext; do [ -f marker ] || continue; done"
  - "Per-run marker files keyed by deterministic run_id for xargs-safe parallel failure tracking"

requirements-completed: [SWP-03, SWP-04]

# Metrics
duration: 7min
completed: 2026-06-07
---

# Phase 07 Plan 02: Sweep Driver Failure Detection and Post-Run Summary

**Per-run .attempted/.failed marker tracking in run_one plus tally_summary() and check_failures() giving CI a pass-rate summary line and actionable non-zero exit with per-failed-run log paths**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-07T10:58:00Z
- **Completed:** 2026-06-07T11:05:12Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `run_one` writes `$LOG_DIR/$run_id.attempted` after every real run attempt and `$LOG_DIR/$run_id.failed` when neither `metrics.json` nor any `output/` file exists (D-01 hard-crash condition); skip-on-clean branch writes no markers
- `tally_summary()` iterates `.attempted` markers and tallies `benchmark_status` from each run's `metrics.json` into clean/timeout/agent_error/missing_deliverable counts, emitting the D-06 format line `summary: clean=N agent_error=N timeout=N missing_deliverable=N`
- `check_failures()` iterates `.failed` markers, prints `FAILED: $LOG_DIR/$run_id.log` to stderr for each, and returns non-zero when any exist; `main()` ends with `check_failures || exit 1`
- Stale markers from prior passes are cleaned with `rm -f "$LOG_DIR"/*.attempted "$LOG_DIR"/*.failed` before xargs (D-04, T-07-05)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write .attempted/.failed markers in run_one** - `58e02a0` (feat)
2. **Task 2: Add tally_summary, check_failures, marker cleanup, and wire main()** - `0a35d0f` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified

- `scripts/sweep.sh` - Added marker writes in run_one, tally_summary(), check_failures(), marker cleanup in main(), tally_summary and check_failures call sites in main()

## Decisions Made

- D-01 failure condition requires BOTH `metrics.json` absent AND `output/` absent/empty — operational errors (timeout/agent_error) still write `metrics.json` and are not hard crashes
- Glob no-match guard `[ -f "$marker" ] || continue` used in both new functions to handle empty `$LOG_DIR` without error
- Skipped tasks (is_clean early return) must NOT write markers to correctly implement D-04 exclusion from summary
- `check_failures` uses `[ "$failed" -eq 0 ]` as its return expression so it returns 0 when clean and 1 when any `.failed` marker exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The marker-file pattern adds filesystem writes under `$LOG_DIR` (already an existing writable path). T-07-04 through T-07-07 mitigations implemented as specified:
- T-07-04: Per-file markers (no shared-file append contention)
- T-07-05: Stale marker cleanup before xargs
- T-07-06: `case` defaults unknown benchmark_status to missing_deliverable
- T-07-07: `check_failures` prints failed log paths before exit 1

## Next Phase Readiness

- SWP-03 and SWP-04 requirements satisfied
- `sweep.sh` now provides CI-actionable exit codes and a one-line pass-rate summary
- Ready for 07-03 (LAB aggregation shell-out or remaining sweep hardening tasks)

---
*Phase: 07-sweep-driver-hardening-and-lab-aggregation*
*Completed: 2026-06-07*
