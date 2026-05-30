---
phase: 01
slug: verify-external-contracts-and-scoring-pipeline
status: complete
created: 2026-05-30
---

# Phase 1 Research: Verify External Contracts And Scoring Pipeline

## RESEARCH COMPLETE

## Scope

Phase 1 should verify the live Harvey LAB and nanoclaw-lq interfaces before any
adapter implementation depends on the imported design brief. The phase should
also prove LAB scoring with a hand-made run directory so later nanoclaw work is
not debugging the evaluator and agent integration at the same time.

## Local Repositories Found

- Harvey LAB: `/Users/houfu/Projects/harvey-labs`
- nanoclaw-lq: `/Users/houfu/Projects/nanoclaw-lq`
- Planning project: `/Users/houfu/Projects/lab-harness-runner`

## Verified LAB Findings

### Task Shape

- Task IDs are slash-separated paths under `tasks/`, with at least two parts.
- `evaluation.run_eval` requires `task.json` to contain `title`, `instructions`,
  and `criteria`.
- Each criterion must contain `id`, `title`, and `match_criteria`.
- Criterion `deliverables` is optional, but when present it must be a list of
  filenames.
- The built-in harness loader also supports `instructions.md` fallback when
  `instructions` is absent, but the evaluator validation currently requires the
  inline `instructions` key.
- The built-in harness loader requires a `documents/` directory.

