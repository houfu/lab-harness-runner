# Document Classification: lab-nanoclaw-plan.md

Path: lab-nanoclaw-plan.md
Type: DOC
Source: heuristic
Precedence: DOC

## Summary

Implementation brief and public design document for building a harness-agnostic
adapter package that can run the local nanoclaw-lq agent system against Harvey
LAB tasks, write LAB-compatible run outputs, and invoke LAB's existing evaluator
without modifying LAB.

## Extracted Decisions

- Treat Harvey LAB as an unmodified dependency, not a fork.
- Depend only on LAB's stable filesystem/scorer surfaces: task metadata and
  `evaluation.run_eval`.
- Do not import LAB's harness orchestrator or use LAB's sandbox for nanoclaw.
- Mount nanoclaw output directly at `results/<run-id>/output/`.
- Detect run completion through a structured terminal sentinel plus a wall-clock
  timeout backstop.
- Record run end state separately from score.
- Use LAB's own reports and dashboards instead of building a reporting system.
- Define a one-method adapter seam: `run(task_spec, output_dir) -> RunResult`.
- Build only the nanoclaw-lq adapter first; leave additional adapters for real
  second users.
- Use `uv` for Python environment and invocation, and `black` for formatting.

## Extracted Requirements

- Read LAB task definitions from `task.json` and optional `instructions.md`.
- Extract expected deliverable filenames from `criteria[].deliverables`.
- Create a LAB-compatible `results/<run-id>/output/` directory.
- Dispatch task instructions and briefing into the nanoclaw agent group.
- Mount task documents read-only and the run output directory read-write.
- Wait for terminal `STATUS:` output or timeout.
- Confirm expected deliverables exist with matching filenames.
- Write `metrics.json` with token, timing, document-coverage, and end-state data
  where available.
- Invoke LAB evaluation to produce `scores.json`.
- Support package-owned loops over tasks and seeds.
- Document the harness adapter contract for community use.

## Extracted Constraints

- Do not modify the Harvey LAB repository.
- Keep nanoclaw in its own Docker container; do not nest it inside LAB's podman
  sandbox.
- Package code must remain sandbox-agnostic.
- Completion detection and harness-specific metrics stay inside the adapter.
- Metrics fields are optional; absent values should be represented safely.
- Results should be described as whole agent-system scores, not model-only
  scores.
- Verify live LAB and nanoclaw-lq interfaces before implementation because the
  brief may have drifted from current code.

## Suggested Phases

1. Verify LAB scoring pipeline with a hand-made output.
2. Define package skeleton and harness-neutral task/result contracts.
3. Implement nanoclaw-lq adapter dispatch and mounts.
4. Implement completion detection, metrics, evaluation, and reporting loop.
