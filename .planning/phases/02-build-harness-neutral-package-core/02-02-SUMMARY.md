---
phase: "02-build-harness-neutral-package-core"
plan: "02"
subsystem: "package-core"
tags: ["task-reader", "result-builder", "file-io", "path-safety", "tdd"]
dependency_graph:
  requires: ["02-01"]
  provides: ["read_task", "build_result_dir"]
  affects: ["lab_harness_runner/__init__.py"]
tech_stack:
  added: []
  patterns:
    - "reject_unsafe_relative_path guard (from lab_probe.py) applied to task_id"
    - "criteria[].deliverables extraction (not top-level deliverables dict)"
    - "Path.mkdir(parents=True, exist_ok=True) for idempotent directory creation"
    - "HARVEY_LAB_PATH env var resolution with fallback to ~/Projects/harvey-labs"
key_files:
  created:
    - lab_harness_runner/task_reader.py
    - lab_harness_runner/result_builder.py
    - tests/test_task_reader.py
    - tests/test_result_builder.py
  modified: []
decisions:
  - "Deliverable extraction reads criteria[].deliverables, never top-level 'deliverables' dict (verified-contracts.md + scoring.py constraint)"
  - "KeyError propagates if task.json missing 'instructions' — no silent fallback to instructions.md"
  - "_reject_unsafe_relative_path validates task_id before any filesystem access (T-02-03 mitigated)"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 2 Plan 02: task_reader and result_builder Summary

Implemented `task_reader.py` and `result_builder.py` — the two file-I/O modules that
form the first two steps of every run: reading a Harvey LAB task definition and creating
the run directory tree.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement task_reader.py | ba8185c | lab_harness_runner/task_reader.py |
| 2 | Implement result_builder.py | 39cbd1e | lab_harness_runner/result_builder.py |

TDD commits:
- RED (task_reader): 9563719 — tests/test_task_reader.py
- RED (result_builder): 813f30f — tests/test_result_builder.py

## What Was Built

### task_reader.py

`read_task(lab_path, task_id, run_id) -> TaskSpec` reads `task.json` from
`lab_path/tasks/<task_id>/task.json` and returns a fully populated `TaskSpec`.

Key behaviors:
- `_reject_unsafe_relative_path` validates `task_id` before any filesystem access —
  raises `ValueError` for absolute paths and paths containing `""`, `"."`, or `".."`
- Extracts `expected_deliverables` exclusively from `criteria[].deliverables` (per-criterion
  lists), never from the top-level `"deliverables"` dict in task.json
- `config["instructions"]` — `KeyError` propagates if key is absent (no silent fallback)
- `_lab_path(override)` helper resolves `HARVEY_LAB_PATH` env var with fallback to
  `Path.home() / "Projects" / "harvey-labs"`

### result_builder.py

`build_result_dir(lab_path, run_id) -> tuple[Path, Path]` creates
`lab_path/results/<run_id>/output/` on disk and returns `(run_dir, output_dir)`.

Key behaviors:
- `mkdir(parents=True, exist_ok=True)` — idempotent; safe to call twice with same run_id
- Python `Path /` operator handles slash-containing run_ids as nested directories
- Pure stdlib — no new dependencies

## Verification Results

```
uv run pytest tests/ -x -q
18 passed in 0.01s

from lab_harness_runner import read_task, build_result_dir  # ok
uv run black --check task_reader.py result_builder.py       # no changes needed
```

## TDD Gate Compliance

Both tasks followed RED/GREEN cycle:

1. task_reader: test commit (9563719) → implementation commit (ba8185c)
2. result_builder: test commit (813f30f) → implementation commit (39cbd1e)

RED phases confirmed ModuleNotFoundError before implementation. GREEN phases passed all
tests without refactoring needed.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — both functions are fully implemented with no placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The T-02-03 mitigation
(path traversal via task_id) is fully implemented via `_reject_unsafe_relative_path` in
`task_reader.py` — raises `ValueError` before any filesystem access as required by the
threat register.

T-02-04 (run_id path traversal) accepted per threat register — run_id in this phase comes
from trusted caller code.

## Self-Check: PASSED

- FOUND: lab_harness_runner/task_reader.py
- FOUND: lab_harness_runner/result_builder.py
- FOUND: tests/test_task_reader.py
- FOUND: tests/test_result_builder.py
- FOUND commit ba8185c: feat(02-02): implement task_reader.py
- FOUND commit 39cbd1e: feat(02-02): implement result_builder.py
