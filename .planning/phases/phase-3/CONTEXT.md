# Phase 3 Context

## Goal

Implement nanoclaw-lq as the reference adapter and run one LAB task through it.

## Decisions

<decisions>
- nanoclaw stays in its own Docker container.
- Task documents are mounted read-only.
- The LAB output directory is mounted read-write.
- Deliverables should use exact expected filenames.
</decisions>

## Expected Output

- nanoclaw dispatch implementation.
- group briefing or briefing builder.
- mount wiring.
- single-task execution path with deliverable sanity checks.
