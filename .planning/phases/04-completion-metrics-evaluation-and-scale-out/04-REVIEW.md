---
phase: 04-completion-metrics-evaluation-and-scale-out
reviewed: 2026-06-01T16:40:30Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - lab_harness_runner/status.py
  - lab_harness_runner/metrics.py
  - lab_harness_runner/evaluator.py
  - lab_harness_runner/aggregation.py
  - lab_harness_runner/__init__.py
  - scripts/run_benchmark.py
  - scripts/nanoclaw_run.py
  - docs/adapter-guide.md
  - tests/test_status.py
  - tests/test_metrics.py
  - tests/test_evaluator.py
  - tests/test_run_benchmark.py
  - tests/test_aggregation.py
  - tests/test_docs.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-01T16:40:30Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Re-reviewed the Phase 04 status, metrics, evaluator, aggregation, benchmark CLI, compatibility wrapper, adapter guide, and associated tests after fix commits `9cd60d1` and `d9651a5`.

Prior findings are resolved:

- `score_run()` rejects unsafe `expected_deliverables` before checking the filesystem or invoking `subprocess.run()`.
- `compare_run()` now fails when LAB does not create the expected dashboard.
- `compare_run()` now fails when LAB leaves a stale pre-existing dashboard unchanged.

Validation run during review:

- `uv run pytest tests/test_status.py tests/test_metrics.py tests/test_evaluator.py tests/test_run_benchmark.py tests/test_aggregation.py tests/test_docs.py -q` - 60 passed

## Narrative Findings (AI reviewer)

## Warnings

### WR-01 [WARNING]: Legacy `nanoclaw_run.py` exposes batch flags but routes them to the single-run path

**File:** `scripts/nanoclaw_run.py:17`

**Issue:** `scripts/nanoclaw_run.py` reuses `build_parser()` from the primary benchmark command, so its help and argument parsing accept repeated `--task`, `--tasks`, `--seeds`, and `--batch-id` batch options. The wrapper then always calls `run_single_benchmark(args)` at line 18. Batch invocations through this advertised compatibility entry point fail with the single-run validation error instead of running the batch flow, and that `ValueError` is not converted into a parser error or JSON output by this wrapper. The primary command works, but the compatibility command now has misleading CLI behavior.

**Fix:** Either keep the wrapper single-run by giving it a parser that does not expose batch-only flags, or delegate the same dispatch as `scripts/run_benchmark.py`:

```python
from scripts.run_benchmark import build_parser, run_batch_benchmark, run_single_benchmark, _should_run_batch


def main() -> int:
    parser = build_parser()
    parser.description = __doc__
    parser.set_defaults(adapter="nanoclaw")
    args = parser.parse_args()
    try:
        summary = run_batch_benchmark(args) if _should_run_batch(args) else run_single_benchmark(args)
    except ValueError as exc:
        parser.error(str(exc))
    ...
```

Add a regression test for `scripts.nanoclaw_run.main()` with `--tasks` or repeated `--task` so the compatibility entry point either rejects those flags at parse time or dispatches the batch implementation.

---

_Reviewed: 2026-06-01T16:40:30Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
