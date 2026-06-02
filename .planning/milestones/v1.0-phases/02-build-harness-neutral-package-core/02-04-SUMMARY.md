---
phase: "02-build-harness-neutral-package-core"
plan: "04"
subsystem: "tests"
tags: ["testing", "pytest", "unit-tests", "fixtures"]
dependency_graph:
  requires: ["02-02", "02-03"]
  provides: ["test_task_reader", "test_result_builder", "test_metrics", "test_evaluator", "conftest"]
  affects: ["phase-gate"]
tech_stack:
  added: []
  patterns: ["pytest fixtures", "tmp_path isolation", "unittest.mock.patch for subprocess"]
key_files:
  created:
    - tests/conftest.py
  modified:
    - tests/test_task_reader.py
    - tests/test_metrics.py
    - tests/test_evaluator.py
decisions:
  - "Used additive approach: existing tests kept intact, new fixture-based tests added alongside"
  - "Patched lab_harness_runner.evaluator.subprocess.run (module-level) per threat model T-02-11"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-30T06:32:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 02 Plan 04: Test Suite Summary

## One-liner

pytest fixtures and fixture-based unit tests covering task reading, result directory creation, metrics writing, and pre-score subprocess validation with module-level mock patching.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Create conftest.py with tmp_lab and sample_run_result fixtures | 8015f51 |
| 2 | Add fixture-based tests with required named test functions | 99e5945 |

## What Was Built

### Task 1: Test Fixtures (conftest.py)

Created `tests/conftest.py` with two fixtures:

- `tmp_lab(tmp_path)` — creates a minimal LAB directory tree with `tasks/test-area/test-task/task.json` (with `criteria[].deliverables: ["output.docx"]`), a `documents/` directory, and a `results/` directory. Returns `tmp_path` as the mock lab root.
- `sample_run_result()` — returns a `RunResult(run_id="test-run-001", end_state="clean", wall_clock_seconds=1.5, input_tokens=100, output_tokens=50)` for reuse in metrics tests.

### Task 2: Unit Tests

The test files already existed from a prior execution with 33 passing tests. Added fixture-based tests and the specifically-named functions required by the plan's acceptance criteria:

**tests/test_task_reader.py** additions:
- `test_read_task_returns_taskspec` — uses `tmp_lab`, asserts `isinstance(spec, TaskSpec)`
- `test_read_task_deliverables_from_criteria` — uses `tmp_lab`, asserts deliverables come from `criteria[].deliverables`
- `test_read_task_documents_dir` — asserts documents_dir path
- `test_read_task_missing_file_raises` — asserts FileNotFoundError
- `test_read_task_path_traversal_raises` — asserts ValueError for `../evil`
- `test_read_task_absolute_path_raises` — asserts ValueError for `/etc/passwd`

**tests/test_metrics.py** additions:
- `test_write_metrics_safe_defaults` — asserts `input_tokens=0` (not null) when `RunResult.input_tokens=None`
- `test_write_metrics_with_sample_run_result` — uses `sample_run_result` fixture

**tests/test_evaluator.py** additions:
- `test_score_run_raises_before_subprocess_when_missing` — `mock_run.assert_not_called()` after FileNotFoundError
- `test_score_run_calls_subprocess_when_files_present` — asserts `--run-id` and `my-run` in cmd args
- `test_score_run_uses_cwd_lab_path_fixture` — asserts `cwd == tmp_path`
- `test_score_run_returns_scores_path_fixture` — asserts return path

Final count: **45 tests passing** (`uv run pytest tests/ -x -q` exits 0).

## Deviations from Plan

### Auto-fixed Issues

None. Plan executed as written.

### Additive approach for existing tests

The test files (`test_task_reader.py`, `test_result_builder.py`, `test_metrics.py`, `test_evaluator.py`) already existed with 33 passing tests before this plan executed. Rather than rewriting them, tests were added additively to reach the required named functions and fixture coverage. This approach preserves existing behavioral coverage while adding the plan-required fixtures and named tests.

## Verification Results

```
uv run pytest tests/ -x -q
45 passed in 0.05s
```

All acceptance criteria met:
- `tests/conftest.py` defines `tmp_lab` and `sample_run_result` fixtures
- `test_task_reader.py` contains `test_read_task_deliverables_from_criteria`
- `test_evaluator.py` contains `test_score_run_raises_before_subprocess_when_missing` with `mock_run.assert_not_called()`
- `test_metrics.py` contains `test_write_metrics_safe_defaults` asserting `input_tokens == 0` (not null)
- All subprocess patching uses `lab_harness_runner.evaluator.subprocess.run` (module-level, per T-02-11)
- No test creates files outside `tmp_path`

## Threat Flags

None. All tests write only to pytest `tmp_path`. Subprocess patched at module level per threat model T-02-11.

## Self-Check: PASSED

Files exist:
- tests/conftest.py: FOUND
- tests/test_task_reader.py: FOUND (contains test_read_task_deliverables_from_criteria)
- tests/test_metrics.py: FOUND (contains test_write_metrics_safe_defaults)
- tests/test_evaluator.py: FOUND (contains test_score_run_raises_before_subprocess_when_missing)

Commits exist:
- 8015f51: feat(02-04): add shared pytest fixtures in conftest.py
- 99e5945: feat(02-04): add fixture-based tests and required named test functions
