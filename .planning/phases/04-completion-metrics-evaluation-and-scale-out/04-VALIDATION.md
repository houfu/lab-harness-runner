---
phase: 4
slug: completion-metrics-evaluation-and-scale-out
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-01
---

# Phase 4 — Validation Strategy

> Nyquist-style validation contract for Phase 4 execution feedback. The phase is not complete until every gate below is green or explicitly documented as live-environment-only evidence.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 via project dev dependencies |
| **Config file** | `pyproject.toml`; existing `tests/conftest.py` |
| **Quick status/metrics command** | `uv run pytest tests/test_status.py tests/test_metrics.py -q` |
| **Quick command/report command** | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` |
| **Quick aggregation/docs command** | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **CLI smoke command** | `uv run python scripts/run_benchmark.py --help` |

---

## Sampling Rate

- **After every task commit:** run the task's targeted pytest command from the plan.
- **After every plan wave:** run `uv run pytest tests/ -q`.
- **Before Phase 4 verification:** run the full suite, `uv run python scripts/run_benchmark.py --help`, and the metadata pollution gate.
- **Max feedback latency:** keep autonomous checks under 60 seconds; live nanoclaw and judge-backed checks are checkpoint evidence, not unit feedback.

---

## Acceptance Gates

| Gate | Required Evidence | Command |
|------|-------------------|---------|
| G-04-STATUS | Raw adapter state and benchmark-facing status are recorded separately; timeout with valid deliverables can be benchmark-clean. | `uv run pytest tests/test_status.py tests/test_metrics.py -q` |
| G-04-REPORTS | The primary command preserves `scores.json` and `report.html` under `results/<run-id>/`. | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` |
| G-04-DASHBOARDS | Optional LAB compare/dashboard mode is score-dependent, records dashboard artifact paths, and never moves per-run LAB result folders. | `uv run pytest tests/test_run_benchmark.py -q` |
| G-04-BATCH | Multi-task/multi-seed runs write per-run LAB folders and metadata-only aggregate summaries. | `uv run pytest tests/test_aggregation.py tests/test_run_benchmark.py -q` |
| G-04-VARIANCE | Aggregate summaries include count, mean, min, max, and stdev where values are available before performance claims. | `uv run pytest tests/test_aggregation.py -q` |
| G-04-DOCS | Adapter guide documents the contract, failure semantics, metrics fields, and future adapter compatibility without implementing a second adapter. | `uv run pytest tests/test_docs.py -q` |
| G-04-POLLUTION | Batch metadata and dashboard preservation do not create aggregate `scores.json` files under LAB batch folders. | `uv run python -c "from pathlib import Path; raise SystemExit(1 if any(Path('/Users/houfu/Projects/harvey-labs/results').glob('batches/*/scores.json')) else 0)"` |

---

## Per-Plan Verification Map

| Plan | Wave | Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|-------------|----------|-----------|-------------------|-------------|--------|
| 04-01 | 1 | REQ-09, REQ-21 | Derive benchmark status from deliverable validation while preserving raw end_state/protocol diagnostics. | unit | `uv run pytest tests/test_status.py tests/test_metrics.py -q` | Wave 0 needed | pending |
| 04-02 | 2 | REQ-14, REQ-21 | Primary command runs adapter, validates deliverables, writes metrics, preserves LAB scores/reports, and optionally preserves compare/dashboard artifacts. | unit/CLI smoke | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` | Wave 0 needed | pending |
| 04-03 | 3 | REQ-15, REQ-21, REQ-22 | Batch task x seed loop writes normal LAB run folders plus metadata-only summaries and variance fields. | unit | `uv run pytest tests/test_aggregation.py tests/test_run_benchmark.py -q` | Wave 0 needed | pending |
| 04-04 | 4 | REQ-16, REQ-21 | Adapter guide documents the reusable contract and reporting semantics without adding a second adapter. | doc test | `uv run pytest tests/test_docs.py -q` | Wave 0 needed | pending |

---

## Wave 0 Requirements

- [ ] `tests/test_status.py` for benchmark status derivation and unsafe deliverable path rejection.
- [ ] `tests/test_metrics.py` additions for diagnostic fields and backwards-compatible metrics writing.
- [ ] `tests/test_run_benchmark.py` for primary command orchestration, report paths, optional `--compare task|area|all`, score dependency, unsafe inputs, and no result-folder moves.
- [ ] `tests/test_evaluator.py` report/compare helper assertions if evaluator helpers are added.
- [ ] `tests/test_aggregation.py` for metadata-only summaries and variance.
- [ ] `tests/test_docs.py` for adapter guide coverage.

---

## Manual / Live-Environment Checks

| Behavior | Requirement | Why Manual | Instructions |
|----------|-------------|------------|--------------|
| Live nanoclaw benchmark run | REQ-09, REQ-21 | Requires nanoclaw daemon, Docker, model runtime, and LAB task assets. | Run `uv run python scripts/run_benchmark.py --task corporate-ma/compare-matter-plan-against-engagement-letter --adapter nanoclaw --nanoclaw-dir /Users/houfu/Projects/nanoclaw-lq --group-id lab-runner --score --report`; confirm metrics preserve raw state and benchmark status. |
| LAB compare/dashboard generation | REQ-14 | Depends on LAB scored runs and local dashboard output behavior. | After at least one scored run, run the primary command with `--score --compare task`, then confirm returned dashboard paths exist and no `results/<run-id>/` folder was moved. |
| Judge-backed scoring | REQ-14, REQ-21 | Requires LAB judge API credentials and may make paid external calls. | Use `--score --report` only when credentials are configured; otherwise rely on mocked/unit scoring checks. |

---

## Phase Gate

Before marking Phase 4 complete:

```bash
uv run pytest tests/ -q
uv run python scripts/run_benchmark.py --help
uv run python -c "from pathlib import Path; raise SystemExit(1 if any(Path('/Users/houfu/Projects/harvey-labs/results').glob('batches/*/scores.json')) else 0)"
```

The live nanoclaw/judge checks must be documented in Phase 4 summary, UAT, or verification artifacts when the environment is available. If not available, the gap must be explicitly recorded as environment-blocked rather than silently passed.

---

## Validation Sign-Off Checklist

- [ ] Every Phase 4 task has an automated verification command.
- [ ] Reports and dashboards are both covered for REQ-14.
- [ ] Deterministic seeds are not overclaimed; seed is metadata/iteration ID unless adapter support is verified.
- [ ] Per-run LAB folders remain under `results/<run-id>/` and are not moved.
- [ ] No aggregate `scores.json` is created under `results/batches/`.
- [ ] Full suite and CLI smoke pass.
