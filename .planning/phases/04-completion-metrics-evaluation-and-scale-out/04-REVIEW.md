---
phase: 04-completion-metrics-evaluation-and-scale-out
reviewed: 2026-06-01T16:37:36Z
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
  critical: 1
  warning: 0
  info: 0
  total: 1
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-01T16:37:36Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Re-reviewed the Phase 04 status, metrics, evaluator, aggregation, benchmark CLI, adapter guide, and associated tests after fix commit `9cd60d1`.

Prior finding CR-01 is resolved: `score_run()` now validates each `expected_deliverables` entry with `_reject_unsafe_relative_path()` before checking the filesystem or invoking `subprocess.run()`, and `tests/test_evaluator.py` covers traversal rejection before subprocess invocation.

Prior finding CR-02 is only partially resolved: `compare_run()` now rejects a missing dashboard path, but it still accepts a stale pre-existing dashboard file as evidence that the current LAB comparison generated a dashboard.

Validation run during review:

- `uv run pytest tests/test_status.py tests/test_metrics.py tests/test_evaluator.py tests/test_run_benchmark.py tests/test_aggregation.py tests/test_docs.py -q` - 59 passed

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01 [BLOCKER]: `--compare` can still report a stale dashboard that LAB did not generate for this run

**File:** `lab_harness_runner/evaluator.py:122`

**Issue:** `compare_run()` checks `dashboard_path.exists()` only after `evaluation.compare` exits successfully. That prevents reporting a path when no file exists, but it does not prove LAB generated the dashboard during this invocation. If `results/comparisons/<scope>/comparison.html` already exists from a previous run and the current `evaluation.compare` exits zero without producing a new dashboard, line 122 passes and `scripts/run_benchmark.py` records `dashboard_paths` anyway. This violates the requirement that compare output should not be reported unless LAB actually generated the dashboard file for the current compare operation.

**Fix:**

Record the dashboard file's pre-run state and require creation or modification after the subprocess starts. For example:

```python
before_mtime = dashboard_path.stat().st_mtime_ns if dashboard_path.exists() else None
subprocess.run(cmd, cwd=lab_path, check=True, capture_output=True, text=True)
if not dashboard_path.exists():
    raise FileNotFoundError(f"LAB comparison did not create {dashboard_path}")
after_mtime = dashboard_path.stat().st_mtime_ns
if before_mtime is not None and after_mtime <= before_mtime:
    raise FileNotFoundError(f"LAB comparison did not update {dashboard_path}")
return [dashboard_path]
```

Add a regression test where `comparison.html` exists before `compare_run()`, mocked LAB exits zero without touching it, and `compare_run()` raises instead of returning the stale path.

---

_Reviewed: 2026-06-01T16:37:36Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
