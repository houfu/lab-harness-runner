# Phase 2: Build Harness-Neutral Package Core - Research

**Researched:** 2026-05-30
**Domain:** Python package scaffolding, dataclasses, typing.Protocol, subprocess invocation, LAB evaluator CLI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Flat layout — source package at `lab_harness_runner/` in the project
  root (not `src/lab_harness_runner/`).
- **D-02:** Flat module structure inside the package: `task_reader.py`,
  `result_builder.py`, `adapter.py`, `metrics.py`, `evaluator.py`. No sub-packages.
- **D-03:** Use `@dataclass` for `TaskSpec` and `RunResult`. No extra dependencies;
  attribute access; optional frozen/slots as needed.
- **D-04:** `TaskSpec` fields: `task_id: str`, `instructions: str`,
  `documents_dir: Path`, `expected_deliverables: list[str]`, `run_id: str`.
- **D-05:** `RunResult` fields: `run_id: str`, `end_state: str`,
  `wall_clock_seconds: float`, plus optional token/coverage fields with `None` defaults.
- **D-06:** `end_state` valid values are string literals `"clean"`, `"agent_error"`,
  `"timeout"` — documented in a comment, no Enum or Literal type alias.
- **D-07:** Adapter contract is a `typing.Protocol` (structural subtyping): any class
  with `run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult` qualifies.
  No explicit inheritance required.
- **D-08:** Locate the Harvey LAB installation via `HARVEY_LAB_PATH` env var, with a
  fallback to `Path.home() / "Projects" / "harvey-labs"`.
- **D-09:** Results directory is always `<HARVEY_LAB_PATH>/results/<run-id>/`.
  No separate `RESULTS_ROOT` env var.
- **D-10:** Invoke the evaluator via `subprocess.run(["uv", "run", "python", "-m",
  "evaluation.run_eval", ...], cwd=lab_path, check=True)`. No sys.path manipulation
  or direct import of LAB internals.
- **D-11:** Pre-score validation: before calling run_eval, check that every expected
  deliverable filename exists in `output/`. Raise `FileNotFoundError` listing missing
  files if any are absent.
- **D-12:** The Phase 2 exit criterion is `scripts/fake_run.py` — a standalone script
  that exercises the full wiring (TaskSpec → output dir → metrics.json → evaluator).
  Not a production adapter; not a test fixture inside the package.

### Claude's Discretion

- Run-ID generation strategy (UUID, timestamp-based, etc.) — Claude decides.
- Exact `__init__.py` exports — Claude decides based on what callers need.
- Whether to add `py.typed` marker for PEP 561 — Claude decides.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

This phase creates the Python package scaffold and harness-agnostic core abstractions
for `lab-harness-runner`. All work uses only Python 3.11+ stdlib — no new runtime
dependencies need to be installed. The only external tooling addition is `black` as a
dev dependency for formatting.

The key integration point is the Harvey LAB evaluator CLI. Research confirms the exact
command signature: `uv run python -m evaluation.run_eval --run-id <id> --task <area/slug>
--judge-model <model>` with two optional flags (`--parallel`, `--verbose`). The
`metrics.json` schema has been verified against the live `run_eval.py` source. The
run directory layout and deliverable matching behavior are verified from Phase 1 contracts.

Package registration for the flat layout requires adding a `[build-system]` table using
`uv_build` with `module-root = ""`. This is verified by live test: a flat layout
`lab_harness_runner/` package with this config becomes importable under `uv run`.

**Primary recommendation:** Add `[build-system]` with `uv_build` and `module-root = ""`
to `pyproject.toml` before creating any package files; everything else follows stdlib
patterns verified against the live LAB source.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Task schema reading | Package (task_reader.py) | — | Parses task.json; LAB filesystem is the source of truth |
| Result directory creation | Package (result_builder.py) | — | Creates `results/<run-id>/output/` under LAB path |
| Adapter contract definition | Package (adapter.py) | — | Protocol definition; nanoclaw adapter implements it in Phase 3 |
| metrics.json writing | Package (metrics.py) | — | Writes into run dir; LAB evaluator reads it optionally |
| Evaluator invocation | Package (evaluator.py) | LAB subprocess | Package owns pre-validation and subprocess call; LAB owns scoring |
| Run-ID generation | Package (__init__.py or result_builder.py) | — | Timestamp-based; Claude's discretion |
| fake_run.py wiring | scripts/ (standalone script) | Package public API | Imports from lab_harness_runner; proves public API works |

---

## Standard Stack

