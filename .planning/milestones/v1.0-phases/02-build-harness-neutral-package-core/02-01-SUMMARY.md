---
phase: "02-build-harness-neutral-package-core"
plan: "01"
subsystem: "package-scaffold"
tags: ["python-package", "dataclasses", "typing-protocol", "uv-build", "flat-layout"]
dependency_graph:
  requires: []
  provides:
    - "lab_harness_runner.adapter.TaskSpec"
    - "lab_harness_runner.adapter.RunResult"
    - "lab_harness_runner.adapter.Adapter"
    - "pyproject.toml build-system config"
  affects:
    - "lab_harness_runner/task_reader.py (02-02)"
    - "lab_harness_runner/result_builder.py (02-03)"
    - "lab_harness_runner/metrics.py (02-04)"
    - "lab_harness_runner/evaluator.py (02-05)"
tech_stack:
  added:
    - "uv_build>=0.11.8,<0.12.0 (build backend)"
    - "black>=26.5.1 (dev dep)"
    - "pytest>=9.0.3 (dev dep)"
  patterns:
    - "flat layout with module-root=\"\" (D-01)"
    - "dataclass models for TaskSpec and RunResult (D-03)"
    - "typing.Protocol for structural subtyping Adapter (D-07)"
    - "from __future__ import annotations header (lab_probe.py convention)"
key_files:
  created:
    - "lab_harness_runner/adapter.py"
    - "lab_harness_runner/__init__.py"
  modified:
    - "pyproject.toml"
    - "uv.lock"
decisions:
  - "Used try/except in __init__.py for Wave 2 module imports so adapter submodule imports work before Wave 2 plans are executed"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 2
---

# Phase 2 Plan 1: Package Scaffold and Adapter Contracts Summary

**One-liner:** Python package scaffold with TaskSpec/RunResult dataclasses and Adapter typing.Protocol using uv_build flat-layout config.

## What Was Built

The `lab_harness_runner` Python package foundation:

1. **`pyproject.toml` build-system config** — added `[build-system]` with `uv_build>=0.11.8,<0.12.0` and `[tool.uv.build-backend]` with `module-root=""` (required for flat layout). Added `black` and `pytest` as dev dependencies.

2. **`lab_harness_runner/adapter.py`** — defines the three core data contracts:
   - `TaskSpec` dataclass: `task_id`, `instructions`, `documents_dir`, `expected_deliverables`, `run_id`
   - `RunResult` dataclass: `run_id`, `end_state`, `wall_clock_seconds`, optional token/coverage fields with `None` defaults, `documents_read_list`/`documents_skipped_list` with `field(default_factory=list)`
   - `Adapter` Protocol: `run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult`
   - Comment on `RunResult` documents valid `end_state` values: `"clean"`, `"agent_error"`, `"timeout"` (no Enum per D-06)

3. **`lab_harness_runner/__init__.py`** — re-exports all public symbols in `__all__`; Wave 2 module imports (task_reader, result_builder, metrics, evaluator) wrapped in `try/except ImportError` so that adapter imports work before Wave 2 plans are executed.

## Verification Results

- `from lab_harness_runner.adapter import TaskSpec, RunResult, Adapter` — exits 0
- `import lab_harness_runner` — exits 0
- `uv run black --check lab_harness_runner/adapter.py` — exits 0 (no changes needed)
- `uv run black --version` — exits 0 (black 26.5.1 installed)
- `uv run pytest --version` — exits 0 (pytest 9.0.3 installed)
- `pyproject.toml` contains `[build-system]` with `build-backend = "uv_build"` — confirmed
- `pyproject.toml` contains `[tool.uv.build-backend]` with `module-root = ""` — confirmed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] try/except wrapper for Wave 2 module imports in __init__.py**
- **Found during:** Task 2 verification
- **Issue:** The plan specified direct imports from Wave 2 modules in `__init__.py`, but Python loads `__init__.py` when any submodule is first accessed. With direct imports that reference non-existent modules (`task_reader`, `result_builder`, `metrics`, `evaluator`), `from lab_harness_runner.adapter import X` would raise `ModuleNotFoundError`, violating the acceptance criteria.
- **Fix:** Wrapped Wave 2 module imports in `try/except ImportError: pass` so the package is functional now and will seamlessly pick up the Wave 2 modules when they're created in subsequent plans.
- **Files modified:** `lab_harness_runner/__init__.py`
- **Commit:** 875df89
- **Note:** The plan itself acknowledged this tension: "the package is importable but importing from __init__ will fail" vs "from lab_harness_runner.adapter import ... succeeds without ImportError" — the try/except resolves both constraints simultaneously.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add build-system config and dev dependencies | 658a9c2 | pyproject.toml, uv.lock |
| 2 | Create adapter.py with TaskSpec, RunResult, Adapter Protocol | 875df89 | lab_harness_runner/adapter.py, lab_harness_runner/__init__.py |

## Known Stubs

None — this plan creates foundational contracts, not UI-connected data flows.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced by this plan. The `pyproject.toml` additions install two packages from PyPI (`uv_build` via build resolution, `black` and `pytest` as dev deps) — these are acknowledged in the threat model (T-02-01, T-02-SC) as accepted/assumed with extremely high provenance (Astral official package + PSF-sponsored formatter + de facto test framework).

## Self-Check: PASSED

- `lab_harness_runner/adapter.py` — FOUND
- `lab_harness_runner/__init__.py` — FOUND
- Commit 658a9c2 — FOUND (chore: pyproject.toml build-system config)
- Commit 875df89 — FOUND (feat: adapter.py + __init__.py)
