# Phase 2: Build Harness-Neutral Package Core - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the Python package scaffold and all harness-agnostic abstractions — task
reader, result directory builder, RunResult + Adapter protocol, metrics writer,
and evaluator invocation wrapper — without any nanoclaw-specific code.

The exit criterion is a `scripts/fake_run.py` that creates a hand-crafted
output directory and drives the evaluator wrapper end-to-end.

</domain>

<decisions>
## Implementation Decisions

### Package Layout
- **D-01:** Flat layout — source package at `lab_harness_runner/` in the project
  root (not `src/lab_harness_runner/`).
- **D-02:** Flat module structure inside the package: `task_reader.py`,
  `result_builder.py`, `adapter.py`, `metrics.py`, `evaluator.py`. No
  sub-packages.

### Data Models
- **D-03:** Use `@dataclass` for `TaskSpec` and `RunResult`. No extra
  dependencies; attribute access; optional frozen/slots as needed.
- **D-04:** `TaskSpec` fields: `task_id: str`, `instructions: str`,
  `documents_dir: Path`, `expected_deliverables: list[str]`, `run_id: str`.
- **D-05:** `RunResult` fields: `run_id: str`, `end_state: str`,
  `wall_clock_seconds: float`, plus optional token/coverage fields with `None`
  defaults.
- **D-06:** `end_state` valid values are string literals `"clean"`,
  `"agent_error"`, `"timeout"` — documented in a comment, no Enum or Literal
  type alias.
- **D-07:** Adapter contract is a `typing.Protocol` (structural subtyping): any
  class with `run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult`
  qualifies. No explicit inheritance required.

### LAB Path Configuration
- **D-08:** Locate the Harvey LAB installation via `HARVEY_LAB_PATH` env var,
  with a fallback to `Path.home() / "Projects" / "harvey-labs"`.
- **D-09:** Results directory is always `<HARVEY_LAB_PATH>/results/<run-id>/`.
  No separate `RESULTS_ROOT` env var.

### Evaluator Invocation
- **D-10:** Invoke the evaluator via `subprocess.run(["uv", "run", "python",
  "-m", "evaluation.run_eval", ...], cwd=lab_path, check=True)`. No sys.path
  manipulation or direct import of LAB internals.
- **D-11:** Pre-score validation: before calling run_eval, check that every
  expected deliverable filename exists in `output/`. Raise `FileNotFoundError`
  listing missing files if any are absent.
- **D-12:** The Phase 2 exit criterion is `scripts/fake_run.py` — a standalone
  script that exercises the full wiring (TaskSpec → output dir → metrics.json →
  evaluator). Not a production adapter; not a test fixture inside the package.

### Claude's Discretion
- Run-ID generation strategy (UUID, timestamp-based, etc.) — Claude decides.
- Exact `__init__.py` exports — Claude decides based on what callers need.
- Whether to add `py.typed` marker for PEP 561 — Claude decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Harvey LAB Contracts (Phase 1 verified)
- `docs/verified-contracts.md` — Verified task schema, result layout, evaluator
  command, deliverable matching, and nanoclaw session/mount contracts.

### Harvey LAB Source (for evaluator command signature)
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py` — Evaluator entry
  point; line 26 (required fields), line 154 (command invocation), line 178
  (report generation).
- `/Users/houfu/Projects/harvey-labs/evaluation/scoring.py` — Deliverable
  matching logic; line 128, 315, 375.

### Project Spec
- `.planning/REQUIREMENTS.md` — Functional and quality requirements.
- `.planning/PROJECT.md` — Locked decisions (LAB as unmodified dep, uv/black,
  adapter contract shape, RunResult end-state taxonomy).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/lab_probe.py` — Phase 1 probe script. Contains working examples of
  reading `task.json`, building result directories, and invoking the evaluator
  CLI. Reference for field names and subprocess invocation pattern, but do not
  import it as a module.

### Established Patterns
- `pyproject.toml` already has `black` configured (`line-length = 88`) and
  `requires-python = ">=3.11"`. Format all new code with black; use Python 3.11+
  syntax (union types with `|`, `Path` from `pathlib`, etc.).
- `uv` is the project's package manager. Add dependencies via `uv add`, not
  `pip install`.

### Integration Points
- `lab_harness_runner/` package root will be importable after `uv` registers it.
  No `src/` prefix — `pyproject.toml` must declare `packages = [{include =
  "lab_harness_runner"}]` if uv doesn't auto-detect the flat layout.

</code_context>

<specifics>
## Specific Ideas

- The fake_run.py script should import from `lab_harness_runner` to prove the
  public API works, not call internal functions directly.
- The evaluator wrapper should pass `cwd=lab_path` to subprocess so that
  `evaluation.run_eval` resolves module imports relative to the LAB root.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Build Harness-Neutral Package Core*
*Context gathered: 2026-05-30*
