# Phase 2 Context

## Goal

Build the harness-neutral package core around task reading, result setup,
adapter invocation, metrics writing, and evaluator invocation.

## Decisions

<decisions>
- Package-owned code must not know nanoclaw-specific execution details.
- The adapter boundary is one blocking call that receives a task spec and output
  directory and returns a run result.
</decisions>

## Expected Output

- Python project scaffold.
- `TaskSpec`, `RunResult`, and adapter protocol.
- Task reader, result directory builder, metrics writer, and evaluator wrapper.
- Fake adapter path for proving the lifecycle.
