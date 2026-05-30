---
phase: 02
status: findings
depth: standard
reviewed: 2026-05-30
files_reviewed: 12
files_reviewed_list:
  - lab_harness_runner/__init__.py
  - lab_harness_runner/adapter.py
  - lab_harness_runner/evaluator.py
  - lab_harness_runner/metrics.py
  - lab_harness_runner/result_builder.py
  - lab_harness_runner/task_reader.py
  - scripts/fake_run.py
  - tests/conftest.py
  - tests/test_evaluator.py
  - tests/test_metrics.py
  - tests/test_result_builder.py
  - tests/test_task_reader.py
findings:
  critical: 3
  warning: 4
  info: 3
  total: 10
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the core harness-neutral package modules and their test coverage. The code is generally well-structured and the stated key security concern (path traversal in `task_reader.py`) is addressed there — but `run_id` is not validated in `result_builder.py` or `evaluator.py`, which creates the same path-traversal risk through the back door. A semantic bug in `metrics.py` will silently corrupt legitimate zero-valued metrics. The `__init__.py` silences all import errors including real ones, creating a deceptive runtime state. These three are the most serious issues.

---

## Critical Issues

### CR-01: `run_id` Path Traversal — `result_builder.py` and `evaluator.py`

**Files:** `lab_harness_runner/result_builder.py:22`, `lab_harness_runner/evaluator.py:21`

**Issue:** `run_id` is interpolated directly into filesystem paths via `/` operator without any validation. A caller passing `run_id="../../../etc/cron.d/evil"` will cause `build_result_dir` to create (and write into) arbitrary directories outside `lab_path/results/`. The `evaluator.py` has the same flaw — it constructs `output_dir` and `scores.json` paths from an unvalidated `run_id`, and also passes it verbatim as the `--run-id` argument to subprocess (though that argument is not shell-expanded, the path construction is still dangerous).

`task_reader.py` correctly uses `_reject_unsafe_relative_path` for `task_id`, and `fake_run.py` calls a local copy of the same validator for `run_id` before calling the library — but the library functions themselves perform no such check, leaving them exploitable when called directly.

**Fix:** Apply the same validator used for `task_id` inside `build_result_dir` and `score_run`, or expose `_reject_unsafe_relative_path` from `task_reader` and call it:

```python
# result_builder.py
from lab_harness_runner.task_reader import _reject_unsafe_relative_path

def build_result_dir(lab_path: Path, run_id: str) -> tuple[Path, Path]:
    _reject_unsafe_relative_path(run_id, "run_id")
    run_dir = lab_path / "results" / run_id
    ...
```

```python
# evaluator.py
from lab_harness_runner.task_reader import _reject_unsafe_relative_path

def score_run(lab_path, run_id, task_id, expected_deliverables, judge_model=...):
    _reject_unsafe_relative_path(run_id, "run_id")
    _reject_unsafe_relative_path(task_id, "task_id")
    ...
```

Note: `score_run` also does not validate `task_id` before using it in the subprocess command, though that argument is not shell-expanded.

---

### CR-02: Falsy-Zero Bug Silently Corrupts Legitimate Zero Metrics — `metrics.py`

**File:** `lab_harness_runner/metrics.py:16-22`

**Issue:** The pattern `result.input_tokens or 0` conflates `None` (missing) with `0` (legitimately zero). When a run genuinely reads zero documents (`documents_read=0`) or uses zero tokens (`input_tokens=0`), the `or 0` expression evaluates `0` as falsy and replaces it with `0` — which happens to produce the correct numeric value in this case, but the same pattern on the list fields (`result.documents_read_list or []`) will discard a legitimately empty list that was explicitly set. More critically, if a future field is added where `0` has a different meaning than "not provided", this pattern will silently corrupt data.

The immediate real bug: `result.documents_read_list or []` — if `documents_read_list` is `[]` (an empty list, which is the dataclass default), `[] or []` evaluates to `[]` — correct by accident. But if a caller explicitly passes `documents_read_list=[]` to signal "we read zero docs and tracked it", the output is indistinguishable from `documents_read_list=None`. The docstring promises "None fields use safe defaults" — the implementation uses truthiness, not `None`-checks, violating that contract.

**Fix:** Use explicit `None` checks:

