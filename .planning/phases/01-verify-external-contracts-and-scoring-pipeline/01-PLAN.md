---
phase: 01
plan: 01
title: Verify LAB and nanoclaw external contracts
type: standard
wave: 1
depends_on: []
files_modified:
  - docs/verified-contracts.md
  - docs/phase-1-manual-check.md
  - scripts/lab_probe.py
  - pyproject.toml
  - .gitignore
autonomous: true
requirements: []
requirements_addressed: []
---

<objective>
Verify the live Harvey LAB and nanoclaw-lq contracts that this project will
depend on, then prove the LAB result-directory shape with a deterministic
hand-made output probe. This phase deliberately stops before implementing the
nanoclaw adapter.
</objective>

<must_haves>
<truths>
- Harvey LAB remains an unmodified dependency.
- The integration surface is LAB task metadata, `results/<run-id>/output/`,
  optional `metrics.json`, `evaluation.run_eval`, `scores.json`, and LAB
  report generation.
- nanoclaw uses host-owned `inbound.db` and container-owned `outbound.db`; do
  not create a long-lived host writer against either DB in this phase.
- nanoclaw additional mounts should be configured as explicit
  `additionalMounts` and placed under `/workspace/extra/*` for provider
  visibility.
- The first real adapter remains deferred until Phase 3.
</truths>
<phase_success>
- `docs/verified-contracts.md` captures verified LAB and nanoclaw contracts
  with local file references.
- `scripts/lab_probe.py --dry-run` creates a LAB-compatible result skeleton,
  dummy expected deliverable, and `metrics.json`.
- `docs/phase-1-manual-check.md` contains the exact optional LAB evaluator
  command for running the judge-backed check.
</phase_success>
</must_haves>

<threat_model>
<assets>
- Harvey LAB checkout under `/Users/houfu/Projects/harvey-labs`.
- nanoclaw-lq checkout under `/Users/houfu/Projects/nanoclaw-lq`.
- Generated LAB result directory under the configured Harvey root.
- Judge API credentials loaded by Harvey LAB from its `.env`.
</assets>
<threats>
- T-01-01: A probe bug writes outside the configured LAB `results/` directory.
- T-01-02: A malformed `task` or `run-id` path escapes the expected tree.
- T-01-03: An implementation accidentally mutates the Harvey LAB or nanoclaw
  source checkout while only verification was intended.
- T-01-04: A default validation command triggers a paid external judge call
  unexpectedly.
</threats>
<mitigations>
- Resolve and validate paths before writing probe output.
- Reject absolute task IDs, `..`, and absolute run IDs.
- Keep Phase 1 writes inside this repo except the explicitly configured LAB
  `results/<run-id>/` probe output.
- Make judge evaluation an explicit manual command, not the default dry-run.
</mitigations>
</threat_model>

<tasks>
<task id="01-01" type="execute" autonomous="true">
<title>Document verified external contracts</title>
<read_first>
- .planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-RESEARCH.md
- .planning/PROJECT.md
- .planning/REQUIREMENTS.md
- /Users/houfu/Projects/harvey-labs/evaluation/run_eval.py
- /Users/houfu/Projects/harvey-labs/evaluation/scoring.py
- /Users/houfu/Projects/harvey-labs/harness/run.py
- /Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts
- /Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts
- /Users/houfu/Projects/nanoclaw-lq/src/container-config.ts
- /Users/houfu/Projects/nanoclaw-lq/src/container-runner.ts
- /Users/houfu/Projects/nanoclaw-lq/container/agent-runner/src/index.ts
</read_first>
<action>
Create `docs/verified-contracts.md` with sections for LAB task schema, LAB
result layout, evaluator/report commands, nanoclaw DB ownership, nanoclaw mount
configuration, and nanoclaw briefing behavior. Include concrete evidence paths
from `01-RESEARCH.md`. State the implementation consequence for each finding,
including: use exact deliverable filenames, treat `metrics.json` as optional but
write it, mount LAB documents/output under `/workspace/extra/*`, and keep judge
calls out of default validation.
</action>
<verify>
Run `test -f docs/verified-contracts.md`.
Run `grep -n "evaluation.run_eval" docs/verified-contracts.md`.
Run `grep -n "/workspace/extra" docs/verified-contracts.md`.
</verify>
<acceptance_criteria>
- `docs/verified-contracts.md` contains `## Harvey LAB Contracts`.
- `docs/verified-contracts.md` contains `## nanoclaw-lq Contracts`.
- `docs/verified-contracts.md` contains `/Users/houfu/Projects/harvey-labs/evaluation/run_eval.py`.
- `docs/verified-contracts.md` contains `/Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts`.
- `docs/verified-contracts.md` contains `/workspace/extra`.
</acceptance_criteria>
</task>

