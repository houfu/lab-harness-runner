---
phase: 7
slug: sweep-driver-hardening-and-lab-aggregation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash / pytest (existing) |
| **Config file** | none — Wave 0 installs no new framework |
| **Quick run command** | `bash scripts/sweep.sh --help 2>&1 \| head -5` |
| **Full suite command** | `python -m pytest tests/ -x -q 2>/dev/null \|\| echo "no pytest suite"` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `bash -n scripts/sweep.sh` (syntax check)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 1 | SWP-01 | — | N/A | syntax | `bash -n scripts/sweep.sh` | ✅ | ⬜ pending |
| 7-02-01 | 02 | 1 | SWP-02 | — | N/A | functional | `bash scripts/sweep.sh inventory <results_dir> \| grep -v '^#' \| head -5` | ✅ | ⬜ pending |
| 7-02-02 | 02 | 1 | SWP-03 | — | N/A | functional | `bash scripts/sweep.sh ... ; echo "exit=$?"` | ✅ | ⬜ pending |
| 7-03-01 | 03 | 2 | SWP-04 | — | N/A | integration | `LAB_COMPARE=task bash scripts/sweep.sh ... 2>&1 \| tail -5` | ✅ | ⬜ pending |
| 7-04-01 | 04 | 3 | LAB-01 | — | N/A | manual | Replay inventory against ~/Projects/harvey-labs/results/ | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements — no new test framework installation needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Replay inventory matches live results (136 clean + 34 timeout = 170 total) | LAB-01 | Requires access to ~/Projects/harvey-labs/results/ | Run `bash scripts/sweep.sh inventory ~/Projects/harvey-labs/results/` and verify counts |
| LAB_COMPARE integration invokes LAB's evaluation.compare | LAB-02 | Requires LAB repo present at ~/Projects/harvey-labs/ | Run `LAB_COMPARE=all bash scripts/sweep.sh <results_dir>` and verify LAB tool is called |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