```python
metrics = {
    "input_tokens": result.input_tokens if result.input_tokens is not None else 0,
    "output_tokens": result.output_tokens if result.output_tokens is not None else 0,
    "wall_clock_seconds": result.wall_clock_seconds,
    "documents_read": result.documents_read if result.documents_read is not None else 0,
    "total_vdr_files": result.total_vdr_files if result.total_vdr_files is not None else 0,
    "documents_skipped": result.documents_skipped if result.documents_skipped is not None else 0,
    "documents_read_list": result.documents_read_list if result.documents_read_list is not None else [],
    "documents_skipped_list": result.documents_skipped_list if result.documents_skipped_list is not None else [],
    "end_state": result.end_state,
}
```

The existing test suite does NOT catch this bug because no test passes `input_tokens=0` (a real zero) and verifies it is preserved as `0` rather than defaulted.

---

### CR-03: `__init__.py` Silences All `ImportError`s Including Real Ones

**File:** `lab_harness_runner/__init__.py:8-26`

**Issue:** Each module import is wrapped in a bare `try/except ImportError: pass`. This was written to handle "module not yet created" during incremental development, but it now permanently silences any real import error — for instance a `SyntaxError` in a sibling module is not an `ImportError` and will surface, but a genuine `ImportError` caused by a missing transitive dependency, a circular import, or a misspelled internal import will be swallowed silently.

Worse, the public `__all__` list unconditionally includes `"read_task"`, `"build_result_dir"`, `"write_metrics"`, and `"score_run"`. If any of those imports fail silently, consumers doing `from lab_harness_runner import read_task` will get `ImportError: cannot import name 'read_task' from 'lab_harness_runner'` — a confusing error that gives no indication of the real cause.

Now that all four modules exist and are complete, the guard has no value and only creates risk.

**Fix:** Remove the try/except guards entirely since all modules are present:

```python
from lab_harness_runner.task_reader import read_task
from lab_harness_runner.result_builder import build_result_dir
from lab_harness_runner.metrics import write_metrics
from lab_harness_runner.evaluator import score_run
```

---

## Warnings

### WR-01: `end_state` Accepts Any String — No Validation at Boundary

**File:** `lab_harness_runner/adapter.py:23-27`

**Issue:** The docstring on `RunResult` states `end_state must be one of: "clean", "agent_error", "timeout"` but nothing enforces this. An adapter can pass any string (or an empty string, or `None` as a runtime override) and the value will be written to `metrics.json` and passed to downstream evaluators unchecked. Since `end_state` drives evaluation logic in the LAB, an invalid value could corrupt results silently.

**Fix:** Add a `__post_init__` validator or use a `Literal` type:

```python
from typing import Literal

@dataclass
class RunResult:
    end_state: Literal["clean", "agent_error", "timeout"]
    ...
    def __post_init__(self):
        valid = {"clean", "agent_error", "timeout"}
        if self.end_state not in valid:
            raise ValueError(f"end_state must be one of {valid}, got: {self.end_state!r}")
```

---

### WR-02: `_lab_path` in `fake_run.py` Duplicates Library Code — Divergence Risk

**File:** `scripts/fake_run.py:73-86`

**Issue:** `fake_run.py` contains a verbatim copy of `_lab_path()` from `task_reader.py` (lines 23-36 of `task_reader.py` vs lines 73-86 of `fake_run.py`). Similarly, `reject_unsafe_relative_path` in `fake_run.py` (lines 30-36) duplicates `_reject_unsafe_relative_path` from `task_reader.py`. Two copies of security-sensitive path-validation logic will inevitably diverge. If the canonical version in `task_reader.py` is patched (e.g., to reject additional unsafe characters), the copy in `fake_run.py` will not be updated.

**Fix:** Import directly from the library:

```python
from lab_harness_runner.task_reader import _reject_unsafe_relative_path, _lab_path
```

Or expose them as public API if needed.

---

### WR-03: `score_run` Does Not Capture Subprocess Output — Errors Are Opaque

**File:** `lab_harness_runner/evaluator.py:33-49`

**Issue:** `subprocess.run(...)` is called without `capture_output` or `stdout`/`stderr` arguments. When `check=True` raises `CalledProcessError`, the exception contains only the return code — the evaluator's error output (which may explain why it failed) is lost to the caller unless they happen to be running in a terminal. In automated harness runs, this means evaluation failures produce no actionable diagnostic.

**Fix:**

