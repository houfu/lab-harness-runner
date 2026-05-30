---
phase: 01-verify-external-contracts-and-scoring-pipeline
status: passed
verified_at: 2026-05-30
score: 6/6
human_verification: []
warnings:
  - Live LAB judge-backed scoring was not run because it may require external API credentials and paid model calls.
  - Local pandoc extraction was not run because pandoc is not installed on this machine's PATH.
  - Security enforcement is enabled by default and no 01-SECURITY.md exists yet.
---

# Phase 1 Verification

## Result

Passed. Phase 1 achieved the scoped plan goal: verified the live LAB and
nanoclaw-lq contracts, created a deterministic LAB result-layout probe, and
documented the optional live scorer command.

The original roadmap phrased one deliverable as a successful evaluator run that
writes `scores.json`. The approved Phase 1 plan intentionally narrowed default
automation to a dry run because `evaluation.run_eval` invokes an external judge.
The live scorer command and expected artifacts are documented for manual use
when credentials are available.

## Must-Have Checks

- Verified LAB contracts are documented in `docs/verified-contracts.md`.
- Verified nanoclaw-lq contracts are documented in `docs/verified-contracts.md`.
- Phase 1 does not modify `/Users/houfu/Projects/nanoclaw-lq`.
- `scripts/lab_probe.py --dry-run` creates `results/<run-id>/output/`,
  expected deliverables, and `metrics.json`.
- `.docx` probe deliverables are real Office Open XML packages.
- `docs/phase-1-manual-check.md` contains the exact optional
  `uv run python -m evaluation.run_eval` command, expected `scores.json`, and
  expected `report.html`.

## Commands Run

```bash
test -f docs/verified-contracts.md
test -f scripts/lab_probe.py
test -f docs/phase-1-manual-check.md
grep -n "evaluation.run_eval" docs/verified-contracts.md
grep -n "/workspace/extra" docs/verified-contracts.md
grep -n "judge" docs/phase-1-manual-check.md
grep -n "scores.json" docs/phase-1-manual-check.md
grep -n "report.html" docs/phase-1-manual-check.md
uv run python -m py_compile scripts/lab_probe.py
uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run
test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx
test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json
file /Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx
gsd-sdk query verify.schema-drift 01
gsd-sdk query verify.codebase-drift
```

## Evidence

- Dry-run result skeleton:
  `/Users/houfu/Projects/harvey-labs/results/manual-probe`
- Expected deliverable:
  `/Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx`
- Metrics file:
  `/Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json`
- DOCX file type check: `Microsoft Word 2007+`
- Schema drift: none detected.
- Codebase drift: skipped because no `STRUCTURE.md` exists.

## Follow-Up

Before advancing to implementation-heavy phases, run:

```bash
$gsd-secure-phase 1
```
