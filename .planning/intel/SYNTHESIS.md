# Ingest Synthesis

## Project

Build a harness-agnostic LAB runner package with a worked nanoclaw-lq adapter.
The package reads Harvey LAB tasks, runs an external agent harness through a
single-method adapter, writes LAB-compatible result directories, and invokes
LAB's evaluator and reports without modifying LAB.

## Goals

- Prove the LAB scoring pipeline with a hand-made output before integrating an
  agent.
- Implement a minimal package lifecycle around task reading, result directory
  creation, adapter invocation, metrics writing, and LAB evaluation.
- Implement nanoclaw-lq as the reference adapter.
- Keep the adapter seam narrow enough that other harness builders can implement
  it without forking LAB or this package.
- Report outcomes honestly as full agent-system results.

## Non-Goals

- Do not fork or patch Harvey LAB.
- Do not build a replacement reporting system.
- Do not implement speculative second or third harness adapters before there is
  a real user for them.
- Do not make package-owned code responsible for sandbox management.

## Locked Decisions

- LAB stays unmodified.
- The evaluator and filesystem result layout are the key integration surface.
- nanoclaw runs in its own Docker container.
- Completion uses a terminal `STATUS:` signal plus timeout.
- The reusable harness interface is `run(task_spec, output_dir) -> RunResult`.
- The first adapter is nanoclaw-lq.
- Use `uv` and `black`.

## Roadmap Shape

1. Validate live LAB and nanoclaw interfaces, then prove scoring with a manual
   deliverable.
2. Build the harness-neutral package core and task/result contracts.
3. Add the nanoclaw-lq adapter for dispatch, mounts, and single-task execution.
4. Add completion detection, metrics, evaluation orchestration, and run
   aggregation.
