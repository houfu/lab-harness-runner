# Roadmap

## Phase 1: Verify External Contracts And Scoring Pipeline

Status: planned

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

## Phase 3: Implement Nanoclaw-LQ Adapter

Status: planned

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
