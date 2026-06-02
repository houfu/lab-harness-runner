# Phase 04: Completion, Metrics, Evaluation, And Scale-Out - Research

**Researched:** 2026-06-01 [VERIFIED: init.phase-op]  
**Domain:** Python benchmark orchestration for Harvey LAB result folders and the nanoclaw-lq adapter [VERIFIED: .planning/PROJECT.md]  
**Confidence:** HIGH for codebase/LAB contract findings; MEDIUM for live nanoclaw operational availability because daemon state was not probed [VERIFIED: codebase grep]

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Mixed Run Outcome Semantics
- **D-01:** The benchmark-facing result should be loose: if all expected
  deliverables exist and pass validation for scoring, the run can be treated as
  `clean` for benchmark/reporting purposes even when the adapter did not observe
  `STATUS:DONE`.
- **D-02:** Preserve diagnostic evidence separately. Planning should add fields
  such as `terminal_status_seen`, `raw_end_state`, `completion_signal`, or
  equivalent so adapter/protocol failures remain visible without failing a run
  whose end product can be evaluated.
- **D-03:** The rationale is pragmatic: this system depends on LAB, nanoclaw,
  Docker/OneCLI, and the model/container agent. Strange adapter/protocol failures
  should not invalidate a benchmark run if LAB can evaluate the produced output.

### Primary Command Shape
- **D-04:** Phase 4 should provide one primary workflow command with flags. The
  main path should not require users to manually chain run -> score -> report ->
  aggregate commands.
- **D-05:** The command should run the adapter, validate deliverables, write
  metrics, optionally invoke scoring/reporting, and preserve generated artifacts.
  Internal functions can remain composable, but the user-facing benchmark path is
  one command.
- **D-06:** A plausible script shape is:
  `uv run python scripts/run_benchmark.py --task <task> --adapter nanoclaw --nanoclaw-dir <path> --group-id <id> --score --report`.

### Batch And Variance Output
- **D-07:** Preserve LAB compatibility. Every run should continue to live under
  the Harvey LAB checkout at `results/<run-id>/`.
- **D-08:** Batch/variance reporting should add an aggregate summary that
  references normal LAB run IDs and paths instead of moving outputs into a new
  layout.
- **D-09:** The aggregate should include task, seed, adapter, deliverable
  validation status, benchmark-facing status, raw terminal/protocol status,
  score/report paths, and variance fields.
- **D-10:** Prefer `results/batches/<batch-id>/summary.json` for aggregate
  metadata only if it does not interfere with LAB evaluator assumptions. A flat
  `results/<batch-id>-aggregate.json` is acceptable if safer.

### Adapter Contract Documentation
- **D-11:** Target a practical adapter guide, not minimal notes and not polished
  public docs.
- **D-12:** The guide should include the interface contract, examples, failure
  semantics, deliverable validation behavior, metrics fields, benchmark-facing
  status vs raw/protocol status, and how to add a second adapter later.

### Carried Forward
- LAB remains an unmodified dependency.
- Package-owned code should remain harness-agnostic; adapter-specific logic
  belongs in adapter implementations or scripts.
- Existing `RunResult.end_state` has `clean`, `agent_error`, and `timeout`.
  Phase 4 may either preserve that raw state in a separate field or add reporting
  fields around it, but the user-facing benchmark status should be based on
  deliverable validation where possible.

### the agent's Discretion