Evidence:
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:26`
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:30`
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:57`
- `/Users/houfu/Projects/harvey-labs/harness/run.py:32`
- `/Users/houfu/Projects/harvey-labs/harness/run.py:53`
- `/Users/houfu/Projects/harvey-labs/harness/run.py:58`

### Result Layout And Scoring

- LAB resolves results under `<harvey-labs>/results/<run-id>/`.
- The scorer reads agent output from `<run-dir>/output/`.
- `metrics.json` is optional; if present, LAB reads `input_tokens`,
  `output_tokens`, `wall_clock_seconds`, `documents_read`, `total_vdr_files`,
  `documents_skipped`, `documents_read_list`, and `documents_skipped_list`.
- `scores.json` is written by `evaluation.run_eval`.
- The evaluator CLI is:
  `uv run python -m evaluation.run_eval --run-id <id> --task <area>/<slug> --judge-model claude-sonnet-4-6`
- `evaluation.run_eval` calls `generate_report()` automatically after scoring.
- `evaluation.report` can also be run directly and writes `report.html`.

Evidence:
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:24`
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:88`
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:137`
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:154`
- `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py:178`
- `/Users/houfu/Projects/harvey-labs/evaluation/report.py:1`
- `/Users/houfu/Projects/harvey-labs/evaluation/report.py:19`

### Deliverable Matching And Grading

- Per-criterion deliverables are expected filenames, and exact names are safest.
- LAB does extension, fuzzy, and LLM-assisted matching if exact names are absent,
  but depending on this adds a failure mode.
- Tasks are all-pass: score is `1.0` only if every criterion passes, otherwise
  `0.0`.

Evidence:
- `/Users/houfu/Projects/harvey-labs/evaluation/scoring.py:128`
- `/Users/houfu/Projects/harvey-labs/evaluation/scoring.py:315`
- `/Users/houfu/Projects/harvey-labs/evaluation/scoring.py:375`
- `/Users/houfu/Projects/harvey-labs/docs/eval-strategies.md:11`

## Verified nanoclaw-lq Findings

### Session And DB Model

- nanoclaw uses a split SQLite model:
  - `inbound.db` is host-owned and contains `messages_in`.
  - `outbound.db` is container-owned and contains `messages_out` and
    `processing_ack`.
- Host writes to `inbound.db` and must open/write/close per operation.
- Container writes to `outbound.db`; host reads it.
- A completion sentinel can be detected by polling `messages_out.content`, but
  the adapter should also inspect `processing_ack` for the inbound task message
  and use a wall-clock timeout.

Evidence:
- `/Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts:1`
- `/Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts:56`
- `/Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts:61`
- `/Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts:148`
- `/Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts:157`
- `/Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts:221`
- `/Users/houfu/Projects/nanoclaw-lq/container/agent-runner/src/db/messages-out.ts:23`

### Container Mounts

- The session directory mounts at `/workspace` and contains the DBs and outbox.
- The group folder mounts at `/workspace/agent`.
- Composed `CLAUDE.md` is regenerated at spawn and mounted read-only at
  `/workspace/agent/CLAUDE.md`.
- Additional mounts are configured through `container_configs.additional_mounts`
  and validated before being added.
- The agent runner discovers additional directories only under
  `/workspace/extra/*`, so LAB documents and LAB output should be mounted there,
  for example `/workspace/extra/lab-documents` and `/workspace/extra/lab-output`.

Evidence:
- `/Users/houfu/Projects/nanoclaw-lq/src/container-config.ts:26`
- `/Users/houfu/Projects/nanoclaw-lq/src/container-config.ts:50`
- `/Users/houfu/Projects/nanoclaw-lq/src/container-runner.ts:267`
- `/Users/houfu/Projects/nanoclaw-lq/src/container-runner.ts:270`
- `/Users/houfu/Projects/nanoclaw-lq/src/container-runner.ts:287`
- `/Users/houfu/Projects/nanoclaw-lq/src/container-runner.ts:323`
- `/Users/houfu/Projects/nanoclaw-lq/container/agent-runner/src/index.ts:56`

### Briefing Location

- The composed `groups/<folder>/CLAUDE.md` imports shared base instructions and
  fragments.
- Per-group editable memory lives in `CLAUDE.local.md`.
- For an adapter, Phase 1 should avoid permanently mutating existing nanoclaw
  group memory. The safer implementation path is to use a dedicated LAB agent
  group or inject the LAB task briefing as the first inbound message.

Evidence:
- `/Users/houfu/Projects/nanoclaw-lq/src/claude-md-compose.ts:1`
- `/Users/houfu/Projects/nanoclaw-lq/src/claude-md-compose.ts:48`
- `/Users/houfu/Projects/nanoclaw-lq/src/claude-md-compose.ts:119`

## External Issue Tracker Check

Web search for `harveyai/harvey-labs` plus agent-harness adapter terms found the
public repository and showed open issues/PRs exist, but did not surface an
obvious first-class bring-your-own-harness adapter issue. Treat this as a quick
negative signal, not a substitute for reviewing GitHub issues directly before
publishing anything upstream-facing.

Source checked: `https://github.com/harveyai/harvey-labs`

## Recommended Phase 1 Plan Shape

One focused plan is enough for this phase:

1. Create a local contract note from verified LAB and nanoclaw findings.
2. Add a small LAB probe script in this repo that can:
   - read a task JSON directly,
   - collect expected deliverable filenames,
   - create a LAB result skeleton,
   - write a dummy deliverable and metrics file,
   - optionally invoke LAB evaluation when a judge API key is available.
3. Run non-network validation against the probe in dry-run mode.
4. Document remaining live-evaluation manual step if no judge key is available.

This avoids implementing the nanoclaw adapter too early. Phase 1 should end with
a known result layout and evaluator command, not with a real agent run.

## Validation Architecture

Validation should not require live judge calls by default. The executable checks
for this phase should verify deterministic behavior:

- `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run`
- The command exits `0`.
- The probe creates `results/manual-probe/output/term-sheet-issues-memo.docx`.
- The probe creates `results/manual-probe/metrics.json`.
- The probe prints the exact evaluator command for the operator to run when
  judge credentials are available.

The optional manual scorer check is:

`cd /Users/houfu/Projects/harvey-labs && uv run python -m evaluation.run_eval --run-id manual-probe --task banking-finance/identify-term-sheet-issues --judge-model claude-sonnet-4-6`

## Planning Risks

- `evaluation.run_eval` requires inline `instructions`, so a future task with
  only `instructions.md` may load in `harness.run` but fail evaluator validation.
- LAB output matching is forgiving, but exact filenames are still required in
  our own sanity checks.
- nanoclaw DB access must preserve the one-writer invariant; use existing
  nanoclaw APIs where practical instead of ad hoc long-lived SQLite writers.
- Additional mounts should be under `/workspace/extra/*` so the agent runner
  advertises them as additional directories to the provider.
