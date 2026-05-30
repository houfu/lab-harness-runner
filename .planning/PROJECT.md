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