### Core (all stdlib — no install required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` | stdlib (3.7+) | TaskSpec and RunResult model definitions | D-03 locked; zero dependencies |
| `typing` (Protocol) | stdlib (3.8+) | Structural subtyping for Adapter | D-07 locked; no ABC inheritance required |
| `pathlib` | stdlib (3.4+) | All path manipulation | Python 3.11+ standard; cleaner than `os.path` |
| `subprocess` | stdlib | Evaluator invocation via `uv run` | D-10 locked; no sys.path hacks |
| `json` | stdlib | task.json reading, metrics.json writing | Used in lab_probe.py pattern |
| `os` | stdlib | `HARVEY_LAB_PATH` env var lookup | D-08 |
| `uuid` | stdlib | Run-ID generation (recommended) | Collision-free; see Run-ID section |

### Build and Dev Tooling

| Tool | Version | Purpose | Configuration |
|------|---------|---------|---------------|
| `uv_build` | `>=0.11.8,<0.12.0` | Build backend for flat layout | Bundled with uv; `module-root = ""` required |
| `black` | latest | Code formatting | Already in `[tool.black]` with `line-length = 88`; add as dev dep |

[VERIFIED: live test] `uv_build` with `module-root = ""` makes a flat layout package importable
under `uv run`. Confirmed on uv 0.11.8.

[VERIFIED: pyproject.toml] `black` is already configured at `line-length = 88`; only needs
`uv add --dev black` to become runnable.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uv_build` | `hatchling` | hatchling also supports flat layout (used in `redlines` project); uv_build is uv's native backend and version-pins cleanly |
| UUID run-IDs | timestamp run-IDs | Timestamps are human-readable; UUIDs guarantee no collision in concurrent runs. Recommend UUID4 for fake_run.py |

### Installation

```bash
# Add build system (edit pyproject.toml — no install needed for uv_build)
# Add black as dev dependency
uv add --dev black
```

No runtime dependencies to install. `uv_build` is resolved by uv at build time from
the version constraint in `[build-system]`.

---

## Package Legitimacy Audit

> slopcheck was not available at research time. All packages are tagged `[ASSUMED]` per
> protocol. However, `uv_build` is uv's own official build backend (published by Astral),
> and `black` is a PSF-sponsored, decade-old formatter — both are extremely well-established.

| Package | Registry | Purpose | slopcheck | Disposition |
|---------|----------|---------|-----------|-------------|
| `uv_build` | PyPI | Build backend | [ASSUMED] | Approved — Astral official package, same org as uv |
| `black` | PyPI | Code formatter | [ASSUMED] | Approved — PSF-sponsored, ~100M/month downloads |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable. Planner should add a lightweight human-verify checkpoint
before the build-system config task if strict policy requires it, but risk is extremely
low given the provenance of both packages.*

---

## Architecture Patterns

### System Architecture Diagram

```
scripts/fake_run.py
        │
        │ imports
        ▼
lab_harness_runner/
  ├── task_reader.py      ← reads <LAB>/tasks/<task-id>/task.json
  │      │ returns TaskSpec
  │      ▼
  ├── result_builder.py   ← creates <LAB>/results/<run-id>/output/
  │      │ returns (run_dir: Path, output_dir: Path)
  │      ▼
  ├── adapter.py          ← Protocol: run(task_spec, output_dir) -> RunResult
  │      │ (fake_run.py implements inline; real adapter in Phase 3)
  │      ▼
  ├── metrics.py          ← writes <run-dir>/metrics.json from RunResult
  │      ▼
  └── evaluator.py        ← pre-validates output/, calls subprocess uv run run_eval

External dependencies:
  <HARVEY_LAB_PATH>/tasks/<task-id>/task.json   ← input
  <HARVEY_LAB_PATH>/results/<run-id>/output/    ← agent writes here
  <HARVEY_LAB_PATH>/results/<run-id>/metrics.json
  <HARVEY_LAB_PATH>/results/<run-id>/scores.json   ← written by evaluator
  <HARVEY_LAB_PATH>/results/<run-id>/report.html   ← written by evaluator
