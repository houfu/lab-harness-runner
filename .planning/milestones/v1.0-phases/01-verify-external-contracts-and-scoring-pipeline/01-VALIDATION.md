---
phase: 01
slug: verify-external-contracts-and-scoring-pipeline
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-30
verified: 2026-06-02
---

# Phase 01 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Shell artifact checks plus Python stdlib behavior in `scripts/lab_probe.py` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run` |
| **Full suite command** | `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run` |
| **Estimated runtime** | ~5 seconds |

## Sampling Rate

- **After every task commit:** Run the quick probe command.
- **After every plan wave:** Run the full probe command.
- **Before `$gsd-verify-work`:** Probe command must be green.
- **Max feedback latency:** 10 seconds.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | LAB contracts | T-01-01 | No writes outside configured result dir | source + CLI | `test -f docs/verified-contracts.md` | yes | passed |
| 01-01-02 | 01 | 1 | result skeleton | T-01-02 | Reject invalid task/result paths | CLI | `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run` | yes | passed |
| 01-01-03 | 01 | 1 | evaluator command | T-01-04 | Judge call remains explicit/manual unless enabled | source + manual-only | `grep -n "evaluation.run_eval" docs/phase-1-manual-check.md` | yes | passed |

## Wave 0 Requirements

- [x] `scripts/lab_probe.py` — deterministic probe for LAB task/result layout.
- [x] `docs/verified-contracts.md` — local contract notes with evidence paths.
- [x] `docs/phase-1-manual-check.md` — manual scorer command and expected output.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LAB judge scoring writes `scores.json` and `report.html` | Scoring pipeline | Requires judge API key and may make paid external model calls | Run the documented `cd /Users/houfu/Projects/harvey-labs && uv run python -m evaluation.run_eval --run-id manual-probe --task banking-finance/identify-term-sheet-issues --judge-model claude-sonnet-4-6` command when credentials are available. |

## Validation Sign-Off

- [x] All tasks have automated verification or an explicit manual-only reason.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 10s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** verified

## Validation Audit 2026-06-02

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |
| Skipped | 0 |

## Audit Evidence

| Behavior | Command | Result |
|----------|---------|--------|
| Phase 1 live external contract artifacts exist | `test -f docs/verified-contracts.md` | passed |
| Phase 1 manual scorer artifact exists | `test -f docs/phase-1-manual-check.md` | passed |
| LAB task/result/evaluator notes are evidence-backed | `grep -n "evaluation.run_eval" docs/verified-contracts.md` and `grep -n "/workspace/extra" docs/verified-contracts.md` | passed |
| Dry-run verifies LAB result path/layout without invoking judge | `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run` | passed |
| Dry-run creates expected deliverable | `test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx` | passed |
| Dry-run creates metrics file | `test -f /Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json` | passed |
| Manual judge-backed scoring remains explicit/manual | `grep -n "judge" docs/phase-1-manual-check.md`, `grep -n "scores.json" docs/phase-1-manual-check.md`, and `grep -n "report.html" docs/phase-1-manual-check.md` | passed |
