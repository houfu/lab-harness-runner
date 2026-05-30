# Decisions

## Locked by Source Document

- Harvey LAB is an unmodified dependency. This project reads from and invokes
  LAB but does not fork or edit it.
- The integration surface is the filesystem and evaluator: task definitions,
  result directories, and `evaluation.run_eval`.
- nanoclaw-lq runs in its own Docker container, not inside LAB's podman sandbox.
- Deliverables should be written directly to LAB's expected
  `results/<run-id>/output/` directory.
- Completion is detected by a structured terminal sentinel from nanoclaw, with a
  wall-clock timeout as a backstop.
- The runner records why a run ended: clean finish, agent-reported error, or
  timeout.
- LAB remains the source of scoring and report generation.
- The public abstraction is a single adapter method:
  `run(task_spec, output_dir) -> RunResult`.
- The first implemented adapter is nanoclaw-lq only.
- Repository tooling uses `uv` for Python execution and `black` for formatting.

## Open Verification Items

- Confirm LAB's live `task.json` keys and optional `instructions.md` behavior.
- Confirm the current `evaluation.run_eval` CLI and result directory layout.
- Confirm LAB report/chart invocation paths.
- Confirm whether the scorer requires files beyond deliverables and metrics.
- Confirm nanoclaw group mount configuration.
- Confirm inbound and outbound SQLite row schemas.
- Confirm whether Ollama-backed runs expose token usage.
- Confirm the location and injection behavior for the nanoclaw group briefing.