```

### Recommended Project Structure

```
lab_harness_runner/
├── __init__.py          # public API exports (TaskSpec, RunResult, Adapter, read_task, build_result_dir, write_metrics, score_run)
├── adapter.py           # Adapter Protocol definition
├── task_reader.py       # read_task(lab_path, task_id, run_id) -> TaskSpec
├── result_builder.py    # build_result_dir(lab_path, run_id) -> tuple[Path, Path]
├── metrics.py           # write_metrics(run_dir, run_result) -> Path
└── evaluator.py         # score_run(lab_path, run_id, task_id, judge_model) -> Path
scripts/
├── lab_probe.py         # Phase 1 (existing, do not import)
└── fake_run.py          # Phase 2 exit criterion
pyproject.toml           # updated with [build-system]
```

### Pattern 1: Flat Layout Package Registration

**What:** Register a package whose source lives directly in the project root, not in `src/`.
**When to use:** D-01 locked — always for this project.

```toml
# Source: verified by live uv 0.11.8 test
[build-system]
requires = ["uv_build>=0.11.8,<0.12.0"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = ""
```

The `module-root = ""` tells `uv_build` to look for `lab_harness_runner/` directly in
the project root rather than under `src/`. The package name `lab-harness-runner` maps
to module `lab_harness_runner` (dashes → underscores).

### Pattern 2: TaskSpec and RunResult Dataclasses

**What:** Typed value objects with no external dependencies.
**When to use:** Always — D-03 locked.

```python
# Source: CONTEXT.md D-04, D-05, D-06 + verified against Python 3.11+ stdlib
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
```

### Pattern 3: Adapter Protocol

**What:** Structural subtyping — any class with `run(self, task_spec, output_dir) -> RunResult` qualifies without inheritance.
**When to use:** D-07 locked.

```python
# Source: CONTEXT.md D-07 + Python docs for typing.Protocol
from typing import Protocol
from pathlib import Path


class Adapter(Protocol):
    """Contract for all harness adapters.

    Any class implementing run(task_spec, output_dir) -> RunResult
    satisfies this protocol without explicit inheritance.
    """

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult: ...
```

### Pattern 4: LAB Path Resolution

**What:** Locate Harvey LAB on disk via env var with fallback.
**When to use:** D-08 locked — used in task_reader, result_builder, and evaluator.

```python
# Source: CONTEXT.md D-08
import os
from pathlib import Path


def _lab_path(override: Path | None = None) -> Path:
    """Return the Harvey LAB root directory."""
    if override is not None:
        return override
    env = os.environ.get("HARVEY_LAB_PATH")
    if env:
        return Path(env)
    return Path.home() / "Projects" / "harvey-labs"
```

### Pattern 5: task_reader — Reading task.json

**What:** Load task.json and construct a TaskSpec. Extract deliverables from
`criteria[].deliverables` (not the top-level `deliverables` dict).
**When to use:** First step of any run.

```python
# Source: lab_probe.py + verified-contracts.md + live task.json inspection
import json
from pathlib import Path


def read_task(lab_path: Path, task_id: str, run_id: str) -> TaskSpec:
    """Read task.json and return a TaskSpec.

    task_id must be a relative slash-separated path, e.g.
    'antitrust-competition/analyze-antitrust-hsr-strategy'.
    """
    task_dir = lab_path / "tasks" / Path(*task_id.split("/"))
    task_json = task_dir / "task.json"
    if not task_json.exists():
        raise FileNotFoundError(f"task.json not found: {task_json}")

    config = json.loads(task_json.read_text(encoding="utf-8"))

    # Extract unique expected deliverables from criteria[].deliverables
    deliverables: set[str] = set()
    for criterion in config.get("criteria", []):
        for d in criterion.get("deliverables", []):
            if not isinstance(d, str):
                raise ValueError(f"criterion deliverable must be a string, got: {d!r}")
            deliverables.add(d)

    return TaskSpec(
        task_id=task_id,
        instructions=config["instructions"],
        documents_dir=task_dir / "documents",
        expected_deliverables=sorted(deliverables),
        run_id=run_id,
    )
```

**Important:** `config["instructions"]` is required (REQUIRED_TASK_KEYS in run_eval.py
includes `"instructions"`). Do not fall back silently to `instructions.md` — that is a
LAB harness convenience, not an evaluator contract. [VERIFIED: run_eval.py line 26]

### Pattern 6: result_builder

**What:** Create `results/<run-id>/output/` under the LAB root.
**When to use:** Before adapter execution.

```python
# Source: CONTEXT.md D-09, verified-contracts.md
from pathlib import Path


def build_result_dir(lab_path: Path, run_id: str) -> tuple[Path, Path]:
    """Create the run directory and output subdirectory.

    Returns (run_dir, output_dir).
    run_id may be a slash-separated path (e.g., 'area/slug/run-001').
    """
    run_dir = lab_path / "results" / Path(*run_id.split("/")) if "/" in run_id else lab_path / "results" / run_id
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, output_dir
```

### Pattern 7: metrics_writer

**What:** Write `metrics.json` from a RunResult, with safe zero/empty defaults for
missing optional fields.
**When to use:** After adapter execution, before evaluator invocation.

```python
# Source: verified-contracts.md, run_eval.py lines 137-152, lab_probe.py write_metrics()
import json
from pathlib import Path


def write_metrics(run_dir: Path, result: RunResult) -> Path:
    """Write metrics.json to run_dir. Always succeeds with safe defaults."""
    metrics = {
        "input_tokens": result.input_tokens or 0,
        "output_tokens": result.output_tokens or 0,
        "wall_clock_seconds": result.wall_clock_seconds,
        "documents_read": result.documents_read or 0,
        "total_vdr_files": result.total_vdr_files or 0,
        "documents_skipped": result.documents_skipped or 0,
        "documents_read_list": result.documents_read_list or [],
        "documents_skipped_list": result.documents_skipped_list or [],
        "end_state": result.end_state,
    }
    path = run_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path
```

LAB reads exactly these keys with `.get(key, default)` — extra keys are ignored. The
`end_state` key is not read by LAB's evaluator but is preserved for harness diagnostics
(consistent with lab_probe.py's pattern).

### Pattern 8: Evaluator Invocation

**What:** Pre-validate deliverables exist, then invoke `evaluation.run_eval` via subprocess.
**When to use:** After metrics.json is written.

```python
# Source: CONTEXT.md D-10, D-11; verified-contracts.md; run_eval.py lines 183-201
import subprocess
from pathlib import Path


def score_run(
    lab_path: Path,
    run_id: str,
    task_id: str,
    judge_model: str = "claude-sonnet-4-6",
) -> Path:
    """Validate deliverables then invoke the LAB evaluator.

    Returns path to scores.json.
    Raises FileNotFoundError if any expected deliverable is missing.
    Raises subprocess.CalledProcessError if run_eval exits non-zero.
    """
    output_dir = lab_path / "results" / run_id / "output"

    # D-11: pre-score validation
    task_dir = lab_path / "tasks" / Path(*task_id.split("/"))
    config = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    expected = sorted({
        d for c in config.get("criteria", []) for d in c.get("deliverables", [])
    })
    missing = [name for name in expected if not (output_dir / name).exists()]
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

### Pattern 9: fake_run.py Structure

**What:** Standalone script that imports from `lab_harness_runner` and exercises the full pipeline.
**When to use:** Phase 2 exit criterion (D-12).

```python
#!/usr/bin/env python3
"""Fake adapter run — proves the full package wiring end-to-end.

Creates a hand-crafted output directory (placeholder deliverables),
writes metrics.json, and optionally invokes the LAB evaluator.

Usage:
    uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy
    uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy --score
"""

import argparse
import time
import uuid
from pathlib import Path

from lab_harness_runner import (
    Adapter,
    RunResult,
    TaskSpec,
    build_result_dir,
    read_task,
    score_run,
    write_metrics,
)


class FakeAdapter:
    """Minimal adapter that writes placeholder deliverables."""

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        start = time.monotonic()
        for filename in task_spec.expected_deliverables:
            (output_dir / filename).write_text(
                f"Placeholder for {filename} — fake_run.py", encoding="utf-8"
            )
        return RunResult(
            run_id=task_spec.run_id,
            end_state="clean",
            wall_clock_seconds=time.monotonic() - start,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="area/slug task path")
    parser.add_argument("--run-id", help="explicit run ID (default: uuid4)")
    parser.add_argument("--score", action="store_true", help="invoke LAB evaluator")
    parser.add_argument("--judge-model", default="claude-sonnet-4-6")
    args = parser.parse_args()

    run_id = args.run_id or str(uuid.uuid4())
    lab_path = ...  # use _lab_path() from lab_harness_runner

    task_spec = read_task(lab_path=lab_path, task_id=args.task, run_id=run_id)
    run_dir, output_dir = build_result_dir(lab_path=lab_path, run_id=run_id)

    adapter = FakeAdapter()
    result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    write_metrics(run_dir=run_dir, result=result)
    print(f"Run directory: {run_dir}")
    print(f"Deliverables: {', '.join(task_spec.expected_deliverables)}")

    if args.score:
        scores_path = score_run(
            lab_path=lab_path,
            run_id=run_id,
            task_id=args.task,
            judge_model=args.judge_model,
        )
        print(f"Scores written to: {scores_path}")
    else:
        print("Skipping evaluator (pass --score to invoke)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `FakeAdapter` satisfies the `Adapter` Protocol structurally — it has `run(self, task_spec, output_dir) -> RunResult` — without importing or inheriting from `Adapter`.

### Anti-Patterns to Avoid

- **Importing LAB internals directly:** Never `from evaluation.run_eval import evaluate_run`. D-10 locked subprocess; direct import creates a hard path dependency.
- **Defining `run_id` as a slash-only path:** `Path(*run_id.split("/"))` handles both flat (`"my-run"`) and nested (`"area/slug/run-001"`) IDs. The LAB stores results as `RESULTS_DIR / run_id` where `run_id` is passed directly to `Path`. Use `lab_path / "results" / run_id` — if `run_id` contains slashes, Python's `Path /` operator handles it as nested directories.
- **Using `instructions.md` fallback silently:** The evaluator requires `task.json["instructions"]` per `REQUIRED_TASK_KEYS`. Fail loudly if it is absent rather than falling back.
- **Writing metrics.json with None values:** LAB uses `.get(key, 0)` — `null` in JSON becomes `None` in Python which LAB accepts via `.get()`, but writing `0` explicitly is cleaner and matches the probe pattern.
- **Passing `check=False` to subprocess:** The evaluator exits non-zero on task validation errors. `check=True` ensures failures surface as `CalledProcessError` rather than silent scoring omissions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structural subtyping for adapter contract | Custom ABC or register() calls | `typing.Protocol` | Protocol is stdlib; no inheritance; structural — D-07 locked |
| Path safety for run-id | Custom path sanitizer | Document that run-id must be a safe relative path (same pattern as lab_probe.py's `reject_unsafe_relative_path`) | The LAB evaluator itself accepts arbitrary strings; validation in fake_run.py is sufficient |
| Deliverable DOCX creation in fake_run.py | Full-fidelity DOCX | Plain `.write_text()` for non-DOCX, minimal ZipFile for `.docx` | The evaluator opens DOCX via python-docx; a minimal valid DOCX (as in lab_probe.py's `write_minimal_docx`) passes. However, fake_run.py's exit criterion is evaluator invocation, not full scoring — placeholder text files suffice for layout validation; only needed if `--score` is passed with a real judge |
| JSON schema validation | jsonschema library | Plain dict key checks + KeyError | The task.json schema is simple enough; LAB's own validator (`validate_task_config`) runs at evaluation time |

---

## Verified Evaluator CLI Contract

[VERIFIED: run_eval.py source]

### Command Signature

```bash
uv run python -m evaluation.run_eval \
    --run-id <run-id> \
    --task <area/slug> \
    --judge-model claude-sonnet-4-6 \
    [--parallel 6] \
    [--verbose]
```

| Flag | Required | Default | Notes |
|------|----------|---------|-------|
| `--run-id` | YES | — | String; becomes path segment under `RESULTS_DIR` |
| `--task` | YES | — | Slash-separated; minimum 2 parts (area/slug) |
| `--judge-model` | NO | `claude-sonnet-4-6` | LLM judge model name |
| `--parallel` | NO | `6` | Concurrent judge calls |
| `--verbose` | NO | false | Print full JSON scores to stdout |

The wrapper function in `evaluator.py` should accept `judge_model` and pass it
explicitly rather than relying on the default — makes test invocations deterministic.
Do not expose `--parallel` in the wrapper's public API for Phase 2; hard-code the
default or omit it (evaluator default is 6).

### What run_eval writes

- `results/<run-id>/scores.json` — scoring result
- `results/<run-id>/report.html` — HTML report (via `generate_report()`)

### What run_eval reads

- `<LAB>/tasks/<task-id>/task.json` — task schema (validated)
- `results/<run-id>/output/` — agent output files
- `results/<run-id>/metrics.json` — optional; keys read via `.get()` with safe defaults

### metrics.json: Verified Schema

[VERIFIED: run_eval.py lines 137-152]

```json
{
  "input_tokens": 0,
  "output_tokens": 0,
  "wall_clock_seconds": 0.0,
  "documents_read": 0,
  "total_vdr_files": 0,
  "documents_skipped": 0,
  "documents_read_list": [],
  "documents_skipped_list": []
}
```

All fields are optional (`metrics.get(key, default)`). Extra keys (like `end_state`,
`task_title`) are ignored by LAB's evaluator. The `end_state` key should still be
written for harness diagnostics — it does not interfere.

### Task ID Format

[VERIFIED: live task directory inspection + run_eval.py `_resolve_task_dir`]

Tasks in this LAB instance follow a 2-part format: `<area>/<slug>`, e.g.:
`antitrust-competition/analyze-antitrust-hsr-strategy`

The evaluator accepts any depth ≥ 2 parts. The `report.py` docstring shows a 5-part
example (`area/slug/scenario/model/timestamp`) from a different LAB configuration.
Use the 2-part format matching the live task directory structure.

### Run-ID Format

[VERIFIED: run_eval.py + results directory inspection]

Run-ID is any string safe as a filesystem path component. Existing runs use flat names
like `manual-probe`. The evaluator simply does `RESULTS_DIR / run_id` — if run-id
contains `/`, Python creates nested directories. For `fake_run.py`, use `uuid.uuid4()`
(hex string, no slashes) as the default. Allow `--run-id` override for reproducibility.

---

## Common Pitfalls

### Pitfall 1: Flat layout not importable without build-system

**What goes wrong:** `from lab_harness_runner import ...` raises `ModuleNotFoundError`
when running `uv run scripts/fake_run.py`.

**Why it happens:** Without a `[build-system]` table in `pyproject.toml`, uv treats the
project as an application (no package install). The `lab_harness_runner/` directory
exists on disk but is not installed into `.venv/`.

**How to avoid:** Add `[build-system]` with `uv_build` AND `[tool.uv.build-backend]
module-root = ""` before creating any package files.

**Warning signs:** `uv run python -c "import lab_harness_runner"` fails even after
the `lab_harness_runner/__init__.py` file exists.

### Pitfall 2: Using `src/` module-root (uv_build default)

**What goes wrong:** Package files under `lab_harness_runner/` are not found at build
time; uv_build looks for `src/lab_harness_runner/` by default.

**Why it happens:** `uv_build` defaults to `module-root = "src"`. This is the `uv init
--package` default and is correct for src layout, not flat layout.

**How to avoid:** Always include `[tool.uv.build-backend] module-root = ""` for this
project. [VERIFIED: live test confirms `module-root = ""` is required]

### Pitfall 3: Extracting deliverables from top-level `deliverables` dict vs criteria

**What goes wrong:** Code reads `config["deliverables"]` (a top-level dict in task.json)
instead of `criteria[].deliverables` (per-criterion lists).

**Why it happens:** task.json has BOTH a top-level `"deliverables"` key (a dict mapping
filename → filename) AND per-criterion `"deliverables"` lists. The scoring code in
`scoring.py` reads from `criteria[].deliverables`. [VERIFIED: scoring.py lines 315-321]

**How to avoid:** Always extract from `criteria[].deliverables`. The top-level
`deliverables` dict is unused by the evaluator's scoring path.

**Warning signs:** TaskSpec.expected_deliverables is a dict instead of a list, or
contains unexpected keys.

### Pitfall 4: Pre-validation checks the wrong directory

**What goes wrong:** FileNotFoundError is raised even though deliverables exist, because
the check looks at `run_dir` instead of `run_dir / "output"`.

**Why it happens:** The evaluator reads from `run_dir / "output"` (scoring.py line 313),
not from `run_dir` directly.

**How to avoid:** Pre-validation in `evaluator.py` must check `output_dir = run_dir /
"output" / filename`. [VERIFIED: verified-contracts.md + scoring.py line 313]

### Pitfall 5: subprocess cwd not set to lab_path

**What goes wrong:** `evaluation.run_eval` raises `ModuleNotFoundError` for LAB
internal modules (e.g., `from evaluation.judge import Judge`).

**Why it happens:** `uv run python -m evaluation.run_eval` resolves modules relative to
the working directory. If cwd is the runner project root, `evaluation` package is not
found.

**How to avoid:** Always pass `cwd=lab_path` to `subprocess.run()`. [VERIFIED:
verified-contracts.md + lab_probe.py eval_command construction]

### Pitfall 6: run_id with slashes passed as a single CLI argument

**What goes wrong:** If `run_id = "area/slug/run-001"`, the CLI call needs
`--run-id area/slug/run-001` — this is fine as a string argument. But `results / run_id`
where `run_id` is a Python string with `/` will be interpreted by `Path` as multiple
path components, creating nested directories. This is correct behavior but can surprise
if you compare `str(run_dir)` with what you expect.

**How to avoid:** For `fake_run.py`, use UUID4 (no slashes) as the default. Document
that slash-containing run-IDs create nested directories.

---

## Run-ID Generation Recommendation

[ASSUMED — Claude's discretion per CONTEXT.md]

Use `uuid.uuid4()` hex string as the default run-ID for `fake_run.py`. Rationale:
- No slashes → simple flat directory under `results/`
- Guaranteed unique → no collision in concurrent runs
- stdlib only (`import uuid`)
- `str(uuid.uuid4())` produces `"55219e4e-602b-4430-9ba0-8c6d637a823d"` — unambiguous

Allow `--run-id` CLI override for reproducible testing (re-run with same run-ID to
overwrite a previous fake run).

---

## `__init__.py` Exports Recommendation

[ASSUMED — Claude's discretion per CONTEXT.md]

Export everything a caller needs to implement `fake_run.py` without importing submodules:

```python
# lab_harness_runner/__init__.py
from lab_harness_runner.adapter import Adapter
from lab_harness_runner.task_reader import read_task
from lab_harness_runner.result_builder import build_result_dir
from lab_harness_runner.metrics import write_metrics
from lab_harness_runner.evaluator import score_run
from lab_harness_runner.adapter import TaskSpec, RunResult  # re-export models

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

Keep `TaskSpec` and `RunResult` in `adapter.py` (or a dedicated `models.py`). Either
location works; co-locating with `Adapter` is slightly cleaner since the Protocol
references both types.

**Do not add `py.typed`** for Phase 2 — it signals PEP 561 compliance (stub files or
inline annotations), which is unnecessary for an internal project not distributed on PyPI.

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from config.json — treated as enabled.

### Test Framework

No test infrastructure exists yet. For Phase 2, the primary validation is `fake_run.py`
itself (the D-12 exit criterion), not a formal test suite. However, unit tests for pure
functions are appropriate.

| Property | Value |
|----------|-------|
| Framework | `pytest` (recommended; add as dev dep) |
| Config file | none — Wave 0 gap |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-task-reader | `read_task` extracts fields from task.json correctly | unit | `uv run pytest tests/test_task_reader.py -x` | No — Wave 0 |
| REQ-deliverables | Deliverables extracted from `criteria[].deliverables`, not top-level dict | unit | `uv run pytest tests/test_task_reader.py::test_deliverable_extraction -x` | No — Wave 0 |
| REQ-result-builder | `build_result_dir` creates `output/` subdirectory | unit | `uv run pytest tests/test_result_builder.py -x` | No — Wave 0 |
| REQ-metrics | `write_metrics` produces valid metrics.json with safe defaults | unit | `uv run pytest tests/test_metrics.py -x` | No — Wave 0 |
| REQ-pre-validation | Missing deliverables raise `FileNotFoundError` before subprocess call | unit | `uv run pytest tests/test_evaluator.py::test_missing_deliverables -x` | No — Wave 0 |
| REQ-fake-run | `fake_run.py` exits 0, creates run dir, writes metrics.json | smoke | `uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/`
- **Phase gate:** All tests green + `fake_run.py` exits 0 without `--score` flag

### Wave 0 Gaps

- [ ] `tests/__init__.py` or `tests/conftest.py` — shared fixtures (tmp_path, sample task.json)
- [ ] `tests/test_task_reader.py` — covers REQ-task-reader, REQ-deliverables
- [ ] `tests/test_result_builder.py` — covers REQ-result-builder
- [ ] `tests/test_metrics.py` — covers REQ-metrics
- [ ] `tests/test_evaluator.py` — covers REQ-pre-validation (mock subprocess)
- [ ] Framework install: `uv add --dev pytest`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.13.5 | — |
| uv | Build + commands | ✓ | 0.11.8 | — |
| black | Formatting | ✗ | — | `uv add --dev black` (Wave 0 setup task) |
| pytest | Tests | ✗ | — | `uv add --dev pytest` (Wave 0 setup task) |
| Harvey LAB | Evaluator invocation | ✓ | live at ~/Projects/harvey-labs | — |
| `HARVEY_LAB_PATH` env var | LAB path resolution | not set (fallback used) | — | Path.home() / "Projects" / "harvey-labs" |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:**
- `black` — add as dev dep; code can be written first, formatted after
- `pytest` — add as dev dep; only needed for Wave 0 test files

---

## Security Domain

> This phase creates no network endpoints, handles no user input from external sources,
> and does not process secrets. ASVS categories V2/V3/V4 do not apply.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | partial | task_id and run_id must be safe relative paths (no `..` or absolute paths) |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via task_id | Tampering | Validate task_id contains no `..` or absolute path prefix (pattern from lab_probe.py `reject_unsafe_relative_path`) |
| Path traversal via run_id | Tampering | Same validation; run_id must be a safe relative path |

The `reject_unsafe_relative_path` pattern from `lab_probe.py` is the established
approach. `fake_run.py` should apply the same guard before passing task_id and
run_id to package functions.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | UUID4 hex string is the recommended run-ID format | Run-ID Generation | Low — any safe string works; only affects fake_run.py convenience |
| A2 | `__init__.py` should re-export all public symbols | `__init__.py` Exports | Low — internal project; callers can import submodules directly |
| A3 | `py.typed` should be omitted | `__init__.py` Exports | Negligible — not distributed on PyPI |
| A4 | `pytest` is the appropriate test framework | Validation Architecture | Low — any framework works; pytest is ecosystem standard |
| A5 | `uv_build` package name on PyPI maps to uv's official build backend | Package Legitimacy Audit | Low — confirmed by `uv init --package` generating this build-system block |

---

## Open Questions (RESOLVED)

1. **Does fake_run.py need a minimal valid DOCX for `.docx` deliverables?** RESOLVED: Yes — `write_minimal_docx` from `lab_probe.py` is copied into `fake_run.py` as a local helper. Default mode is no-score; `--score` requires proper DOCX.
   - What we know: The pre-score validation only checks file existence. The LAB
     evaluator reads file content when `--score` is invoked. For the D-12 exit
     criterion (without `--score`), plain text files suffice.
   - What's unclear: If `--score` is part of the exit demonstration, the fake `.docx`
     must be parseable by python-docx (the evaluator opens it). The `write_minimal_docx`
     function in `lab_probe.py` handles this.
   - Recommendation: Default `fake_run.py` to no-score mode for exit criterion. Document
     that `--score` requires proper DOCX files. Optionally copy `write_minimal_docx`
     from `lab_probe.py` into `fake_run.py` as a local helper.

2. **Should `score_run` in `evaluator.py` re-read task.json to get expected deliverables,
   or accept them as a parameter?** RESOLVED: Accept `expected_deliverables: list[str]` as a parameter — caller already has TaskSpec at call time, avoiding a redundant task.json read.
   - What we know: The pre-validation needs the expected deliverables list. Two sources:
     (a) re-read task.json, (b) accept `TaskSpec` or `expected_deliverables` as parameter.
   - What's unclear: Passing `TaskSpec` makes the API tighter; re-reading is independent.
   - Recommendation: Accept `expected_deliverables: list[str]` as a parameter to avoid
     re-reading task.json. Caller already has TaskSpec at this point.

---

## Sources

### Primary (HIGH confidence)

- `run_eval.py` (live source at `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py`) — evaluator CLI signature, required flags, metrics.json read pattern
- `scoring.py` (live source at `/Users/houfu/Projects/harvey-labs/evaluation/scoring.py`) — deliverable matching, output dir path (`run_dir / "output"`)
- `verified-contracts.md` (Phase 1 output) — task schema, result layout, evaluator command
- Live test: flat layout with `uv_build` + `module-root = ""` confirmed importable under uv 0.11.8
- `pyproject.toml` (project root) — existing black config, requires-python = ">=3.11"
- `CONTEXT.md` — all locked decisions D-01 through D-12

### Secondary (MEDIUM confidence)

- [https://docs.astral.sh/uv/concepts/projects/config/](https://docs.astral.sh/uv/concepts/projects/config/) — build-system requirement for package registration
- [https://docs.astral.sh/uv/reference/settings/#build-backend](https://docs.astral.sh/uv/reference/settings/#build-backend) — `module-root = ""` for flat layout
- `redlines/pyproject.toml` (same author, flat layout with hatchling) — established pattern for this user's flat layout projects

### Tertiary (LOW confidence)

- None — all material claims verified from live sources.

---

## Metadata

**Confidence breakdown:**

- Evaluator CLI contract: HIGH — verified from live run_eval.py source
- Package registration (flat layout): HIGH — verified by live uv 0.11.8 test
- metrics.json schema: HIGH — verified from live run_eval.py lines 137-152
- Deliverable extraction pattern: HIGH — verified from scoring.py + task.json inspection
- Run-ID format: HIGH — verified from results directory + run_eval.py source
- Test framework choice: LOW — assumed based on ecosystem standard

**Research date:** 2026-05-30
**Valid until:** 2026-06-30 (stable stdlib + locked decisions; re-verify if uv major version changes)