No explicit `## the agent's Discretion` section exists in `04-CONTEXT.md`; implementation discretion is limited to the locked decisions above and the project constraints below. [VERIFIED: .planning/phases/04-completion-metrics-evaluation-and-scale-out/04-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

- Full public package documentation, tutorials, and contribution docs remain out
  of scope for this milestone.
- Additional adapters beyond nanoclaw-lq remain deferred until a real second
  harness needs one.
</user_constraints>

## Summary

Phase 4 should add a benchmark-status layer above the existing adapter `RunResult.end_state`, not replace the adapter state. [VERIFIED: lab_harness_runner/adapter.py] The observed Phase 3 proof run produced the expected deliverable while recording `end_state: "timeout"`, so the plan should report `benchmark_status: "clean"` only when deliverable validation passes, while preserving `raw_end_state`, `terminal_status_seen`, and `completion_signal` fields in metrics and aggregate summaries. [VERIFIED: .planning/phases/03-implement-nanoclaw-lq-adapter/03-03-SUMMARY.md]

The primary user-facing command should be a new benchmark workflow command that composes the existing functions `read_task`, `build_result_dir`, `NanoclawAdapter.run`, `write_metrics`, and `score_run`, then records report paths and aggregate metadata without moving LAB outputs. [VERIFIED: scripts/nanoclaw_run.py] Keep all run folders under the Harvey LAB `results/<run-id>/` tree because LAB scoring/reporting resolve `scores.json` and `report.html` from that layout. [CITED: docs/verified-contracts.md]

**Primary recommendation:** Build `scripts/run_benchmark.py` as the single command for single-task and batch runs, write per-run enriched `metrics.json`, preserve LAB `scores.json` and `report.html`, and write batch-only metadata at `results/batches/<batch-id>/summary.json` if that path does not introduce LAB comparison noise. [VERIFIED: .planning/phases/04-completion-metrics-evaluation-and-scale-out/04-CONTEXT.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Adapter execution | Adapter implementation | Benchmark CLI | `NanoclawAdapter.run()` owns nanoclaw dispatch, mounts, polling, timeout, and raw `RunResult`. [VERIFIED: lab_harness_runner/nanoclaw_adapter.py] |
| Benchmark-facing status | Benchmark CLI / package orchestration | Metrics writer | Deliverable validation and raw adapter state must be combined after adapter return and before scoring. [VERIFIED: lab_harness_runner/evaluator.py] |
| LAB scoring/reporting | Harvey LAB dependency | Evaluator wrapper | `evaluation.run_eval` writes `scores.json` and calls report generation; this project should invoke, not replace it. [CITED: docs/verified-contracts.md] |
| Batch aggregation and variance | Benchmark CLI / aggregation module | LAB result folders | Aggregate metadata should reference LAB run IDs and paths while per-run artifacts remain in `results/<run-id>/`. [VERIFIED: 04-CONTEXT.md] |
| Adapter guide | Project docs | Adapter protocol | The public extension point is `run(task_spec, output_dir) -> RunResult`. [VERIFIED: lab_harness_runner/adapter.py] |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-09 | Wait for terminal `STATUS:` signal; Phase 4 must handle missing signal with valid deliverables. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Preserve `raw_end_state` and explicit terminal/protocol fields while deriving benchmark status from deliverable validation. [VERIFIED: 04-CONTEXT.md] |
| REQ-14 | Preserve LAB-generated reports and dashboards. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | `score_run` returns `scores.json`; LAB `run_eval` generates `report.html`; compare dashboards are separate LAB commands. [CITED: docs/verified-contracts.md] |
| REQ-15 | Support multi-task and multi-seed runs. [VERIFIED: .planning/REQUIREMENTS.md] | Add task/seed iteration around the existing single-run flow and store aggregate metadata without changing per-run folders. [VERIFIED: scripts/nanoclaw_run.py] |
| REQ-16 | Document how third-party harnesses implement the adapter contract. [VERIFIED: .planning/REQUIREMENTS.md] | Write a practical adapter guide covering `TaskSpec`, `RunResult`, raw vs benchmark status, deliverables, metrics, and future adapter registration. [VERIFIED: lab_harness_runner/adapter.py] |
| REQ-21 | Present benchmark results as whole agent-system outcomes. [VERIFIED: .planning/v1.0-MILESTONE-AUDIT.md] | Aggregate rows must include adapter, harness, status, score, cost/timing, document coverage, and protocol evidence. [VERIFIED: docs/verified-contracts.md] |
| REQ-22 | Report variance before multi-task performance claims. [VERIFIED: .planning/REQUIREMENTS.md] | Batch summaries should include count, mean, min, max, sample standard deviation, and per-seed rows for score, wall clock, token counts, and document coverage where available. [ASSUMED] |
</phase_requirements>

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Python | 3.13.5 available; project requires `>=3.11` [VERIFIED: python3 --version; pyproject.toml] | CLI orchestration, JSON summaries, subprocess invocation | Existing package and scripts are Python. [VERIFIED: scripts/nanoclaw_run.py] |
| `uv` | 0.11.8 [VERIFIED: uv --version] | Run project commands and LAB evaluator commands | Project command convention is `uv run ...`. [VERIFIED: .planning/PROJECT.md] |
| pytest | 9.0.3 dependency spec [VERIFIED: pyproject.toml] | Unit and integration-harness tests | Existing suite uses pytest and currently passes. [VERIFIED: `uv run pytest tests/ -q`] |
| black | `>=26.5.1` dev dependency [VERIFIED: pyproject.toml] | Formatting | Project locked decision says use black. [VERIFIED: .planning/PROJECT.md] |
| stdlib `argparse`, `json`, `pathlib`, `statistics`, `subprocess`, `uuid` | Python stdlib [VERIFIED: codebase imports] | CLI flags, metadata files, path handling, variance, external process calls, run IDs | No external package is required for Phase 4 orchestration. [VERIFIED: pyproject.toml] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| Docker | 29.5.2 available [VERIFIED: docker --version] | nanoclaw container runtime dependency | Needed for live nanoclaw runs, not for unit tests. [VERIFIED: .planning/PROJECT.md] |
| Harvey LAB checkout | Present at `/Users/houfu/Projects/harvey-labs` [VERIFIED: filesystem probe] | Source tasks, result folders, evaluator, reports | Required for actual benchmark runs and scoring. [CITED: docs/verified-contracts.md] |
| nanoclaw-lq checkout | Present at `/Users/houfu/Projects/nanoclaw-lq` [VERIFIED: filesystem probe] | First adapter runtime | Required for `--adapter nanoclaw`. [VERIFIED: .planning/PROJECT.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `results/batches/<batch-id>/summary.json` | `results/<batch-id>-aggregate.json` | Nested `results/batches` is cleaner, but a flat file avoids accidental discovery by LAB `rglob("scores.json")`; use nested only for metadata files and never write `scores.json` inside batch folders. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/compare.py] |
| New external CLI framework | stdlib `argparse` | Existing scripts use `argparse`; no package install or slopcheck gate is needed. [VERIFIED: scripts/nanoclaw_run.py] |
| Replacing LAB reports | Preserve LAB `scores.json`, `report.html`, and optional compare outputs | LAB remains source of scoring and reporting. [VERIFIED: .planning/PROJECT.md] |

**Installation:** No new external packages are recommended for Phase 4. [VERIFIED: pyproject.toml]

```bash
# No install command required.
uv run pytest tests/ -q
```

## Package Legitimacy Audit

No external packages are recommended or installed in this phase, so the Package Legitimacy Gate is not applicable. [VERIFIED: Standard Stack]

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| None | - | - | - | - | - | No install required. [VERIFIED: pyproject.toml] |

**Packages removed due to slopcheck [SLOP] verdict:** none. [VERIFIED: no new packages]  
**Packages flagged as suspicious [SUS]:** none. [VERIFIED: no new packages]

## Architecture Patterns

### System Architecture Diagram

```text
User CLI flags
  --task/--tasks, --seeds, --adapter, --score, --report
        |
        v
scripts/run_benchmark.py
        |
        +--> expand task x seed matrix
        |
        v
Per-run flow
  read_task() -> build_result_dir()
        |
        v
  Adapter.run(task_spec, output_dir)
        |
        +--> nanoclaw dispatch/mounts/poll/timeout
        |       returns raw RunResult(end_state)
        |
        v
  validate expected deliverables in output/
        |
        +--> missing deliverables -> benchmark_status="error"
        +--> present deliverables + raw timeout -> benchmark_status="clean", raw_end_state="timeout"
        |
        v
  write metrics.json with LAB fields + diagnostic extension fields
        |
        v
  optional score_run() -> LAB evaluation.run_eval
        |
        +--> scores.json
        +--> report.html
        |
        v
Batch summary
  results/batches/<batch-id>/summary.json
  references run_id, paths, score/report artifacts, statuses, variance fields
```

### Recommended Project Structure

```text
lab_harness_runner/
|-- adapter.py              # existing TaskSpec, RunResult, Adapter protocol
|-- metrics.py              # extend writer or add helper for diagnostic fields
|-- evaluator.py            # existing score_run() pre-score validation and LAB invocation
`-- aggregation.py          # new batch summary and variance helpers

scripts/
|-- run_benchmark.py        # new primary single/batch command
|-- nanoclaw_run.py         # keep as narrow compatibility/dev script or delegate to run_benchmark
`-- fake_run.py             # keep as wiring proof

docs/
`-- adapter-guide.md        # new practical adapter implementation guide
```

### Pattern 1: Layer Benchmark Status Over Raw Adapter State

**What:** Keep `RunResult.end_state` as the raw adapter observation and derive separate benchmark-facing fields after deliverable validation. [VERIFIED: lab_harness_runner/adapter.py]  
**When to use:** Use this for every run before scoring so Phase 3 timeout-with-valid-output is represented honestly. [VERIFIED: 03-03-SUMMARY.md]  
**Example:**

```python
# Source: 04-CONTEXT.md and lab_harness_runner/evaluator.py
missing = [
    name
    for name in task_spec.expected_deliverables
    if not (output_dir / name).exists()
]
deliverables_valid = not missing
raw_end_state = result.end_state

benchmark_status = (
    "clean"
    if deliverables_valid
    else "error" if raw_end_state != "timeout" else "timeout"
)
diagnostics = {
    "benchmark_status": benchmark_status,
    "raw_end_state": raw_end_state,
    "terminal_status_seen": raw_end_state != "timeout",
    "completion_signal": "STATUS:DONE" if raw_end_state == "clean" else None,
    "expected_deliverables_present": deliverables_valid,
    "missing_deliverables": missing,
}
```

### Pattern 2: One Primary Command, Composable Internals

**What:** `scripts/run_benchmark.py` should be the benchmark entry point and should call existing package functions instead of duplicating task/result/evaluator logic. [VERIFIED: scripts/nanoclaw_run.py]  
**When to use:** Use for both single-task and multi-task/multi-seed execution. [VERIFIED: 04-CONTEXT.md]  
**Example command:**

```bash
uv run python scripts/run_benchmark.py \
  --task corporate-ma/compare-matter-plan-against-engagement-letter \
  --adapter nanoclaw \
  --nanoclaw-dir /Users/houfu/Projects/nanoclaw-lq \
  --group-id lab-runner \
  --score \
  --report
```

### Pattern 3: Batch Summary References LAB Artifacts

**What:** Store batch metadata outside individual run folders but keep each run in `results/<run-id>/`. [VERIFIED: 04-CONTEXT.md]  
**When to use:** Use for task/seed sweeps and variance reporting. [VERIFIED: .planning/REQUIREMENTS.md]  
**Required fields:** `batch_id`, `task_id`, `seed`, `adapter`, `run_id`, `run_dir`, `output_dir`, `metrics_path`, `scores_path`, `report_path`, `benchmark_status`, `raw_end_state`, `terminal_status_seen`, `expected_deliverables_present`, `missing_deliverables`, `score`, `all_pass`, `wall_clock_seconds`, `input_tokens`, `output_tokens`, `documents_read`, `total_vdr_files`. [VERIFIED: run_eval.py and compare.py; ASSUMED for seed field semantics]

### Anti-Patterns to Avoid

- **Rewriting `RunResult.end_state` from `timeout` to `clean`:** This destroys protocol evidence from the adapter layer. [VERIFIED: 03-UAT.md]
- **Moving scored runs out of LAB `results/<run-id>/`:** LAB report and compare code scan the LAB results tree. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/report.py]
- **Writing aggregate `scores.json` files under batch folders:** LAB comparison scans `RESULTS_DIR.rglob("scores.json")`, so fake aggregate score files can pollute dashboard inputs. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/compare.py]
- **Making package core depend on nanoclaw-only concepts:** Adapter-specific config must stay in adapter implementations or scripts. [VERIFIED: .planning/PROJECT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LAB scoring | Custom rubric scorer | LAB `evaluation.run_eval` via `score_run()` | LAB is the locked source of scoring and writes `scores.json`. [CITED: docs/verified-contracts.md] |
| Per-run report | Custom HTML report | LAB `evaluation.report` generated by `run_eval` | LAB report writes `results/<run-id>/report.html`. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/report.py] |
| Dashboard comparison | Custom comparison dashboard | LAB `evaluation.compare` commands where needed | LAB already has task/area/all comparison commands. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/compare.py] |
| Path validation | Ad hoc string checks | Existing `_reject_unsafe_relative_path()` | Current readers/evaluator use this helper for task IDs and run IDs. [VERIFIED: lab_harness_runner/task_reader.py] |
| Adapter protocol | Harness-specific abstract base | Existing structural `Adapter` Protocol | The interface is already `run(task_spec, output_dir) -> RunResult`. [VERIFIED: lab_harness_runner/adapter.py] |
| Variance math | Unreviewed formulas inline everywhere | stdlib `statistics` in a single aggregation helper | One helper can define sample count, mean, min, max, and standard deviation consistently. [ASSUMED] |

**Key insight:** Phase 4 should compose existing verified surfaces; the new behavior is orchestration and reporting semantics, not a replacement evaluator or a second harness runtime. [VERIFIED: .planning/PROJECT.md]

## Common Pitfalls

### Pitfall 1: Collapsing Raw And Benchmark Status

**What goes wrong:** A run with valid deliverables but no `STATUS:DONE` is reported only as `clean`, hiding a protocol failure. [VERIFIED: 03-UAT.md]  
**Why it happens:** The old `metrics.json` has a single `end_state` field. [VERIFIED: lab_harness_runner/metrics.py]  
**How to avoid:** Write `end_state`/`raw_end_state` plus `benchmark_status`, `terminal_status_seen`, `completion_signal`, and deliverable validation fields. [VERIFIED: 04-CONTEXT.md]  
**Warning signs:** Batch summaries cannot distinguish adapter timeout from missing deliverables. [ASSUMED]

### Pitfall 2: Scoring Before Deliverable Validation

**What goes wrong:** The LAB evaluator may spend judge calls or fail later when expected files are absent. [VERIFIED: lab_harness_runner/evaluator.py]  
**Why it happens:** The CLI runs `score_run` without exposing validation state in metrics. [VERIFIED: scripts/nanoclaw_run.py]  
**How to avoid:** Run the same output-dir deliverable check before writing final status fields, and let `score_run` remain the enforcement gate. [VERIFIED: lab_harness_runner/evaluator.py]  
**Warning signs:** `metrics.json` lacks `missing_deliverables` even though scoring failed with `FileNotFoundError`. [ASSUMED]

### Pitfall 3: Batch Metadata Pollutes LAB Compare

**What goes wrong:** Aggregate files are mistaken for LAB runs. [VERIFIED: compare.py scans `scores.json`]  
**Why it happens:** LAB comparison recursively scans `results/**/scores.json`. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/compare.py]  
**How to avoid:** Store batch metadata as `summary.json`, never `scores.json`, and do not fabricate per-batch `config.json`. [VERIFIED: compare.py behavior]  
**Warning signs:** LAB compare dashboards show a non-run or duplicate batch entry. [ASSUMED]

### Pitfall 4: Multi-Seed Without Real Seed Semantics

**What goes wrong:** Reports imply controlled randomness when the adapter/model path may not accept a seed. [ASSUMED]  
**Why it happens:** Phase 4 requires multi-seed loops, but the existing nanoclaw script has no `--seed` flag and `RunResult` has no seed field. [VERIFIED: scripts/nanoclaw_run.py]  
**How to avoid:** Treat `seed` as run metadata and run-id suffix unless a future adapter explicitly supports deterministic seed injection. [ASSUMED]  
**Warning signs:** Docs claim reproducibility without verifying adapter/model seed support. [ASSUMED]

### Pitfall 5: Adapter Guide Overfits Nanoclaw

**What goes wrong:** Future adapters inherit nanoclaw-specific concepts like outbound SQLite or Docker mounts as core requirements. [VERIFIED: lab_harness_runner/nanoclaw_adapter.py]  
**Why it happens:** nanoclaw is the only implemented adapter. [VERIFIED: .planning/PROJECT.md]  
**How to avoid:** Document the required protocol in terms of `TaskSpec`, output directory, deliverables, `RunResult`, metrics, and failure semantics; keep nanoclaw as an example section. [VERIFIED: lab_harness_runner/adapter.py]  
**Warning signs:** Guide says every adapter must emit `STATUS:` instead of saying adapters must return raw end-state evidence. [ASSUMED]

## Code Examples

### Primary Command Single-Run Skeleton

```python
# Source: scripts/nanoclaw_run.py
task_spec = read_task(lab_path=lab_path, task_id=task_id, run_id=run_id)
run_dir, output_dir = build_result_dir(lab_path=lab_path, run_id=run_id)
result = adapter.run(task_spec=task_spec, output_dir=output_dir)

# New Phase 4 step: derive benchmark status before scoring.
status = derive_benchmark_status(task_spec, output_dir, result)
write_metrics(run_dir=run_dir, result=result, extra_fields=status)

scores_path = None
report_path = None
if score:
    scores_path = score_run(
        lab_path=lab_path,
        run_id=run_id,
        task_id=task_id,
        expected_deliverables=task_spec.expected_deliverables,
        judge_model=judge_model,
    )
    report_path = run_dir / "report.html"
```

### Batch Variance Shape

```python
# Source: stdlib statistics pattern; fields from run_eval.py scores/metrics usage
from statistics import mean, stdev

def summarize(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": mean(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "stdev": stdev(values) if len(values) > 1 else 0.0,
    }
```

### Adapter Guide Contract Example

```python
# Source: lab_harness_runner/adapter.py
class MyAdapter:
    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        # Write every expected deliverable under output_dir.
        # Return raw harness state; do not convert artifact success into protocol success here.
        return RunResult(
            run_id=task_spec.run_id,
            end_state="clean",
            wall_clock_seconds=elapsed,
            input_tokens=None,
            output_tokens=None,
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `end_state` carries both protocol and benchmark meaning | Raw adapter state plus benchmark-facing status and deliverable validation evidence | Phase 4 locked decision after Phase 3 UAT on 2026-06-01 [VERIFIED: 04-CONTEXT.md] | Valid outputs can score cleanly while protocol failures remain diagnosable. [VERIFIED: 03-UAT.md] |
| Single-task `scripts/nanoclaw_run.py` | One primary command with task/seed loops, scoring/report flags, and aggregation | Phase 4 scope [VERIFIED: .planning/ROADMAP.md] | Users should not manually chain run, score, report, and aggregate. [VERIFIED: 04-CONTEXT.md] |
| Per-run only reporting | Per-run LAB artifacts plus batch summary/variance metadata | Phase 4 scope [VERIFIED: .planning/REQUIREMENTS.md] | Benchmark claims can cite variance across repeated runs. [VERIFIED: .planning/REQUIREMENTS.md] |

**Deprecated/outdated:**
- Treating `end_state == "timeout"` as automatic benchmark failure when expected deliverables validate is deprecated by Phase 4 D-01. [VERIFIED: 04-CONTEXT.md]
- Hand-running separate benchmark steps is outdated for the primary path; Phase 4 requires one command with flags. [VERIFIED: 04-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Variance summaries should include count, mean, min, max, sample standard deviation, and per-seed rows for score, wall clock, token counts, and document coverage. | Phase Requirements / Don't Hand-Roll / Code Examples | Planner may choose variance fields that do not satisfy stakeholder expectations. |
| A2 | `seed` should be treated as run metadata and run-id suffix unless an adapter explicitly supports deterministic seed injection. | Common Pitfalls | Multi-seed results could be overclaimed as deterministic reproducibility. |
| A3 | Batch warning signs such as dashboard pollution and missing-deliverable diagnostics are inferred from LAB scan behavior and current script gaps. | Common Pitfalls | Planner may need additional tests to validate warning signs. |

## Open Questions (RESOLVED)

1. **Should Phase 4 call LAB comparison dashboards automatically?**
   - What we know: LAB provides `evaluation.compare --task`, `--area`, and `--all`. [VERIFIED: /Users/houfu/Projects/harvey-labs/evaluation/compare.py]
   - Resolution: Dashboards are in Phase 4 scope as optional LAB compare/dashboard preservation through the primary benchmark command. The planned command should expose `--compare task|area|all` or an equivalent explicit flag that invokes LAB's existing comparison flow after scoring, records generated dashboard artifact paths in command output and aggregate metadata, and never moves per-run LAB result folders. Per-run `scores.json` and `report.html` remain the default preserved artifacts; compare/dashboard generation is opt-in because it depends on scored runs and LAB's result tree state. [VERIFIED: 04-CONTEXT.md; docs/verified-contracts.md]

2. **How should deterministic seed support be exposed?**
   - What we know: Existing scripts do not expose a seed flag to nanoclaw. [VERIFIED: scripts/nanoclaw_run.py]
   - Resolution: Deterministic seeds are represented as benchmark metadata and iteration identifiers where adapters cannot force model determinism. The multi-seed loop should record `seed` in metrics/aggregate rows and may use it in run-id suffixes for traceability, but docs and summaries must not claim deterministic reproducibility unless a specific adapter implements and verifies seed injection. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | CLI and tests | yes [VERIFIED: python3 --version] | 3.13.5 | Project requires `>=3.11`; no fallback needed. [VERIFIED: pyproject.toml] |
| `uv` | Project/LAB commands | yes [VERIFIED: uv --version] | 0.11.8 | None; locked project command convention. [VERIFIED: .planning/PROJECT.md] |
| pytest | Validation | yes [VERIFIED: `uv run pytest tests/ -q`] | 9.0.3 spec | None needed. [VERIFIED: pyproject.toml] |
| Docker | live nanoclaw execution | yes [VERIFIED: docker --version] | 29.5.2 | Unit tests can mock adapter, but live nanoclaw benchmark has no fallback. [VERIFIED: .planning/PROJECT.md] |
| Harvey LAB checkout | scoring/reporting | yes [VERIFIED: filesystem probe] | local checkout | No fallback; LAB is locked dependency. [VERIFIED: .planning/PROJECT.md] |
| nanoclaw-lq checkout | nanoclaw adapter | yes [VERIFIED: filesystem probe] | local checkout | Fake adapter can test orchestration; live nanoclaw run has no fallback. [VERIFIED: scripts/fake_run.py] |
| nanoclaw daemon / OneCLI runtime | live nanoclaw run | not probed [ASSUMED] | - | Planner should include manual/live checkpoint before e2e benchmark. [VERIFIED: 03-VALIDATION.md] |
| LAB judge API credentials | live scoring | not probed [ASSUMED] | - | Planner should allow `--no-score` / dry run and separate live scoring checkpoint. [CITED: docs/verified-contracts.md] |

**Missing dependencies with no fallback:**
- Live nanoclaw daemon state and judge credentials were not probed during research; live benchmark/scoring plans need checkpoints. [ASSUMED]

**Missing dependencies with fallback:**
- Live nanoclaw and judge calls can be bypassed for unit tests using fake/mocked adapters and `--no-score`. [VERIFIED: scripts/fake_run.py]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 dependency spec [VERIFIED: pyproject.toml] |
| Config file | `pyproject.toml`; `tests/conftest.py` exists [VERIFIED: filesystem grep] |
| Quick run command | `uv run pytest tests/test_metrics.py tests/test_evaluator.py -q` [VERIFIED: existing files] |
| Full suite command | `uv run pytest tests/ -q` [VERIFIED: 53 passed in 0.71s] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REQ-09 | Raw timeout/protocol evidence is preserved while benchmark status can be clean when deliverables validate. [VERIFIED: 04-CONTEXT.md] | unit | `uv run pytest tests/test_metrics.py::test_write_metrics_preserves_raw_and_benchmark_status -x` | no; Wave 0 needed [VERIFIED: tests list] |
| REQ-14 | Scoring preserves `scores.json` and `report.html` paths. [VERIFIED: run_eval.py] | unit/integration mock | `uv run pytest tests/test_evaluator.py::test_score_run_returns_scores_json_path -x` plus new report-path assertion | partial; Wave 0 needed for report assertion [VERIFIED: tests/test_evaluator.py] |
| REQ-15 | Multi-task/multi-seed command writes per-run folders and batch summary rows. [VERIFIED: .planning/REQUIREMENTS.md] | unit/CLI smoke | `uv run pytest tests/test_run_benchmark.py -q` | no; Wave 0 needed [VERIFIED: tests list] |
| REQ-16 | Adapter guide documents required contract and failure semantics. [VERIFIED: .planning/REQUIREMENTS.md] | doc check | `test -s docs/adapter-guide.md` | no; Wave 0 needed [VERIFIED: docs list] |
| REQ-21 | Aggregate rows report whole agent-system outcomes. [VERIFIED: .planning/REQUIREMENTS.md] | unit | `uv run pytest tests/test_aggregation.py::test_summary_contains_whole_system_fields -x` | no; Wave 0 needed [VERIFIED: tests list] |
| REQ-22 | Variance fields are present before performance claims. [VERIFIED: .planning/REQUIREMENTS.md] | unit | `uv run pytest tests/test_aggregation.py::test_variance_fields_for_repeated_runs -x` | no; Wave 0 needed [VERIFIED: tests list] |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_metrics.py tests/test_evaluator.py -q` for metrics/evaluator changes, or targeted new test file for CLI/aggregation/docs. [ASSUMED]
- **Per wave merge:** `uv run pytest tests/ -q`. [VERIFIED: existing suite]
- **Phase gate:** full suite green plus a dry-run/fake batch command and one documented live nanoclaw checkpoint if environment is available. [ASSUMED]

### Wave 0 Gaps

- [ ] `tests/test_metrics.py` additions for `benchmark_status`, `raw_end_state`, `terminal_status_seen`, `completion_signal`, `expected_deliverables_present`, and `missing_deliverables`. [VERIFIED: tests/test_metrics.py lacks fields]
- [ ] `tests/test_aggregation.py` for summary rows, artifact paths, and variance fields. [VERIFIED: tests list]
- [ ] `tests/test_run_benchmark.py` for CLI argument expansion and fake/mocked adapter execution. [VERIFIED: tests list]
- [ ] `docs/adapter-guide.md` doc existence/content checks for interface, failure semantics, deliverable validation, metrics fields, and future adapter compatibility. [VERIFIED: docs list]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth feature is introduced; live judge credentials remain LAB environment concern. [ASSUMED] |
| V3 Session Management | no | No web/session feature is introduced. [VERIFIED: .planning/PROJECT.md] |
| V4 Access Control | yes | Preserve safe relative path validation for task IDs, run IDs, and group IDs. [VERIFIED: lab_harness_runner/task_reader.py] |
| V5 Input Validation | yes | Validate CLI task/run/group paths with existing helper and validate deliverables before scoring. [VERIFIED: lab_harness_runner/evaluator.py] |
| V6 Cryptography | no | No cryptography feature is introduced. [VERIFIED: phase scope] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through `--task`, `--run-id`, or batch metadata | Tampering / Information disclosure | Use `_reject_unsafe_relative_path()` before filesystem joins. [VERIFIED: lab_harness_runner/task_reader.py] |
| Shell injection through subprocess commands | Tampering / Execution | Use list-form `subprocess.run(..., shell=False default, cwd=..., check=True)`. [VERIFIED: lab_harness_runner/evaluator.py] |
| Misleading benchmark report after adapter/protocol timeout | Repudiation | Preserve raw protocol fields alongside benchmark status. [VERIFIED: 04-CONTEXT.md] |
| Accidental scoring of aggregate files | Tampering | Never write aggregate `scores.json`; use `summary.json`. [VERIFIED: compare.py scans `scores.json`] |

## Sources

### Primary (HIGH confidence)

- `.planning/PROJECT.md` - project scope, locked decisions, runtime/tooling. [VERIFIED: file read]
- `.planning/REQUIREMENTS.md` - Phase 4 functional and quality requirements. [VERIFIED: file read]
- `.planning/ROADMAP.md` - Phase 4 deliverables and exit criteria. [VERIFIED: file read]
- `.planning/v1.0-MILESTONE-AUDIT.md` - unsatisfied Phase 4 requirements and blockers. [VERIFIED: file read]
- `.planning/phases/04-completion-metrics-evaluation-and-scale-out/04-CONTEXT.md` - locked Phase 4 decisions. [VERIFIED: file read]
- `.planning/phases/03-implement-nanoclaw-lq-adapter/03-03-SUMMARY.md`, `03-UAT.md`, `03-VALIDATION.md` - Phase 3 timeout/deliverable evidence and validation state. [VERIFIED: file read]
- `lab_harness_runner/adapter.py`, `metrics.py`, `evaluator.py`, `nanoclaw_adapter.py`, `task_reader.py`, `result_builder.py` - existing package contracts. [VERIFIED: codebase grep]
- `scripts/nanoclaw_run.py`, `scripts/fake_run.py` - current CLI orchestration patterns. [VERIFIED: codebase grep]
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py`, `report.py`, `compare.py` - LAB scoring/reporting/dashboard behavior. [VERIFIED: local dependency source]

### Secondary (MEDIUM confidence)

- `docs/verified-contracts.md` - verified LAB/nanoclaw contract notes from Phase 1. [CITED: docs/verified-contracts.md]
- `/Users/houfu/Projects/harvey-labs/docs/architecture.md` - LAB architecture and command references. [CITED: local LAB docs]

### Tertiary (LOW confidence)

- Deterministic seed semantics for nanoclaw/model execution were not verified and must be treated as metadata-only unless implementation proves adapter support. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - local project files and command probes verify Python, uv, pytest, Docker, LAB, and nanoclaw availability. [VERIFIED: command probes]
- Architecture: HIGH - based on current package scripts, LAB local source, and locked Phase 4 decisions. [VERIFIED: codebase grep]
- Pitfalls: MEDIUM - core pitfalls are verified from Phase 3/LAB behavior; seed determinism and warning signs are assumptions requiring planner caution. [VERIFIED: 03-UAT.md; ASSUMED]

**Research date:** 2026-06-01 [VERIFIED: environment_context]  
**Valid until:** 2026-06-08 for live LAB/nanoclaw operational details; 2026-07-01 for package-internal architecture if dependencies remain unchanged. [ASSUMED]
