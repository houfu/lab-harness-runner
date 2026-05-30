---
phase: 02-build-harness-neutral-package-core
plan: "03"
subsystem: core
tags: [python, metrics, subprocess, evaluator, json, pathlib]

# Dependency graph
requires:
  - phase: 02-01
    provides: adapter.py with RunResult dataclass and Adapter Protocol

provides:
  - lab_harness_runner/metrics.py with write_metrics function
  - lab_harness_runner/evaluator.py with score_run function
  - tests/test_metrics.py with 7 TDD unit tests
  - tests/test_evaluator.py with 8 TDD unit tests

affects:
  - 02-04 (fake_run.py exit criterion — imports write_metrics and score_run)
  - 02-05 (tests reference — test files created here)
  - Phase 3 nanoclaw adapter (uses write_metrics and score_run from package public API)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "write_metrics: source all values from RunResult; use 'or 0'/'or []' for None fields"
    - "score_run: D-11 pre-validate deliverables in output_dir before subprocess; D-10 list-form subprocess with cwd=lab_path and check=True"
    - "TDD: RED commit (test) then GREEN commit (feat) per task"
    - "__init__.py: guard each Wave 2 module import independently so partially-created wave remains usable"

key-files:
  created:
    - lab_harness_runner/metrics.py
    - lab_harness_runner/evaluator.py
    - tests/test_metrics.py
    - tests/test_evaluator.py
    - tests/__init__.py
  modified:
    - lab_harness_runner/__init__.py

key-decisions:
  - "write_metrics sources all field values from RunResult parameter, not from disk"
  - "score_run accepts expected_deliverables: list[str] as parameter (caller has TaskSpec, avoids redundant task.json read)"
  - "__init__.py try/except blocks split to one per Wave 2 module — allows individually-created modules to be importable before siblings exist"

patterns-established:
  - "metrics.py: result.field or 0 pattern for optional int fields; result.field or [] for list fields"
  - "evaluator.py: output_dir = lab_path / results / run_id / output (NOT run_dir — Pitfall 4)"
  - "evaluator.py: subprocess.run(list_form, cwd=lab_path, check=True) — no string form, no shell=True"

requirements-completed:
  - Write metrics.json using available RunResult metrics and safe defaults for missing values
  - Invoke LAB's evaluator to produce scores.json
  - Validate that expected deliverable filenames exist before scoring

# Metrics
duration: 8min
completed: 2026-05-30
---

# Phase 2 Plan 03: Metrics Writer and Evaluator Invocation Summary

**write_metrics writes RunResult to metrics.json with safe zero/empty defaults; score_run pre-validates deliverables in output_dir then invokes LAB evaluator via subprocess with cwd=lab_path**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-30T06:18:00Z
- **Completed:** 2026-05-30T06:26:26Z
- **Tasks:** 2 (both TDD with RED/GREEN commits)
- **Files modified:** 6

## Accomplishments

- Implemented `write_metrics(run_dir, result) -> Path` — writes all 9 LAB-required keys to metrics.json with None fields safely defaulted to 0 or []
- Implemented `score_run(lab_path, run_id, task_id, expected_deliverables, judge_model) -> Path` — validates deliverables exist in output_dir before calling subprocess, raises FileNotFoundError listing all missing filenames
- 15 TDD unit tests created and passing (7 for metrics, 8 for evaluator)
- Fixed `__init__.py` to guard each Wave 2 module import independently

## Task Commits

Each task was committed atomically following TDD RED/GREEN pattern:

1. **Task 1 RED: Failing tests for metrics.py** - `f09a285` (test)
2. **Task 1 GREEN: Implement write_metrics** - `effebfc` (feat) — includes __init__.py fix
3. **Task 2 RED: Failing tests for evaluator.py** - `8059bbd` (test)
4. **Task 2 GREEN: Implement score_run** - `f982346` (feat)

_TDD tasks have two commits each (test → feat)_

## Files Created/Modified

- `lab_harness_runner/metrics.py` — write_metrics function; writes all LAB keys with safe defaults
- `lab_harness_runner/evaluator.py` — score_run function; D-11 pre-validation + D-10 subprocess invocation
- `lab_harness_runner/__init__.py` — split monolithic try/except into per-module guards
- `tests/__init__.py` — package marker for tests directory
- `tests/test_metrics.py` — 7 unit tests for write_metrics behaviors
- `tests/test_evaluator.py` — 8 unit tests for score_run behaviors

## Decisions Made

- **expected_deliverables as parameter**: score_run accepts `expected_deliverables: list[str]` directly rather than re-reading task.json — caller already has TaskSpec at call time (Open Question 2 resolution from RESEARCH.md)
- **Independent __init__.py guards**: Fixed the monolithic try/except block in __init__.py to guard each Wave 2 module independently so that an already-created module (e.g., metrics.py) is importable even when sibling modules (task_reader, result_builder) don't exist yet
- **No task_title in metrics.json**: Omitted per plan — task_title was a probe-only diagnostic field ignored by the LAB evaluator

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Split monolithic try/except in __init__.py into per-module guards**
- **Found during:** Task 1 verification (`from lab_harness_runner import write_metrics`)
- **Issue:** The existing __init__.py grouped all four Wave 2 module imports in a single try/except; any one missing module (task_reader, result_builder) caused the entire block to fail silently, making write_metrics unreachable from the package despite metrics.py existing
- **Fix:** Replaced single try/except block with four independent try/except blocks (one per Wave 2 module)
- **Files modified:** lab_harness_runner/__init__.py
- **Verification:** `from lab_harness_runner import write_metrics` succeeds; all 15 tests pass
- **Committed in:** effebfc (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix)
**Impact on plan:** Essential for correctness — acceptance criteria explicitly require `from lab_harness_runner import write_metrics` and `from lab_harness_runner import score_run` to succeed. No scope creep.

## Issues Encountered

None beyond the __init__.py import fix documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- write_metrics and score_run are fully implemented and importable from lab_harness_runner
- 15 TDD unit tests pass
- Both modules are black-formatted
- Wave 2 post-run pipeline is complete: metrics write → deliverable validation → evaluator invocation
- Ready for Plan 04 (fake_run.py integration script) which imports both functions

## Self-Check

- [x] lab_harness_runner/metrics.py exists
- [x] lab_harness_runner/evaluator.py exists
- [x] tests/test_metrics.py exists (7 tests)
- [x] tests/test_evaluator.py exists (8 tests)
- [x] `from lab_harness_runner import write_metrics, score_run` succeeds
- [x] All 15 tests pass
- [x] Both modules black-formatted

---
*Phase: 02-build-harness-neutral-package-core*
*Completed: 2026-05-30*