```python
result = subprocess.run(
    [...],
    cwd=lab_path,
    check=True,
    capture_output=True,
    text=True,
)
```

If the stderr should be surfaced on failure, catch and re-raise:

```python
except subprocess.CalledProcessError as exc:
    raise subprocess.CalledProcessError(
        exc.returncode, exc.cmd,
        output=exc.output,
        stderr=exc.stderr,
    ) from exc
```

---

### WR-04: `result_builder.py` Does Not Create `run_dir` — Only `output_dir` Exists on Disk

**File:** `lab_harness_runner/result_builder.py:22-25`

**Issue:** The function returns `(run_dir, output_dir)` and promises in the docstring that "The output_dir is created on disk". `run_dir` is returned but never explicitly created — it only exists because `output_dir.mkdir(parents=True, exist_ok=True)` creates it as a parent. This is correct at runtime but fragile: a caller who uses `run_dir` before `output_dir` is created (e.g., to write `metrics.json` directly to `run_dir`) would find `run_dir` does not exist. In `write_metrics`, the call is `path.write_text(...)` on `run_dir / "metrics.json"` — this works only because `build_result_dir` was called first, and `run_dir` was created as a side effect of `output_dir.mkdir(parents=True)`. The contract is implicit and ordering-dependent.

**Fix:** Explicitly create `run_dir` to make the contract clear and safe regardless of future refactoring:

```python
run_dir = lab_path / "results" / run_id
output_dir = run_dir / "output"
run_dir.mkdir(parents=True, exist_ok=True)  # explicit
output_dir.mkdir(exist_ok=True)             # now no longer needs parents=True
return run_dir, output_dir
```

---

## Info

### IN-01: Test Suite Has Zero Coverage for the `or 0` Falsy-Zero Edge Case

**File:** `tests/test_metrics.py`

**Issue:** No test passes a genuinely zero-valued int field (e.g., `input_tokens=0`) and asserts it is preserved as `0` in the output JSON. All "None defaults to zero" tests pass `None` and check for `0`, which passes even with the broken `or 0` implementation. The bug in CR-02 is invisible to the current test suite.

**Fix:** Add a test:

```python
def test_write_metrics_preserves_explicit_zero(tmp_path):
    result = RunResult(run_id="r", end_state="clean", wall_clock_seconds=1.0,
                       input_tokens=0, documents_read=0)
    data = json.loads(write_metrics(tmp_path, result).read_text())
    assert data["input_tokens"] == 0   # would pass with 'or 0'
    assert data["documents_read"] == 0  # would pass with 'or 0'
    # The critical case: a field that is 0 must not be mistaken for None
    # Verify by checking that the or-0 shortcut cannot distinguish None from 0:
    # this test exposes the semantic gap only when combined with type checking
```

Note: as stated above the numeric case produces the right answer by coincidence; a stronger test would involve a hypothetical non-int field. The list field case (`documents_read_list=[]`) does have the same semantic gap, but no test exercises a path where the distinction between `None` and `[]` matters downstream.

---

### IN-02: `_reject_unsafe_relative_path` Is a Private Function Used Across Module Boundaries

**File:** `lab_harness_runner/task_reader.py:10`

**Issue:** This function is prefixed with `_` (private) but is a security primitive that needs to be called from `result_builder.py`, `evaluator.py`, and `fake_run.py` (see CR-01 and WR-02). The current naming convention signals it should not be imported externally, yet it must be to fix the path traversal issues.

**Fix:** Rename to `reject_unsafe_relative_path` (no underscore) and expose it in `__all__` or move it to a dedicated `lab_harness_runner/security.py` module.

---

### IN-03: Duplicate Test Cases in `test_evaluator.py`

**File:** `tests/test_evaluator.py`

**Issue:** Several test cases are effectively duplicated with minor variable renaming:
- `test_score_run_raises_before_subprocess_when_deliverables_missing` (line 108) and `test_score_run_raises_before_subprocess_when_missing` (line 172) test the exact same behavior.
- `test_score_run_uses_cwd_lab_path` (line 46) and `test_score_run_uses_cwd_lab_path_fixture` (line 204) are identical in behavior.
- `test_score_run_returns_scores_json_path` (line 88) and `test_score_run_returns_scores_path_fixture` (line 218) are identical.

This test bloat makes it harder to identify what is actually covered and what is not.

**Fix:** Consolidate duplicate test cases. The fixture-based variants add no additional coverage.

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
