# Phase 1 Context

## Goal

Confirm live external interfaces and prove that LAB scoring works from a
manually created output directory.

## Required Verification

- LAB task directory shape and `task.json` keys.
- Whether task instructions are inline or in `instructions.md`.
- Shape of `criteria[].deliverables`.
- Actual `evaluation.run_eval` command and parameters.
- Required result directory layout, including metrics filename and fields.
- Report/chart generation modules and commands.
- Whether scoring needs any harness-side files beyond deliverables and metrics.
- nanoclaw group mount configuration.
- inbound/outbound SQLite message schemas.
- Token usage availability for Ollama-backed runs.
- nanoclaw group briefing location and injection behavior.

## Expected Output

- Verified implementation notes.
- One simple LAB task scored from a hand-made deliverable directory.
