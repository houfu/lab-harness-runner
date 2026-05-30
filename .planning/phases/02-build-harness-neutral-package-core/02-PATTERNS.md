# Phase 2: Build Harness-Neutral Package Core - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 8 new files
**Analogs found:** 7 / 8 (all sourced from `scripts/lab_probe.py`; one file has no analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `lab_harness_runner/__init__.py` | config/exports | — | `scripts/lab_probe.py` (top-level structure) | partial |
| `lab_harness_runner/adapter.py` | model/protocol | — | none in codebase | no analog |
| `lab_harness_runner/task_reader.py` | utility | file-I/O | `scripts/lab_probe.py` (`load_task` + `expected_deliverables`, lines 22-36) | exact |
| `lab_harness_runner/result_builder.py` | utility | file-I/O | `scripts/lab_probe.py` (`main` dir-creation block, lines 126-128) | role-match |
| `lab_harness_runner/metrics.py` | utility | file-I/O | `scripts/lab_probe.py` (`write_metrics`, lines 88-106) | exact |
| `lab_harness_runner/evaluator.py` | service | request-response | `scripts/lab_probe.py` (`eval_command` construction + `reject_unsafe_relative_path`, lines 13-19, 136-141) | role-match |
| `scripts/fake_run.py` | utility/script | request-response | `scripts/lab_probe.py` (`main`, lines 109-151) | role-match |
| `pyproject.toml` (modified) | config | — | `pyproject.toml` (current, lines 1-10) | exact |

---

## Pattern Assignments

### `lab_harness_runner/__init__.py` (config/exports)

**Analog:** `scripts/lab_probe.py` (top-of-file import block, lines 1-11)

**Imports pattern** (lab_probe.py lines 1-11):
```python
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
```

**Public exports pattern** — copy this exact block into `__init__.py`:
```python
# lab_harness_runner/__init__.py
from lab_harness_runner.adapter import Adapter, RunResult, TaskSpec
from lab_harness_runner.evaluator import score_run
from lab_harness_runner.metrics import write_metrics
from lab_harness_runner.result_builder import build_result_dir
from lab_harness_runner.task_reader import read_task

__all__ = [
    "Adapter",
    "TaskSpec",
    "RunResult",
    "read_task",
    "build_result_dir",
    "write_metrics",
    "score_run",
]
```

---

### `lab_harness_runner/adapter.py` (model, protocol)

**Analog:** None — `typing.Protocol` dataclasses do not exist in this codebase yet.

**Core pattern** (from RESEARCH.md Pattern 2 and Pattern 3 — no existing analog):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol


@dataclass
class TaskSpec:
    """Parsed representation of a Harvey LAB task."""

    task_id: str
    instructions: str
    documents_dir: Path
    expected_deliverables: list[str]
    run_id: str


@dataclass
class RunResult:
    """Outcome reported by an adapter after executing a task.

    end_state must be one of: "clean", "agent_error", "timeout"
    """

    run_id: str
    end_state: str
    wall_clock_seconds: float
    # Optional metrics — None when adapter cannot provide them
    input_tokens: int | None = None
    output_tokens: int | None = None
    documents_read: int | None = None
    total_vdr_files: int | None = None
    documents_skipped: int | None = None
    documents_read_list: list[str] = field(default_factory=list)
    documents_skipped_list: list[str] = field(default_factory=list)


class Adapter(Protocol):
    """Contract for all harness adapters.

    Any class implementing run(task_spec, output_dir) -> RunResult
    satisfies this protocol without explicit inheritance.
    """

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult: ...
```

**Note:** `TaskSpec` and `RunResult` live in `adapter.py` alongside `Adapter` (co-location pattern). `__init__.py` re-exports all three.

---

### `lab_harness_runner/task_reader.py` (utility, file-I/O)

**Analog:** `scripts/lab_probe.py` — functions `load_task` (lines 22-26) and `expected_deliverables` (lines 29-36).

**Imports pattern** (lab_probe.py lines 1-9):
```python
from __future__ import annotations

import json
from pathlib import Path
```

**Core pattern** (lab_probe.py lines 22-36):
```python
def load_task(harvey_root: Path, task: Path) -> dict:
    task_json = harvey_root / "tasks" / task / "task.json"
    if not task_json.exists():
        raise FileNotFoundError(f"task.json not found: {task_json}")
    return json.loads(task_json.read_text(encoding="utf-8"))


def expected_deliverables(task_config: dict) -> list[str]:
    names: set[str] = set()
    for criterion in task_config.get("criteria", []):
        for deliverable in criterion.get("deliverables", []):
            if not isinstance(deliverable, str):
                raise ValueError("criterion deliverables must be filenames")
            names.add(deliverable)
    return sorted(names)
```

**Adaptation for `task_reader.py`:** Merge both probe functions into a single `read_task(lab_path, task_id, run_id) -> TaskSpec` function. The `task_id` is a slash-separated string, so split it with `Path(*task_id.split("/"))`. Return a `TaskSpec` instead of a raw dict. Raise `ValueError` (not silently fallback) if `config["instructions"]` is missing.

**Path safety pattern** (lab_probe.py lines 13-19) — apply to `task_id` input:
```python
def reject_unsafe_relative_path(value: str, name: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} contains an unsafe path segment: {value}")
    return path
```

**LAB path resolution pattern** — add as module-private helper (per RESEARCH.md Pattern 4):
```python
import os

def _lab_path(override: Path | None = None) -> Path:
    if override is not None:
        return override
    env = os.environ.get("HARVEY_LAB_PATH")
    if env:
        return Path(env)
    return Path.home() / "Projects" / "harvey-labs"
```

---

### `lab_harness_runner/result_builder.py` (utility, file-I/O)

**Analog:** `scripts/lab_probe.py` — directory creation block in `main` (lines 126-128).

**Core pattern** (lab_probe.py lines 126-128):
```python
run_dir = harvey_root / "results" / run_id
output_dir = run_dir / "output"
output_dir.mkdir(parents=True, exist_ok=True)
```

**Adaptation for `result_builder.py`:** Wrap into `build_result_dir(lab_path: Path, run_id: str) -> tuple[Path, Path]`. Return `(run_dir, output_dir)`. Use `lab_path / "results" / run_id` — Python's `Path /` handles slash-containing run-IDs as nested directories automatically (no split needed).

**Full function shape:**
```python
from __future__ import annotations

from pathlib import Path


def build_result_dir(lab_path: Path, run_id: str) -> tuple[Path, Path]:
    """Create the run directory and output subdirectory.

    Returns (run_dir, output_dir).
    """
    run_dir = lab_path / "results" / run_id
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, output_dir
```

---

### `lab_harness_runner/metrics.py` (utility, file-I/O)

**Analog:** `scripts/lab_probe.py` — `write_metrics` function (lines 88-106).

**Core pattern** (lab_probe.py lines 88-106):
```python
def write_metrics(path: Path, task_config: dict, harvey_root: Path, task: Path) -> None:
    documents_dir = harvey_root / "tasks" / task / "documents"
    total_files = 0
    if documents_dir.exists():
        total_files = sum(1 for item in documents_dir.rglob("*") if item.is_file())

    metrics = {
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_clock_seconds": 0,
        "documents_read": 0,
        "total_vdr_files": total_files,
        "documents_skipped": total_files,
        "documents_read_list": [],
        "documents_skipped_list": [],
        "task_title": task_config.get("title", ""),
        "end_state": "dry-run",
    }
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
```

**Adaptation for `metrics.py`:** Replace signature with `write_metrics(run_dir: Path, result: RunResult) -> Path`. Source all field values from `RunResult` instead of computing from disk. Use `result.field or 0` for optional int fields and `result.field or []` for optional list fields. Return the path to the written file. Do not include `task_title` — that was a probe-only diagnostic field not required by the LAB evaluator. Include `end_state` from `result.end_state`.

**Writes to:** `run_dir / "metrics.json"` (not a path argument — derive it internally).

---

### `lab_harness_runner/evaluator.py` (service, request-response)

**Analog:** `scripts/lab_probe.py` — `eval_command` string construction (lines 136-141) and `reject_unsafe_relative_path` (lines 13-19).

**Core subprocess pattern** (lab_probe.py lines 136-141):
```python
eval_command = (
    "uv run python -m evaluation.run_eval "
    f"--run-id {run_id.as_posix()} "
    f"--task {task.as_posix()} "
    "--judge-model claude-sonnet-4-6"
)
```

**Adaptation for `evaluator.py`:** Use `subprocess.run(list_form, cwd=lab_path, check=True)` — not a string command. The probe builds a string for printing only; the evaluator module must use list form with `check=True` and `cwd=lab_path`.

**Pre-validation pattern** — original probe does NOT do pre-validation; this is new logic per D-11. The validation checks `output_dir / name` for each name in `expected_deliverables: list[str]`. Accept this as a parameter (not re-read from task.json) since the caller already has a `TaskSpec`.

**Full function shape:**
```python
from __future__ import annotations

import subprocess
from pathlib import Path


def score_run(
    lab_path: Path,
    run_id: str,
    task_id: str,
    expected_deliverables: list[str],
    judge_model: str = "claude-sonnet-4-6",
) -> Path:
    """Validate deliverables then invoke the LAB evaluator.

    Returns path to scores.json.
    Raises FileNotFoundError if any expected deliverable is missing.
    Raises subprocess.CalledProcessError if run_eval exits non-zero.
    """
    output_dir = lab_path / "results" / run_id / "output"

    # D-11: pre-score validation
    missing = [name for name in expected_deliverables if not (output_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing deliverables in {output_dir}: {', '.join(missing)}"
        )

    # D-10: subprocess invocation
    subprocess.run(
        [
            "uv", "run", "python", "-m", "evaluation.run_eval",
            "--run-id", run_id,
            "--task", task_id,
            "--judge-model", judge_model,
        ],
        cwd=lab_path,
        check=True,
    )

    return lab_path / "results" / run_id / "scores.json"
```

**Critical:** `cwd=lab_path` is mandatory — without it, `evaluation.run_eval` module is not found. See lab_probe.py line 140 for the explicit `cwd` pattern (though probe prints rather than runs).

---

### `scripts/fake_run.py` (utility/script, request-response)

**Analog:** `scripts/lab_probe.py` — `main` function structure (lines 109-151).

**CLI/main pattern** (lab_probe.py lines 109-151):
```python
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvey-root", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    harvey_root = Path(args.harvey_root).expanduser().resolve()
    task = reject_unsafe_relative_path(args.task, "--task")
    run_id = reject_unsafe_relative_path(args.run_id, "--run-id")
    ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Path safety pattern** (lab_probe.py lines 13-19) — copy inline into fake_run.py:
```python
def reject_unsafe_relative_path(value: str, name: str) -> None:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} contains an unsafe path segment: {value}")
```

**Dummy deliverable writing pattern** (lab_probe.py lines 73-85) — adapt for fake_run.py:
```python
def write_dummy_deliverable(path: Path, task_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Dummy deliverable for LAB result-layout validation.",
        "",
        f"Task: {task_title}",
    ]
    if path.suffix.lower() == ".docx":
        write_minimal_docx(path, lines)
        return
    path.write_text("\n".join(lines), encoding="utf-8")
```

**Adaptation for `fake_run.py`:** Replace `--harvey-root` (required) with `--lab-path` (optional, falls back to env var via `_lab_path`). Replace `--dry-run` with `--score` flag (inverts the sense — scoring is opt-in). Use `uuid.uuid4()` as default run-ID instead of requiring `--run-id`. Import all public symbols from `lab_harness_runner` (not from internal probe functions). Implement `FakeAdapter` class satisfying the `Adapter` protocol structurally.

**Minimal DOCX pattern** (lab_probe.py lines 39-70) — copy `write_minimal_docx` from lab_probe.py verbatim into fake_run.py as a local helper (needed only if `--score` is used with DOCX deliverables; otherwise plain `write_text` suffices for layout validation).

---

### `pyproject.toml` (modified, config)

**Analog:** Current `pyproject.toml` (lines 1-10).

**Current state** (pyproject.toml lines 1-10):
```toml
[project]
name = "lab-harness-runner"
version = "0.1.0"
description = "Harness-neutral runner experiments for Harvey LAB."
requires-python = ">=3.11"
dependencies = []

[tool.black]
line-length = 88
```

**Required addition** — append these blocks (do not modify existing content):
```toml
[build-system]
requires = ["uv_build>=0.11.8,<0.12.0"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = ""
```

**Critical:** `module-root = ""` is required for flat layout. Without it, `uv_build` defaults to `src/` and `lab_harness_runner/` is not found. Verified against live uv 0.11.8.

---

## Shared Patterns

### File header convention
**Source:** `scripts/lab_probe.py` lines 1-4
**Apply to:** All new Python files
```python
from __future__ import annotations
```
Use `from __future__ import annotations` as the first import in every module. This enables PEP 563 postponed evaluation, consistent with lab_probe.py.

### Path construction
**Source:** `scripts/lab_probe.py` lines 22-26, 88-90, 126-128
**Apply to:** `task_reader.py`, `result_builder.py`, `evaluator.py`
```python
# Pattern: always use pathlib operators, never os.path.join
task_json = harvey_root / "tasks" / task / "task.json"
run_dir = harvey_root / "results" / run_id
output_dir = run_dir / "output"
```

### JSON read/write
**Source:** `scripts/lab_probe.py` lines 26, 106
**Apply to:** `task_reader.py`, `metrics.py`
```python
# Read
config = json.loads(task_json.read_text(encoding="utf-8"))
# Write
path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
```
Always pass `encoding="utf-8"` explicitly.

### Path safety guard
**Source:** `scripts/lab_probe.py` lines 13-19
**Apply to:** `task_reader.py` (guard `task_id`), `scripts/fake_run.py` (guard `--task` and `--run-id` CLI args)
```python
def reject_unsafe_relative_path(value: str, name: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} contains an unsafe path segment: {value}")
    return path
```
In `task_reader.py`, place this as a module-private helper `_reject_unsafe_relative_path`. In `fake_run.py`, inline it as a local function (the script is standalone, not an import target).

### Script entry point
**Source:** `scripts/lab_probe.py` lines 150-151
**Apply to:** `scripts/fake_run.py`
```python
if __name__ == "__main__":
    raise SystemExit(main())
```
`raise SystemExit(main())` — not `sys.exit(main())`. Consistent with lab_probe.py convention.

### argparse description from module docstring
**Source:** `scripts/lab_probe.py` line 110
**Apply to:** `scripts/fake_run.py`
```python
parser = argparse.ArgumentParser(description=__doc__)
```
Put the full usage doc in the module-level docstring; pass `description=__doc__` to argparse.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `lab_harness_runner/adapter.py` | model/protocol | — | `typing.Protocol` pattern does not exist in this codebase. Use RESEARCH.md Pattern 3 directly. Python stdlib `typing.Protocol` is the reference. |

---

## Anti-Patterns (from lab_probe.py observation)

These patterns appear in `lab_probe.py` but must NOT be copied into the package:

| Probe Pattern | Why Not to Copy | Package Alternative |
|---------------|-----------------|---------------------|
| `eval_command` as a formatted string (line 136) | String form cannot use `check=True` or `cwd=` safely | Use `subprocess.run([...], cwd=lab_path, check=True)` |
| `--harvey-root` required arg (line 112) | Package functions receive `lab_path` as parameter | Accept `lab_path: Path` parameter; resolve env var in `_lab_path()` helper |
| `write_metrics` takes `task_config: dict` and recomputes files from disk (lines 88-106) | Metrics should come from `RunResult`, not re-derived | Accept `result: RunResult`; source all values from it |
| No pre-validation of deliverables before eval | D-11 locked: must validate before subprocess call | Add missing-file check in `evaluator.py::score_run` |

---

## Metadata

**Analog search scope:** `/Users/houfu/Projects/lab-harness-runner/scripts/`, `/Users/houfu/Projects/lab-harness-runner/` (no `lab_harness_runner/` package exists yet — greenfield)
**Files scanned:** `scripts/lab_probe.py`, `pyproject.toml`, `docs/verified-contracts.md`
**Pattern extraction date:** 2026-05-30
