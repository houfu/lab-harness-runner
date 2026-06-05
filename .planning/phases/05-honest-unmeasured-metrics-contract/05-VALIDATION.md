---
phase: 5
slug: honest-unmeasured-metrics-contract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project test dep, configured via `pyproject.toml`) |
| **Config file** | `pyproject.toml` (no dedicated pytest config; default discovery) |
| **Quick run command** | `uv run --quiet python -m pytest tests/test_metrics.py tests/test_aggregation.py tests/test_run_benchmark.py tests/test_docs.py -q` |
| **Full suite command** | `uv run --quiet python -m pytest -q` |
| **Estimated runtime** | ~15 seconds (full suite ~25s on this project) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --quiet python -m pytest tests/test_metrics.py tests/test_aggregation.py tests/test_run_benchmark.py tests/test_docs.py -q`
- **After every plan wave:** Run `uv run --quiet python -m pytest -q` (full suite)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds (per-task) / ~25 seconds (full suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CON-01 | — | N/A | unit | `pytest tests/test_metrics.py -q` | ✅ | ⬜ pending |
| 05-01-02 | 01 | 1 | CON-01, CON-02 | — | N/A | unit | `pytest tests/test_metrics.py -q` | ✅ | ⬜ pending |
| 05-01-03 | 01 | 1 | CON-01, CON-02 | — | N/A | unit | `pytest tests/test_metrics.py tests/test_aggregation.py -q` | ✅ | ⬜ pending |
| 05-02-01 | 02 | 1 | CON-02, CON-03 | — | N/A | unit | `pytest tests/test_aggregation.py -q` | ✅ | ⬜ pending |
| 05-02-02 | 02 | 1 | CON-03 | — | N/A | unit | `pytest tests/test_aggregation.py -q` | ✅ | ⬜ pending |
| 05-02-03 | 02 | 1 | CON-02, CON-03 | — | N/A | unit | `pytest tests/test_run_benchmark.py -q` | ✅ | ⬜ pending |
| 05-03-01 | 03 | 2 | CON-01, CON-02, CON-03 | — | N/A | unit | `pytest tests/test_aggregation.py tests/test_metrics.py -q` | ✅ | ⬜ pending |
| 05-03-02 | 03 | 2 | CON-01, CON-02, CON-03 | — | N/A | unit | `pytest tests/test_docs.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_metrics.py` exists (assertions to be updated per D-17)
- [x] `tests/test_aggregation.py` exists (new tests to be added per D-18)
- [x] `tests/test_run_benchmark.py` exists (integration test for `_batch_row` may need new test for unmeasured row)
- [x] `tests/test_docs.py` exists (may need new doc test for nullability wording)
- [x] `tests/conftest.py` exists (`sample_run_result` is a "measured" example; new fixture optional)
- [x] pytest framework is project test dep

*Existing infrastructure covers all phase requirements — no Wave 0 framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docs/adapter-guide.md` paragraph wording is clear and reflects the nullability change | CON-01 | Doc text is prose; automated test only checks for keyword presence | After Plan 03 lands, read the "Metrics And Status Semantics" section and the "RunResult" field list; verify the `null` vs `0` distinction is explicit. |

*One manual verification only — the rest are unit tests against the contract change.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
