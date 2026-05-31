---
phase: 3
slug: implement-nanoclaw-lq-adapter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 — ALREADY INSTALLED (in `pyproject.toml` dev deps); existing suite under `tests/` |
| **Config file** | `pyproject.toml` (dev deps); `tests/conftest.py` already exists |
| **Quick run command** | `uv run pytest tests/test_nanoclaw_adapter.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds (unit tests; synthetic outbound.db in tmp_path) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_nanoclaw_adapter.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Phase gate (exit criterion, manual smoke):** `uv run python scripts/nanoclaw_run.py --task corporate-ma/compare-matter-plan-against-engagement-letter`; confirm `results/<run-id>/output/discrepancy-analysis-memo.docx` exists.
- **Max feedback latency:** ~5 seconds (unit layer)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-T3 | 01 | 1 | REQ-STATUS (STATUS: DONE in outbound.db → end_state="clean") | T-03-02 | Open/read/close-per-poll; only the task's own session outbound.db is read | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_status_done_returns_clean -x` | ❌ W0 | ⬜ pending |
| 03-01-T3 | 01 | 1 | REQ-TIMEOUT (poll timeout → end_state="timeout") | — | Timeout recorded distinctly from agent_error | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_timeout_returns_timeout -x` | ❌ W0 | ⬜ pending |
| 03-01-T3 | 01 | 1 | REQ-ENDSTATE (agent error → end_state="agent_error") | — | Non-clean terminal mapped correctly | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_status_error_returns_agent_error -x` | ❌ W0 | ⬜ pending |
| 03-01-T2/T3 | 01 | 1 | REQ-DELIVERABLE (footer states exact filenames; score_run gates missing deliverable before evaluator — enforced in Phase 2 evaluator.py) | T-03-01 | Footer lists exact expected_deliverables; score_run raises FileNotFoundError before subprocess (existing) | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_build_message_content_includes_contract -x` (footer) + `uv run pytest tests/test_evaluator.py -x` (pre-score gate) | ❌ W0 | ⬜ pending |
| 03-02-T1/T2 | 02 | 2 | REQ-DISPATCH (adapter creates session + enqueues message via Node shim) | T-03-05 | group_id rejected if unsafe relative path; list-form subprocess, no shell=True | integration | Manual — requires running nanoclaw daemon (Plan 02 Task 1 human-check) | ❌ W0 | ⬜ pending |
| 03-02-T2 | 02 | 2 | REQ-MOUNTS (documents appear at /workspace/extra/lab-documents RO; output RW) | T-03-04, T-03-06 | Only known docs dir + run output dir added to additional_mounts; relative containerPath | integration | Manual — requires Docker + daemon (verified at Plan 03 checkpoint) | ❌ W0 | ⬜ pending |
| 03-03-T2 | 03 | 3 | REQ-EXIT (one real task produces deliverable in output/) | T-03-08 | Allowlist scoped to LAB root only | e2e/smoke | `uv run python scripts/nanoclaw_run.py --task corporate-ma/compare-matter-plan-against-engagement-letter --nanoclaw-dir /Users/houfu/Projects/nanoclaw-lq --group-id <LAB group>` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs reconciled to plan tasks: 03-01-T2 (adapter logic + footer), 03-01-T3 (unit tests), 03-02-T1 (Node shim), 03-02-T2 (run() mounts+dispatch), 03-03-T2 (e2e proof run).*

---

## Wave 0 Requirements

- [x] pytest framework — ALREADY PRESENT (pytest 9.0.3 in dev deps; `tests/conftest.py` exists). No install task needed.
- [ ] `tests/test_nanoclaw_adapter.py` — stubs for REQ-STATUS, REQ-TIMEOUT, REQ-ENDSTATE, REQ-DELIVERABLE
- [ ] Extend `tests/conftest.py` (or add fixtures locally) — tmp_path-based synthetic outbound.db builder, fake session dir
- [ ] Human setup (cannot be unit-automated): add Harvey LAB paths to `~/.config/nanoclaw/mount-allowlist.json` (currently `allowedRoots: []` — silently drops all extra mounts)
- [ ] Human setup: ensure a LAB nanoclaw group configured for Anthropic Claude exists (the `_ping-test` group uses Ollama)

*If none: "Existing infrastructure covers all phase requirements." — pytest infra exists; only the new test file + fixtures + human nanoclaw setup remain.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Session creation + inbound enqueue via Node shim | REQ-DISPATCH | Requires the running nanoclaw daemon and pnpm/tsx; not unit-isolatable | Start daemon; run the shim with a test group + message; confirm a new session dir with inbound.db row appears |
| Documents/output mounts visible inside container | REQ-MOUNTS | Requires Docker container spawn | Spawn a session; from inside container confirm `/workspace/extra/lab-documents` (RO) and `/workspace/extra/lab-output` (RW) exist |
| End-to-end single-task run produces deliverable | REQ-EXIT | Requires daemon + Docker + Anthropic model + paid judge later | Run `scripts/nanoclaw_run.py` against the proof task; confirm `results/<run-id>/output/discrepancy-analysis-memo.docx` exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (pytest install, conftest, mount-allowlist, LAB group)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