<task id="01-02" type="execute" autonomous="true">
<title>Create deterministic LAB result-layout probe</title>
<read_first>
- docs/verified-contracts.md
- /Users/houfu/Projects/harvey-labs/tasks/banking-finance/identify-term-sheet-issues/task.json
- /Users/houfu/Projects/harvey-labs/evaluation/run_eval.py
- /Users/houfu/Projects/harvey-labs/evaluation/scoring.py
</read_first>
<action>
Create a minimal Python project if needed with `pyproject.toml`, then implement
`scripts/lab_probe.py`. The script must accept `--harvey-root`, `--task`,
`--run-id`, and `--dry-run`. It must reject path traversal in `--task` and
`--run-id`, load `<harvey-root>/tasks/<task>/task.json`, collect unique expected
deliverable filenames from every criterion's `deliverables` list, create
`<harvey-root>/results/<run-id>/output/`, write one dummy file for each expected
deliverable filename, write `metrics.json` with `input_tokens`, `output_tokens`,
`wall_clock_seconds`, `documents_read`, `total_vdr_files`, `documents_skipped`,
`documents_read_list`, and `documents_skipped_list`, and print the exact
`uv run python -m evaluation.run_eval --run-id <run-id> --task <task>
--judge-model claude-sonnet-4-6` command. In `--dry-run`, do not invoke the
evaluator.
</action>
<verify>
Run `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run`.
Run `test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx`.
Run `test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json`.
</verify>
<acceptance_criteria>
- `scripts/lab_probe.py` contains `argparse`.
- `scripts/lab_probe.py` contains `def reject_unsafe_relative_path`.
- `scripts/lab_probe.py` contains `metrics.json`.
- `scripts/lab_probe.py` contains `evaluation.run_eval`.
- The dry-run command exits `0`.
- `/Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx` exists after the dry run.
- `/Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json` exists after the dry run.
</acceptance_criteria>
</task>

<task id="01-03" type="execute" autonomous="true">
<title>Document optional manual scorer proof</title>
<read_first>
- scripts/lab_probe.py
- docs/verified-contracts.md
- /Users/houfu/Projects/harvey-labs/evaluation/run_eval.py
- /Users/houfu/Projects/harvey-labs/evaluation/report.py
</read_first>
<action>
Create `docs/phase-1-manual-check.md` with the optional live scorer procedure.
The doc must say the default automated validation stops at dry-run because
`evaluation.run_eval` uses an external LLM judge. Include the exact command:
`cd /Users/houfu/Projects/harvey-labs && uv run python -m evaluation.run_eval
--run-id manual-probe --task banking-finance/identify-term-sheet-issues
--judge-model claude-sonnet-4-6`. State the expected artifacts:
`results/manual-probe/scores.json` and `results/manual-probe/report.html`.
</action>
<verify>
Run `grep -n "judge" docs/phase-1-manual-check.md`.
Run `grep -n "scores.json" docs/phase-1-manual-check.md`.
Run `grep -n "report.html" docs/phase-1-manual-check.md`.
</verify>
<acceptance_criteria>
- `docs/phase-1-manual-check.md` contains `uv run python -m evaluation.run_eval`.
- `docs/phase-1-manual-check.md` contains `manual-probe`.
- `docs/phase-1-manual-check.md` contains `scores.json`.
- `docs/phase-1-manual-check.md` contains `report.html`.
- The document states that the live scorer may require judge API credentials.
</acceptance_criteria>
</task>
</tasks>

<verification>
Run these commands from `/Users/houfu/Projects/lab-harness-runner`:

1. `test -f docs/verified-contracts.md`
2. `test -f scripts/lab_probe.py`
3. `test -f docs/phase-1-manual-check.md`
4. `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run`
5. `test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx`
6. `test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json`
</verification>

<success_criteria>
- Phase 1 produces verified contract documentation.
- Phase 1 produces a deterministic probe for LAB result layout.
- Phase 1 does not implement the nanoclaw adapter.
- Phase 1 does not run the paid/external judge by default.
- A developer has a documented manual scorer command to prove
  `scores.json` and `report.html` when credentials are available.
</success_criteria>
