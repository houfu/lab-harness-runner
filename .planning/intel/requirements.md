# Requirements

## Functional Requirements

- Discover or accept LAB task identifiers and locate their task directories.
- Read task instructions from `task.json` or `instructions.md`.
- Extract expected deliverable filenames from rubric criteria.
- Build a `TaskSpec` carrying instructions, documents directory, expected
  deliverables, and run id.
- Create a LAB-compatible `results/<run-id>/` skeleton, including an `output/`
  directory.
- Define an `AgentHarness` style adapter interface with
  `run(task_spec, output_dir) -> RunResult`.
- Implement a nanoclaw-lq adapter that dispatches task input into the selected
  agent group.
- Configure task documents as read-only input and run output as writable output
  for nanoclaw.
- Wait for a terminal `STATUS:` signal from nanoclaw or mark the run timed out.
- Validate expected deliverable filenames before scoring.
- Write `metrics.json` from `RunResult`, using zeros or null-safe defaults when
  a metric is unavailable.
- Invoke LAB's evaluator and collect `scores.json`.
- Preserve LAB-generated reports and dashboards rather than replacing them.
- Support multiple task and seed runs after the single-task path works.
- Document the adapter contract so other harness builders can implement it.

## Non-Functional Requirements

- Keep the package harness-agnostic outside adapter implementations.
- Keep adapter-specific sandbox, dispatch, completion, and metrics behavior
  behind `run()`.
- Prefer small, verifiable milestones over speculative abstraction.
- Present results as whole agent-system measurements, with variance for
  multi-run claims.
- Use `uv run ...` for Python commands and `black` for formatting.
