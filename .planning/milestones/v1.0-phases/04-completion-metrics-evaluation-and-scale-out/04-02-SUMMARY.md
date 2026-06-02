---
phase: 04-completion-metrics-evaluation-and-scale-out
plan: 02
subsystem: benchmark-command
tags: [python, argparse, pytest, lab, nanoclaw, reports, dashboards]
requires:
  - phase: 04-completion-metrics-evaluation-and-scale-out
    provides: Benchmark status diagnostics and extended metrics from Plan 04-01
provides:
  - Primary single-run LAB benchmark command for nanoclaw
  - LAB scores.json and report.html path preservation
  - Optional LAB compare/dashboard invocation and artifact path reporting
  - Compatibility wrapper for scripts/nanoclaw_run.py
affects: [04-03-aggregation, 04-04-adapter-guide]
tech-stack:
  added: []
  patterns:
    - Compose read_task, build_result_dir, adapter.run, derive_benchmark_status, write_metrics, and score_run in one CLI path
    - Preserve per-run LAB folders under results/<run-id>/ and record dashboard artifacts at LAB-created comparison paths
key-files:
  created:
    - scripts/run_benchmark.py
    - tests/test_run_benchmark.py
  modified:
    - lab_harness_runner/evaluator.py
    - lab_harness_runner/__init__.py
    - scripts/nanoclaw_run.py
    - tests/test_evaluator.py
key-decisions:
  - "run_benchmark.py is the primary benchmark CLI; nanoclaw_run.py delegates to it for compatibility."
  - "Report paths are recorded as results/<run-id>/report.html only when LAB scoring is requested."
  - "Compare/dashboard generation is score-dependent and returns LAB comparison.html paths without moving run folders."
patterns-established:
  - "Parser-level and runtime guards both reject --report/--compare without --score."
  - "Comparison helpers use list-form subprocess calls with cwd set to the LAB root."
requirements-completed: [REQ-14, REQ-21]
duration: 4min
completed: 2026-06-01
---

# Phase 4 Plan 02: Primary LAB-Compatible Benchmark Command Summary

**Single nanoclaw benchmark command that runs LAB tasks, writes status-aware metrics, and preserves LAB score, report, and comparison dashboard artifacts.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-01T16:12:16Z
- **Completed:** 2026-06-01T16:16:14Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `scripts/run_benchmark.py` with the requested `--task`, `--adapter nanoclaw`, `--nanoclaw-dir`, `--group-id`, `--score`, `--report`, and `--compare task|area|all` command shape.
- Wired the single-run path through existing task reading, result directory creation, nanoclaw adapter execution, benchmark status derivation, metrics writing, LAB scoring, report path preservation, and optional LAB compare/dashboard generation.
- Added evaluator helpers for `report.html` path preservation and LAB comparison dashboard invocation using list-form subprocess calls.
- Kept `scripts/nanoclaw_run.py` as a compatibility wrapper that delegates to the primary command internals.

## Task Commits

1. **Task 1: Test single-run command orchestration and report paths** - `d66d8d1` (test)
2. **Task 2: Implement scripts/run_benchmark.py single-run path** - `dc2e09f` (feat)
3. **Task 3: Command smoke and full-suite check** - no file changes; validation passed

## Files Created/Modified

- `scripts/run_benchmark.py` - Primary benchmark CLI and importable `build_parser()` / `run_single_benchmark(args)` internals.
- `scripts/nanoclaw_run.py` - Compatibility wrapper delegating to the primary benchmark command.
- `lab_harness_runner/evaluator.py` - LAB report path helper and compare/dashboard subprocess helper.
- `lab_harness_runner/__init__.py` - Public exports for report/compare helpers.
- `tests/test_run_benchmark.py` - CLI orchestration, report, compare, score-dependency, and unsafe-input tests.
- `tests/test_evaluator.py` - Report path and LAB compare subprocess/path tests.

## Decisions Made

- `--compare` and `--report` are rejected unless `--score` is present because LAB reports and dashboards depend on scored runs.
- `compare_run()` returns expected LAB-created `comparison.html` paths for task, area, and global modes while leaving `results/<run-id>/` untouched.
- The command prints JSON metadata so downstream batch aggregation can consume the same fields without parsing prose.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: evaluator-subprocess | `lab_harness_runner/evaluator.py` | Adds LAB compare subprocess invocation; mitigated with list-form args, `shell=False` default, validated task IDs, and `cwd=lab_path`. |

## Issues Encountered

- RED tests failed as intended before implementation because `scripts.run_benchmark`, `report_path_for_run`, and `compare_run` did not exist.

## Validation

- `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` - 28 passed
- `uv run python scripts/run_benchmark.py --help` - passed
- `uv run pytest tests/ -q` - 78 passed

## User Setup Required

None - no external service configuration required for mocked/unit validation. Live `--score` still depends on LAB judge credentials, as documented in the project contract.

## Next Plan Handoff

Plan 04-03 can build batch and variance reporting around `run_single_benchmark(args)` and the JSON fields it returns: run/task IDs, run/output dirs, benchmark/raw statuses, metrics path, score/report paths, compare mode, and dashboard paths. Batch metadata should continue to reference normal LAB run folders and must not create aggregate `scores.json` files under `results/batches/`.

## Self-Check: PASSED

- Created files exist: `scripts/run_benchmark.py`, `tests/test_run_benchmark.py`, `.planning/phases/04-completion-metrics-evaluation-and-scale-out/04-02-SUMMARY.md`
- Task commits exist: `d66d8d1`, `dc2e09f`
- Validation commands passed: targeted tests, CLI help smoke, and full suite

---
*Phase: 04-completion-metrics-evaluation-and-scale-out*
*Completed: 2026-06-01*
