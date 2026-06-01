---
phase: 3
slug: implement-nanoclaw-lq-adapter
status: verified
nyquist_compliant: true
wave_0_complete: true
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
| **Estimated runtime** | < 1 second for full local suite in current environment (unit tests; synthetic outbound.db in tmp_path) |

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
| 03-01-T3 | 01 | 1 | REQ-STATUS (STATUS: DONE in outbound.db -> end_state="clean") | T-03-02 | Open/read/close-per-poll; only the task's own session outbound.db is read | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_status_done_returns_clean -x` | ✅ | ✅ green |
| 03-01-T3 | 01 | 1 | REQ-TIMEOUT (poll timeout -> end_state="timeout") | — | Timeout recorded distinctly from agent_error | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_timeout_returns_timeout -x` | ✅ | ✅ green |
| 03-01-T3 | 01 | 1 | REQ-ENDSTATE (agent error -> end_state="agent_error") | — | Non-clean terminal mapped correctly | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_status_error_returns_agent_error -x` | ✅ | ✅ green |
| 03-01-T2/T3 | 01 | 1 | REQ-DELIVERABLE (footer states exact filenames; score_run gates missing deliverable before evaluator — enforced in Phase 2 evaluator.py) | T-03-01 | Footer lists exact expected_deliverables; score_run raises FileNotFoundError before subprocess (existing) | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_build_message_content_includes_contract -x` (footer) + `uv run pytest tests/test_evaluator.py -x` (pre-score gate) | ✅ | ✅ green |
| 03-02-T1/T2 | 02 | 2 | REQ-DISPATCH (adapter creates session + enqueues message via Node shim) | T-03-05 | group_id rejected if unsafe relative path; list-form subprocess, no shell=True | integration/unit hybrid | `uv run pytest tests/test_nanoclaw_adapter.py::test_dispatch_calls_shim_and_returns_clean -x`; live daemon path exercised by proof run | ✅ | ✅ green |
| 03-02-T2 | 02 | 2 | REQ-MOUNTS (documents appear at /workspace/extra/lab-documents RO; output RW) | T-03-04, T-03-06 | Only known docs dir + run output dir added to additional_mounts; relative containerPath | integration/manual evidence | `uv run pytest tests/test_nanoclaw_adapter.py::test_dispatch_calls_shim_and_returns_clean -x`; mount allowlist and proof artifact verified in 03-UAT.md and 03-SECURITY.md | ✅ | ✅ green |
| 03-03-T2 | 03 | 3 | REQ-EXIT (one real task produces deliverable in output/) | T-03-08 | Allowlist scoped to LAB root only | e2e/smoke | `test -s /Users/houfu/Projects/harvey-labs/results/69f75ee0-84e2-44ca-a906-0bca7da7baae/output/discrepancy-analysis-memo.docx`; 03-UAT.md passed 3/3 | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs reconciled to plan tasks: 03-01-T2 (adapter logic + footer), 03-01-T3 (unit tests), 03-02-T1 (Node shim), 03-02-T2 (run() mounts+dispatch), 03-03-T2 (e2e proof run).*

---

## Wave 0 Requirements

- [x] pytest framework — ALREADY PRESENT (pytest 9.0.3 in dev deps; `tests/conftest.py` exists). No install task needed.
- [x] `tests/test_nanoclaw_adapter.py` — covers REQ-STATUS, REQ-TIMEOUT, REQ-ENDSTATE, REQ-DELIVERABLE, path safety, and dispatch wiring.
- [x] `tests/conftest.py` — provides tmp_path-based synthetic outbound.db fixture.
- [x] Human setup: Harvey LAB path present in `~/.config/nanoclaw/mount-allowlist.json`.
- [x] Human setup: LAB nanoclaw group `lab-runner` / `820628bb-c260-4bb4-bd60-b5a3b9ce4f58` confirmed during Plan 03.

Existing infrastructure covers all Phase 3 requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Session creation + inbound enqueue via Node shim | REQ-DISPATCH | Requires the running nanoclaw daemon and pnpm/tsx; not unit-isolatable | Start daemon; run the shim with a test group + message; confirm a new session dir with inbound.db row appears |
| Documents/output mounts visible inside container | REQ-MOUNTS | Requires Docker container spawn | Spawn a session; from inside container confirm `/workspace/extra/lab-documents` (RO) and `/workspace/extra/lab-output` (RW) exist |
| End-to-end single-task run produces deliverable | REQ-EXIT | Requires daemon + Docker + Anthropic model + paid judge later | Run `scripts/nanoclaw_run.py` against the proof task; confirm `results/<run-id>/output/discrepancy-analysis-memo.docx` exists |

Manual-only results:
- REQ-DISPATCH and REQ-MOUNTS were exercised by the approved proof run and documented in `03-03-SUMMARY.md`, `03-UAT.md`, and `03-SECURITY.md`.
- REQ-EXIT is verified by `/Users/houfu/Projects/harvey-labs/results/69f75ee0-84e2-44ca-a906-0bca7da7baae/output/discrepancy-analysis-memo.docx`.
- The run's `metrics.json` recorded `end_state: "timeout"` despite valid output. This is not a Phase 3 validation gap because Phase 3's exit criterion is deliverable-based; it is carried to Phase 4 as a status semantics requirement.

---

## Validation Audit 2026-06-01

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 7 |
| Escalated | 0 |

Commands run:

```bash
uv run pytest tests/test_nanoclaw_adapter.py -x -q
uv run pytest tests/test_evaluator.py -x -q
uv run pytest tests/ -q
test -s /Users/houfu/Projects/harvey-labs/results/69f75ee0-84e2-44ca-a906-0bca7da7baae/output/discrepancy-analysis-memo.docx
```

Results:
- `tests/test_nanoclaw_adapter.py`: 8 passed
- `tests/test_evaluator.py`: 12 passed
- Full suite: 53 passed
- Proof deliverable presence check: passed

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or documented manual-only validation evidence
- [x] Sampling continuity: no 3 consecutive tasks without automated verify/manual proof evidence
- [x] Wave 0 covers all MISSING references (pytest install, conftest, mount-allowlist, LAB group)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-06-01
