---
phase: 04-completion-metrics-evaluation-and-scale-out
reviewed: 2026-06-01T16:34:29Z
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
  critical: 2
  warning: 0
  info: 0
  total: 2
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-01T16:34:29Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the Phase 04 status, metrics, evaluator, aggregation, benchmark CLI, adapter guide, and associated tests. The implementation has two blocker-level issues: scoring validation can be bypassed with unsafe deliverable paths, and dashboard comparison reporting can claim a generated artifact when LAB produced none. The targeted tests pass, but they do not cover these failure modes.

Validation run during review:

- `uv run pytest tests/test_status.py tests/test_metrics.py tests/test_evaluator.py tests/test_run_benchmark.py tests/test_aggregation.py tests/test_docs.py -q` - 57 passed
- `uv run python scripts/run_benchmark.py --help` - passed
- LAB batch pollution guard - passed

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01 [BLOCKER]: Scoring pre-validation accepts traversal deliverable names

**File:** `lab_harness_runner/evaluator.py:31`

**Issue:** `score_run()` validates `run_id` and `task_id`, but it joins every `expected_deliverables` entry directly with `output_dir` at lines 31-33. A deliverable like `../outside.docx` is treated as `results/<run-id>/output/../outside.docx`, so scoring can proceed when the file exists in the run directory but not in `output/`. This contradicts the Phase 04 path-safety requirement and the new `status.py` behavior. I verified this path calls the evaluator subprocess when `results/<run-id>/outside.docx` exists and `expected_deliverables=["../outside.docx"]`.

**Fix:**

```python
missing = []
for name in expected_deliverables:
    deliverable_path = _reject_unsafe_relative_path(name, "expected_deliverable")
    if not (output_dir / deliverable_path).exists():
        missing.append(name)
```

Add a regression test in `tests/test_evaluator.py` asserting unsafe deliverable names raise `ValueError` before `subprocess.run()`.

### CR-02 [BLOCKER]: `--compare` can report a dashboard path that LAB never generated

**File:** `lab_harness_runner/evaluator.py:102`

**Issue:** `compare_run()` assumes LAB created `comparison.html` whenever `evaluation.compare` exits zero, then returns the expected path at line 118 without checking that it exists. LAB's compare command exits successfully even when no scored runs are found for a task/area/global scope, and it skips runs without `config.json`. The new benchmark runner writes `metrics.json` and invokes `run_eval`, but it does not create a LAB-compatible per-run `config.json`, so a freshly scored runner output can be invisible to LAB comparison while `scripts/run_benchmark.py` still records `dashboard_paths` as if the dashboard exists.

**Fix:**

Create or preserve the per-run LAB metadata required by `evaluation.compare` before invoking comparison, or make compare explicitly fail when LAB does not produce the expected artifact. At minimum:

```python
subprocess.run(cmd, cwd=lab_path, check=True, capture_output=True, text=True)
if not dashboard_path.exists():
    raise FileNotFoundError(f"LAB comparison did not create {dashboard_path}")
return [dashboard_path]
```

Also add a command-level test that `--score --compare task` either writes the required `config.json` for the just-scored run or raises when `comparison.html` is absent, instead of returning a nonexistent dashboard path.

---

_Reviewed: 2026-06-01T16:34:29Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
