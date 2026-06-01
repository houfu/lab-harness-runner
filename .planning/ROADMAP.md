# Roadmap

## Phase 1: Verify External Contracts And Scoring Pipeline

Status: complete (2026-05-30)

Goal: Confirm the live LAB and nanoclaw-lq surfaces, then prove LAB scoring with
a manually created result output.

Deliverables:

- Verified notes for LAB `task.json`, instructions handling, result directory
  layout, evaluator CLI, and report generation commands.

- Verified notes for nanoclaw group mounts, inbound/outbound database schemas,
  token metrics availability, and briefing location.

- A hand-made `results/<run-id>/output/` for one simple LAB task.
- A successful LAB evaluator run that writes `scores.json`.

Exit Criteria:

- The project has a known-good result layout and evaluator command.
- Unknowns from the implementation brief are either confirmed or converted into
  explicit follow-up work.

## Phase 2: Build Harness-Neutral Package Core

Status: planned

Goal: Create the package lifecycle and contracts without binding package-owned
code to nanoclaw.

Deliverables:

- Python project scaffold using `uv` and `black`.
- Task reader that builds `TaskSpec`.
- Result directory builder for `results/<run-id>/output/`.
- `RunResult` and adapter protocol definitions.
- Metrics writer with safe defaults.
- Evaluator invocation wrapper for LAB.

Exit Criteria:

- A fake adapter can produce a LAB-compatible run directory and invoke scoring.

**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Package scaffold: pyproject.toml build-system config, adapter.py (TaskSpec, RunResult, Adapter Protocol), __init__.py public exports

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — File I/O modules: task_reader.py (read_task) and result_builder.py (build_result_dir)
- [x] 02-03-PLAN.md — Pipeline modules: metrics.py (write_metrics) and evaluator.py (score_run with pre-validation)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-04-PLAN.md — Unit test suite: conftest.py fixtures, test_task_reader, test_result_builder, test_metrics, test_evaluator

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 02-05-PLAN.md — Exit criterion: scripts/fake_run.py end-to-end wiring proof

## Phase 3: Implement Nanoclaw-LQ Adapter

Status: complete (2026-06-01)

Goal: Run one LAB task through nanoclaw-lq and place deliverables in the expected
LAB output directory.

Deliverables:

- nanoclaw briefing builder or group briefing update.
- Dispatch code that writes a valid inbound task message.
- Mount configuration for read-only documents and writable output.
- Single-task adapter implementation.
- Filename sanity checks for expected deliverables.

Exit Criteria:

- One LAB task reaches nanoclaw and produces at least one expected deliverable in
  `results/<run-id>/output/`.

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Adapter core: NanoclawAdapter class, outbound.db STATUS: poll loop, wall-clock timeout, end-state mapping, D-04/D-05 message footer, plus Wave 0 unit tests + synthetic outbound.db fixture (autonomous)

**Wave 2** *(blocked on Wave 1; needs nanoclaw daemon + Docker for integration verify)*

- [x] 03-02-PLAN.md — Dispatch wiring: Node shim send-lab-message.ts in nanoclaw-lq repo (Option A), run() mount config + subprocess dispatch + poll, scripts/nanoclaw_run.py, mocked dispatch test (not autonomous)

**Wave 3** *(blocked on Wave 2; human setup + e2e proof)*

- [x] 03-03-PLAN.md — Exit criterion: human mount-allowlist + Anthropic-Claude LAB group setup, end-to-end proof run of corporate-ma/compare-matter-plan-against-engagement-letter producing discrepancy-analysis-memo.docx (not autonomous; approved with timeout-vs-deliverable semantics carried to Phase 4)

## Phase 4: Completion, Metrics, Evaluation, And Scale-Out

Status: planned

Goal: Make runs reliable enough for benchmark use and honest reporting.

Deliverables:

- Outbound `STATUS:` sentinel watcher.
- Timeout handling and run end-state recording.
- Token, timing, and document-coverage metrics where available.
- End-to-end command for run, evaluate, and report.
- Multi-task and multi-seed loop.
- Adapter contract documentation.

Exit Criteria:

- A run records clean/error/timeout status, writes metrics, invokes LAB scoring,
  and supports repeated runs with variance reporting.

**Plans:** 2/4 plans executed

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Benchmark status semantics and metrics diagnostics

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Primary LAB-compatible benchmark command and report preservation

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 04-03-PLAN.md — Multi-task multi-seed aggregation and variance reporting

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 04-04-PLAN.md — Practical adapter guide and second-adapter compatibility check
