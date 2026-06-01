---
phase: 4
slug: completion-metrics-evaluation-and-scale-out
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-01
verified: 2026-06-02
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

| Gate | Required Evidence | Command | Observed Result | Status |
|------|-------------------|---------|-----------------|--------|
| G-04-STATUS | Raw adapter state and benchmark-facing status are recorded separately; timeout with valid deliverables can be benchmark-clean. | `uv run pytest tests/test_status.py tests/test_metrics.py -q` | 18 passed in 0.02s | green |
| G-04-REPORTS | The primary command preserves `scores.json` and `report.html` under `results/<run-id>/`. | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` | 35 passed in 0.04s | green |
| G-04-DASHBOARDS | Optional LAB compare/dashboard mode is score-dependent, records dashboard artifact paths, and never moves per-run LAB result folders. | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` | 35 passed in 0.04s | green |
| G-04-BATCH | Multi-task/multi-seed runs write per-run LAB folders and metadata-only aggregate summaries. | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q` plus full suite | 8 passed in 0.01s; 93 passed in 0.73s | green |
| G-04-VARIANCE | Aggregate summaries include count, mean, min, max, and stdev where values are available before performance claims. | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q` | 8 passed in 0.01s | green |
| G-04-DOCS | Adapter guide documents the contract, failure semantics, metrics fields, and future adapter compatibility without implementing a second adapter. | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q` | 8 passed in 0.01s | green |
| G-04-POLLUTION | Batch metadata and dashboard preservation do not create aggregate `scores.json` files under LAB batch folders. | `find /Users/houfu/Projects/harvey-labs/results/batches -path '*/scores.json' -print -quit 2>/dev/null \| wc -l` | 0 | green |

---

## Per-Plan Verification Map

| Plan | Wave | Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|-------------|----------|-----------|-------------------|-------------|--------|
| 04-01 | 1 | REQ-09, REQ-21 | Derive benchmark status from deliverable validation while preserving raw end_state/protocol diagnostics. | unit | `uv run pytest tests/test_status.py tests/test_metrics.py -q` | yes: `tests/test_status.py`, `tests/test_metrics.py` | covered/passed |
| 04-02 | 2 | REQ-14, REQ-21 | Primary command runs adapter, validates deliverables, writes metrics, preserves LAB scores/reports, and optionally preserves compare/dashboard artifacts. | unit/CLI smoke | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q`; `uv run python scripts/run_benchmark.py --help` | yes: `tests/test_run_benchmark.py`, `tests/test_evaluator.py` | covered/passed |
| 04-03 | 3 | REQ-15, REQ-21, REQ-22 | Batch task x seed loop writes normal LAB run folders plus metadata-only summaries and variance fields. | unit/integration | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q`; `uv run pytest tests/ -q` | yes: `tests/test_aggregation.py`, `tests/test_run_benchmark.py` | covered/passed |
| 04-04 | 4 | REQ-16, REQ-21 | Adapter guide documents the reusable contract and reporting semantics without adding a second adapter. | doc test | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q` | yes: `tests/test_docs.py`, `docs/adapter-guide.md` | covered/passed |

---

## Wave 0 Requirements

- [x] `tests/test_status.py` for benchmark status derivation and unsafe deliverable path rejection.
- [x] `tests/test_metrics.py` additions for diagnostic fields and backwards-compatible metrics writing.
- [x] `tests/test_run_benchmark.py` for primary command orchestration, report paths, optional `--compare task|area|all`, score dependency, unsafe inputs, and no result-folder moves.
- [x] `tests/test_evaluator.py` report/compare helper assertions if evaluator helpers are added.
- [x] `tests/test_aggregation.py` for metadata-only summaries and variance.
- [x] `tests/test_docs.py` for adapter guide coverage.

---

## Manual / Live-Environment Checks

| Behavior | Requirement | Why Manual | Instructions |
|----------|-------------|------------|--------------|
| Live nanoclaw benchmark run | REQ-09, REQ-21 | Requires nanoclaw daemon, Docker, model runtime, and LAB task assets. | Environment-dependent/manual-only. Run `uv run python scripts/run_benchmark.py --task corporate-ma/compare-matter-plan-against-engagement-letter --adapter nanoclaw --nanoclaw-dir /Users/houfu/Projects/nanoclaw-lq --group-id lab-runner --score --report`; confirm metrics preserve raw state and benchmark status. Not blocking automated Nyquist coverage because the adapter boundary is covered by behavioral tests. |
| LAB compare/dashboard generation | REQ-14 | Depends on LAB scored runs and local dashboard output behavior. | Environment-dependent/manual-only. After at least one scored run, run the primary command with `--score --compare task`, then confirm returned dashboard paths exist and no `results/<run-id>/` folder was moved. Not blocking automated Nyquist coverage because compare path creation, stale-dashboard detection, and score dependency are covered in `tests/test_evaluator.py` and `tests/test_run_benchmark.py`. |
| Judge-backed scoring | REQ-14, REQ-21 | Requires LAB judge API credentials and may make paid external calls. | Environment-dependent/manual-only. Use `--score --report` only when credentials are configured; otherwise rely on mocked/unit scoring checks. Not blocking automated Nyquist coverage because subprocess invocation, deliverable prechecks, and artifact path preservation are covered by tests. |

