---
phase: 01
slug: verify-external-contracts-and-scoring-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-30
---

# Phase 01 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python stdlib assertions through the probe script |
| **Config file** | `pyproject.toml` if created by the plan; otherwise none |
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
| 01-01-01 | 01 | 1 | LAB contracts | T-01-01 | No writes outside configured result dir | source + CLI | `test -f docs/verified-contracts.md` | no | pending |
| 01-01-02 | 01 | 1 | result skeleton | T-01-02 | Reject invalid task/result paths | CLI | `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run` | no | pending |
| 01-01-03 | 01 | 1 | evaluator command | — | Judge call remains explicit/manual unless enabled | source | `grep -n "evaluation.run_eval" docs/phase-1-manual-check.md` | no | pending |

## Wave 0 Requirements

- [ ] `scripts/lab_probe.py` — deterministic probe for LAB task/result layout.
- [ ] `docs/verified-contracts.md` — local contract notes with evidence paths.
- [ ] `docs/phase-1-manual-check.md` — manual scorer command and expected output.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LAB judge scoring writes `scores.json` and `report.html` | Scoring pipeline | Requires judge API key and may make paid external model calls | Run the documented `uv run python -m evaluation.run_eval ...` command from the Harvey LAB repo when credentials are available. |

## Validation Sign-Off

- [ ] All tasks have automated verification or an explicit manual-only reason.
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] Wave 0 covers all missing references.
- [ ] No watch-mode flags.
- [ ] Feedback latency < 10s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending
