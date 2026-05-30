# Phase 4 Context

## Goal

Add reliable completion detection, metrics, evaluation orchestration, and
repeated-run support.

## Decisions

<decisions>
- Completion requires a structured `STATUS:` terminal signal or timeout.
- Run end-state is separate from score.
- Results must be described as whole agent-system scores.
</decisions>

## Expected Output

- Sentinel watcher.
- Timeout handling.
- Metrics capture and `metrics.json` writing.
- End-to-end evaluate/report command.
- Multi-task and multi-seed loop.
- Adapter contract documentation.