---

## Phase Gate

Before marking Phase 4 complete:

```bash
uv run pytest tests/ -q
uv run python scripts/run_benchmark.py --help
uv run python -c "from pathlib import Path; raise SystemExit(1 if any(Path('/Users/houfu/Projects/harvey-labs/results').glob('batches/*/scores.json')) else 0)"
```

Live nanoclaw, LAB judge, and real dashboard generation checks are operational checks, not automated Nyquist blockers. They remain documented above as manual-only because they require local services, credentials, scored LAB data, or paid external calls.

---

## Post-Execution Audit Trail

| Date | Command | Observed Result | Status |
|------|---------|-----------------|--------|
| 2026-06-02 | `uv run pytest tests/test_status.py tests/test_metrics.py -q` | 18 passed in 0.02s | green |
| 2026-06-02 | `uv run pytest tests/test_run_benchmark.py tests/test_evaluator.py -q` | 35 passed in 0.04s | green |
| 2026-06-02 | `uv run pytest tests/test_aggregation.py tests/test_docs.py -q` | 8 passed in 0.01s | green |
| 2026-06-02 | `uv run pytest tests/ -q` | 93 passed in 0.73s | green |
| 2026-06-02 | `uv run python scripts/run_benchmark.py --help` | usage printed with single-run, batch, score, report, compare, and judge-model flags | green |
| 2026-06-02 | `find /Users/houfu/Projects/harvey-labs/results/batches -path '*/scores.json' -print -quit 2>/dev/null \| wc -l` | 0 | green |

## Requirement Coverage

| Requirement | Coverage | Evidence | Status |
|-------------|----------|----------|--------|
| REQ-09 | Status/protocol/deliverable semantics: timeout with valid deliverables is benchmark-clean while raw timeout remains diagnostic. | `tests/test_status.py`; `tests/test_metrics.py`; `lab_harness_runner/status.py`; `lab_harness_runner/metrics.py` | filled |
| REQ-14 | Score/report/dashboard preservation and safe compare behavior, including score dependency and stale/missing dashboard failures. | `tests/test_run_benchmark.py`; `tests/test_evaluator.py`; `scripts/run_benchmark.py`; `lab_harness_runner/evaluator.py` | filled |
| REQ-15 | Multi-task/multi-seed batch runs with normal per-run LAB folders and metadata-only batch summaries. | `tests/test_run_benchmark.py`; `tests/test_aggregation.py`; `scripts/run_benchmark.py`; `lab_harness_runner/aggregation.py` | filled |
| REQ-16 | Adapter guide contract documentation without adding a second adapter. | `tests/test_docs.py`; `docs/adapter-guide.md` | filled |
| REQ-21 | Whole agent-system outcome reporting across metrics, command output, batch rows, and docs. | `tests/test_metrics.py`; `tests/test_run_benchmark.py`; `tests/test_aggregation.py`; `tests/test_docs.py` | filled |
| REQ-22 | Variance reporting before claims: count, mean, min, max, stdev for score and operational metrics where values are present. | `tests/test_aggregation.py`; `lab_harness_runner/aggregation.py` | filled |
| No aggregate `scores.json` under LAB `results/batches` | Batch writer uses `summary.json`; filesystem gate confirmed zero matching files. | `tests/test_aggregation.py`; `tests/test_run_benchmark.py`; pollution command | filled |

---

## Validation Sign-Off Checklist

- [x] Every Phase 4 task has an automated verification command.
- [x] Reports and dashboards are both covered for REQ-14.
- [x] Deterministic seeds are not overclaimed; seed is metadata/iteration ID unless adapter support is verified.
- [x] Per-run LAB folders remain under `results/<run-id>/` and are not moved.
- [x] No aggregate `scores.json` is created under `results/batches/`.
- [x] Full suite and CLI smoke pass.
