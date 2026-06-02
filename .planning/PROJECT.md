# lab-nanoclaw

## Purpose

Build a harness-agnostic runner package that can execute Harvey LAB tasks through
external agent harnesses, starting with nanoclaw-lq, and score those runs using
LAB's existing evaluator and reporting pipeline.

## Scope

This project owns the glue around LAB task reading, result directory creation,
adapter invocation, metrics capture, evaluator invocation, and run aggregation.
It treats Harvey LAB as an unmodified dependency and nanoclaw-lq as the first
reference adapter.

## Goals

- Prove LAB scoring with a manually created output before integrating nanoclaw.
- Provide a narrow adapter contract:
  `run(task_spec, output_dir) -> RunResult`.
- Implement a nanoclaw-lq adapter that can run a LAB task and produce
  deliverables in LAB's expected output directory.
- Preserve LAB's existing `scores.json`, report, and dashboard generation.
- Record run end-state so harness failures are not silently treated as model
  failures.
- Document the adapter contract for future community harnesses.

## Non-Goals

- Do not fork or modify Harvey LAB.
- Do not replace LAB's evaluator or reporting system.
- Do not implement speculative additional adapters before a real second harness
  needs one.
- Do not make package-owned code responsible for harness sandboxing.

## Runtime And Tooling

- Language/runtime: Python, managed with `uv`.
- Command convention: use `uv run ...` for project commands.
- Formatting: `black`.
- External dependencies: a local Harvey LAB clone, nanoclaw-lq, Docker for
  nanoclaw, and LAB's judge API configuration.

## Locked Decisions

<decisions>
- Harvey LAB is an unmodified dependency; this project must not edit or fork it.
- Integration depends on LAB's filesystem and evaluator surfaces: task metadata,
  result directories, and `evaluation.run_eval`.
- nanoclaw-lq runs in its own Docker container, not inside LAB's podman sandbox.
- Deliverables should land directly in `results/<run-id>/output/`.
- Run completion is detected by a structured terminal `STATUS:` signal plus a
  wall-clock timeout.
- The runner records whether each run ended cleanly, with agent error, or by
  timeout.
- LAB remains the source of scoring and report generation.
- The reusable adapter interface is `run(task_spec, output_dir) -> RunResult`.
- The first implemented adapter is nanoclaw-lq.
- Use `uv` and `black`.
</decisions>

## Success Metric

A single LAB task can be run through nanoclaw-lq end to end, producing expected
deliverables, `metrics.json`, LAB `scores.json`, and a recorded run end-state
without modifying LAB.

## Current State

**Shipped:** v1.0 MVP (2026-06-02) — Phases 1-4, 13 plans, 99 tests passing.

The success metric is met: one LAB task (`corporate-ma/compare-matter-plan-against-engagement-letter`)
ran end to end through the nanoclaw-lq adapter, producing
`discrepancy-analysis-memo.docx`, `metrics.json`, and a recorded run end-state.

### Validated

- ✓ Harness-neutral package core (`TaskSpec`/`RunResult`/`Adapter` protocol, task
  reader, result builder, metrics writer, evaluator wrapper) — v1.0
- ✓ nanoclaw-lq adapter: Node dispatch shim, read-only doc / read-write output
  mounts, `STATUS:` poll loop, wall-clock timeout — v1.0
- ✓ LAB evaluator invocation preserving `scores.json`, reports, and dashboards — v1.0
- ✓ Run end-state recording (clean / agent-error / timeout) plus benchmark status
  semantics (timeout-with-deliverable → benchmark-clean) — v1.0
- ✓ Multi-task / multi-seed batch aggregation with variance reporting — v1.0
- ✓ Documented third-party adapter contract — v1.0

### Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| LAB is an unmodified dependency, integrated via filesystem/evaluator surfaces | Keep runner portable and avoid forking LAB | ✓ Good |
| Adapter contract `run(task_spec, output_dir) -> RunResult` | Narrow, reusable boundary for future harnesses | ✓ Good |
| Completion = terminal `STATUS:` signal + wall-clock timeout | Distinguish clean completion from hangs | ✓ Good |
| Benchmark status derives clean from valid deliverables while preserving raw `end_state: timeout` | Honest reporting when output exists but no terminal signal observed | ⚠️ Revisit — exercise on more tasks |
| Node dispatch shim lives in the nanoclaw-lq repo (Option A) | Avoid reimplementing nanoclaw message protocol in Python | ✓ Good |

### Context / Known Limitations

- Live judge-backed scoring and real dashboard generation remain
  environment-dependent (require local credentials/runtime). Subprocess paths,
  artifact checks, and preservation behavior are tested.
- REQ-02: `read_task()` supports the verified current LAB shape
  (`task.json["instructions"]`). A move to `instructions.md` would be a contract change.
- Phase 3 lacks a formal `03-VERIFICATION.md`; closure evidence lives in UAT,
  security, validation, summaries, tests, and the proof deliverable.

## Next Milestone Goals

Deferred from v1.0, candidates for the next milestone:

- Additional adapters beyond nanoclaw-lq (REQ-23, deferred until a real second
  harness needs one).
- Upstream LAB documentation PR for stable task/result contracts.
- Public package publishing and broader community onboarding (REQ-24).

---

_Last updated: 2026-06-02 after v1.0 milestone_
