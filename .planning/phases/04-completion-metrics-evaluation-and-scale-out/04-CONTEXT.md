# Phase 4: Completion, Metrics, Evaluation, And Scale-Out - Context

**Gathered:** 2026-06-01T03:35:10Z
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the single-task nanoclaw proof into a reliable benchmark workflow: completion
semantics, deliverable validation, LAB scoring/report preservation, repeated
task/seed execution, variance summaries, and practical adapter documentation.

This phase does not add a second adapter or modify Harvey LAB. It makes the first
adapter path honest and usable enough for benchmark runs.

</domain>

<decisions>
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Audit And Requirements
- `.planning/v1.0-MILESTONE-AUDIT.md` — Defines the Phase 4 blockers:
  status semantics, report preservation, multi-task/multi-seed, variance, and
  adapter documentation.
- `.planning/REQUIREMENTS.md` — Functional and quality requirements, including
  LAB report preservation, repeated runs, and whole agent-system reporting.
- `.planning/PROJECT.md` — Locked project scope and non-goals.
- `.planning/ROADMAP.md` — Phase 4 goal, deliverables, and exit criteria.

### Phase 3 Evidence
- `.planning/phases/03-implement-nanoclaw-lq-adapter/03-03-SUMMARY.md` —
  Documents the proof run where output existed but `end_state` was `timeout`.
- `.planning/phases/03-implement-nanoclaw-lq-adapter/03-UAT.md` — User
  acceptance evidence approving deliverable-based success and honest timeout
  metrics.
- `.planning/phases/03-implement-nanoclaw-lq-adapter/03-VALIDATION.md` —
  Validation evidence and Phase 4 status-semantics carry-forward.

### Existing Package Surface
- `lab_harness_runner/adapter.py` — `TaskSpec`, `RunResult`, and `Adapter`
  Protocol.
- `lab_harness_runner/metrics.py` — Current `metrics.json` writer.
- `lab_harness_runner/evaluator.py` — Existing LAB scoring wrapper and
  deliverable pre-validation.
- `scripts/nanoclaw_run.py` — Existing single-task nanoclaw script to evolve or
  wrap for the primary benchmark command.
- `scripts/fake_run.py` — Phase 2 wiring proof reference.

### External Contract Notes
- `docs/verified-contracts.md` — Verified LAB result/evaluator/report contracts
  and nanoclaw mount/session contracts.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lab_harness_runner/adapter.py`: `RunResult` currently validates raw
  `end_state`; Phase 4 can add a separate benchmark status layer without
  breaking adapter internals.
- `lab_harness_runner/metrics.py`: currently writes LAB-required metrics with
  safe defaults and `end_state`; likely extension point for additional status
  fields.
- `lab_harness_runner/evaluator.py`: already validates expected deliverables
  before scoring and returns the `scores.json` path.
- `scripts/nanoclaw_run.py`: already performs read_task -> build_result_dir ->
  adapter.run -> write_metrics -> optional score; likely the closest starting
  point for the single primary command.

### Established Patterns
- Use `uv run ...` for project commands.
- Use list-form subprocess calls with `cwd=...` and `check=True`.
- Keep LAB as an unmodified dependency; interact with its filesystem and
  evaluator CLI surfaces.
- Keep outputs under Harvey LAB's `results/<run-id>/` for compatibility.

### Integration Points
- Benchmark command should compose existing package functions rather than
  duplicating task/result/metric/evaluator logic.
- Aggregate summaries should reference LAB result paths instead of changing
  LAB's expected output structure.

</code_context>

<specifics>
## Specific Ideas

- For the Phase 3 mixed state, use deliverable validation to produce benchmark
  status `clean`, while preserving raw/protocol evidence such as
  `terminal_status_seen: false` and `raw_end_state: "timeout"`.
- Batch summary should make whole-system reporting easy: adapter, task, seed,
  benchmark status, raw status, deliverable validation, score path, report path,
  and variance inputs.

</specifics>

<deferred>
## Deferred Ideas

- Full public package documentation, tutorials, and contribution docs remain out
  of scope for this milestone.
- Additional adapters beyond nanoclaw-lq remain deferred until a real second
  harness needs one.

</deferred>

---

*Phase: 4-Completion, Metrics, Evaluation, And Scale-Out*
*Context gathered: 2026-06-01T03:35:10Z*
