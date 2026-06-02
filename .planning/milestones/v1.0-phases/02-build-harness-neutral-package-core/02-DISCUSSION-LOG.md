# Phase 2: Build Harness-Neutral Package Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 02-build-harness-neutral-package-core
**Areas discussed:** Package layout, Data model approach, LAB path config, Evaluator invocation

---

## Package Layout

| Option | Description | Selected |
|--------|-------------|----------|
| src/ layout | src/lab_harness_runner/ — modern Python best practice, prevents accidental root imports | |
| Flat layout | lab_harness_runner/ at project root — simpler, no src/ prefix | ✓ |

**User's choice:** Flat layout

**Follow-up — Module organization:**

| Option | Description | Selected |
|--------|-------------|----------|
| Flat modules | One file per concern: task_reader.py, result_builder.py, adapter.py, metrics.py, evaluator.py | ✓ |
| Sub-packages | Group into lab/, core/, adapters/ sub-packages | |

**User's choice:** Flat modules

---

## Data Model Approach

| Option | Description | Selected |
|--------|-------------|----------|
| @dataclass | Pure Python, no extra deps, attribute access | ✓ |
| TypedDict | Pure dict at runtime, type hints only | |
| Pydantic | Validation + serialization, adds a dependency | |

**User's choice:** @dataclass (Recommended)

**Follow-up — Adapter Protocol:**

| Option | Description | Selected |
|--------|-------------|----------|
| typing.Protocol | Structural subtyping — any class with the right signature qualifies | ✓ |
| ABC | Explicit inheritance required | |

**User's choice:** typing.Protocol (Recommended)

**Follow-up — end_state values:**

| Option | Description | Selected |
|--------|-------------|----------|
| String literals | "clean", "agent_error", "timeout" documented in a comment | ✓ |
| Literal type alias | EndState = Literal["clean", "agent_error", "timeout"] | |
| Enum | class EndState(str, Enum) | |

**User's choice:** String literals (Recommended)

---

## LAB Path Config

| Option | Description | Selected |
|--------|-------------|----------|
| Env var | HARVEY_LAB_PATH with ~/Projects/harvey-labs fallback | ✓ |
| Constructor parameter | Pass lab_path at call site | |
| Config file | [tool.lab-harness-runner] or .env | |

**User's choice:** Env var (Recommended)

**Follow-up — Results directory:**

| Option | Description | Selected |
|--------|-------------|----------|
| Always inside LAB | results/<run-id>/ always under HARVEY_LAB_PATH | ✓ |
| Separate RESULTS_ROOT | Second env var for output location | |

**User's choice:** Always inside LAB (Recommended)

---

## Evaluator Invocation

| Option | Description | Selected |
|--------|-------------|----------|
| subprocess | uv run python -m evaluation.run_eval ... — clean subprocess, no LAB coupling | ✓ |
| Python import | sys.path + direct import of evaluation.run_eval | |

**User's choice:** subprocess (Recommended)

**Follow-up — Pre-score validation:**

| Option | Description | Selected |
|--------|-------------|----------|
| Check deliverables first | Validate expected filenames exist before calling run_eval | ✓ |
| Let run_eval handle it | LAB's matching logic handles missing deliverables | |

**User's choice:** Yes — check deliverables first (Recommended)

**Follow-up — Fake adapter for exit criterion:**

| Option | Description | Selected |
|--------|-------------|----------|
| Test script in scripts/ | scripts/fake_run.py — standalone script, manually runnable | ✓ |
| In-package FakeAdapter | FakeAdapter class in adapter.py satisfying the Protocol | |

**User's choice:** Test script in scripts/ (Recommended)

---

## Claude's Discretion

- Run-ID generation strategy (UUID, timestamp-based, etc.)
- Exact `__init__.py` exports
- Whether to add `py.typed` marker for PEP 561

## Deferred Ideas

None — discussion stayed within phase scope.
