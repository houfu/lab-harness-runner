# Verified External Contracts

Phase 1 verifies the live interfaces this project will depend on before any
nanoclaw adapter code is built.

Path placeholders:

- `<harvey-labs>`: local checkout of Harvey LAB.
- `<nanoclaw-lq>`: local checkout of nanoclaw-lq.

## Harvey LAB Contracts

### Task Schema

Task IDs are slash-separated paths under `<harvey-labs>/tasks`.
The evaluator requires each task's `task.json` to include:

- `title`
- `instructions`
- `criteria`

Each criterion must include:

- `id`
- `title`
- `match_criteria`

When `deliverables` is present on a criterion, it must be a list of filenames.
The built-in LAB harness loader can fall back to `instructions.md` when
`instructions` is missing, but `evaluation.run_eval` currently validates
`instructions` as required. Treat inline `instructions` as the evaluator contract.

Evidence:

- `<harvey-labs>/evaluation/run_eval.py:26`
- `<harvey-labs>/evaluation/run_eval.py:30`
- `<harvey-labs>/harness/run.py:32`
- `<harvey-labs>/harness/run.py:53`
- `<harvey-labs>/harness/run.py:58`

Implementation consequence: the package should read task JSON directly, extract
instructions from `task.json`, and only support `instructions.md` fallback as a
compatibility helper after confirming evaluator behavior for that task.

### Result Layout

LAB resolves runs under:

`<harvey-labs>/results/<run-id>/`

The scorer reads agent output from:

`<harvey-labs>/results/<run-id>/output/`

`metrics.json` is optional, but when present LAB reads:

- `input_tokens`
- `output_tokens`
- `wall_clock_seconds`
- `documents_read`
- `total_vdr_files`
- `documents_skipped`
- `documents_read_list`
- `documents_skipped_list`

Evidence:

- `<harvey-labs>/evaluation/run_eval.py:24`
- `<harvey-labs>/evaluation/run_eval.py:88`
- `<harvey-labs>/evaluation/run_eval.py:137`

Implementation consequence: the package should always create
`results/<run-id>/output/` and write `metrics.json` with safe defaults, even when
the adapter cannot provide real token or document coverage metrics.

### Evaluator And Reports

The evaluator command is:

```bash
uv run python -m evaluation.run_eval --run-id <run-id> --task <area>/<slug> --judge-model claude-sonnet-4-6
```

`evaluation.run_eval` writes `scores.json` and invokes report generation. The
report module writes `report.html`.

Evidence:

- `<harvey-labs>/evaluation/run_eval.py:154`
- `<harvey-labs>/evaluation/run_eval.py:178`
- `<harvey-labs>/evaluation/report.py:1`
- `<harvey-labs>/evaluation/report.py:19`

Implementation consequence: live evaluation should be an explicit step because
the judge may require API credentials and external model calls. Dry-run
validation should stop at result-layout creation.

### Deliverable Matching

Per-criterion deliverables are expected output filenames. LAB can perform
extension, fuzzy, and LLM-assisted matching if exact filenames are missing, but
exact filenames remove that failure mode.

Evidence:

- `<harvey-labs>/evaluation/scoring.py:128`
- `<harvey-labs>/evaluation/scoring.py:315`
- `<harvey-labs>/evaluation/scoring.py:375`
- `<harvey-labs>/docs/eval-strategies.md:11`

Implementation consequence: the package should extract unique expected filenames
from `criteria[].deliverables` and fail its own pre-score sanity check if any
expected deliverable is missing.

## nanoclaw-lq Contracts

### Session Databases

nanoclaw uses two SQLite files per session:

- `inbound.db`: host-owned, contains `messages_in`
- `outbound.db`: container-owned, contains `messages_out` and `processing_ack`

Host writes must open, write, and close per operation. The split is designed to
avoid cross-mount SQLite write contention.

Evidence:

- `<nanoclaw-lq>/src/session-manager.ts:1`
- `<nanoclaw-lq>/src/session-manager.ts:56`
- `<nanoclaw-lq>/src/session-manager.ts:61`
- `<nanoclaw-lq>/src/db/schema.ts:148`
- `<nanoclaw-lq>/src/db/schema.ts:157`
- `<nanoclaw-lq>/src/db/schema.ts:221`

Implementation consequence: adapter code should prefer nanoclaw's existing
session APIs where practical. If it writes directly, it must preserve the
one-writer invariant and avoid long-lived host connections.

### Mount Configuration

The session directory mounts at `/workspace`, and the group folder mounts at
`/workspace/agent`. Additional mounts are configured through
`container_configs.additional_mounts`, then validated and appended by the
container runner.

The agent runner discovers additional directories mounted under
`/workspace/extra/*`.

Evidence:

- `<nanoclaw-lq>/src/container-config.ts:26`
- `<nanoclaw-lq>/src/container-config.ts:50`
- `<nanoclaw-lq>/src/container-runner.ts:267`
- `<nanoclaw-lq>/src/container-runner.ts:270`
- `<nanoclaw-lq>/src/container-runner.ts:323`
- `<nanoclaw-lq>/container/agent-runner/src/index.ts:56`

Implementation consequence: mount LAB documents and LAB output as explicit
additional mounts under stable paths such as `/workspace/extra/lab-documents`
and `/workspace/extra/lab-output`.

### Briefing Behavior

nanoclaw composes `groups/<folder>/CLAUDE.md` at spawn from shared base
instructions, fragments, and per-group local memory. The composed file is mounted
read-only inside the container. Per-group editable memory lives in
`CLAUDE.local.md`.

Evidence:

- `<nanoclaw-lq>/src/claude-md-compose.ts:1`
- `<nanoclaw-lq>/src/claude-md-compose.ts:48`
- `<nanoclaw-lq>/src/claude-md-compose.ts:119`

Implementation consequence: avoid mutating an existing nanoclaw group for LAB
runs. Prefer a dedicated LAB group or put the task-specific briefing in the
first inbound task message.

## Phase 1 Boundary

Phase 1 does not change `<nanoclaw-lq>`. It verifies the
contracts and creates a deterministic LAB result-layout probe. Real nanoclaw
adapter work starts in a later phase.
