# Milestones

## v1.1 Post-v1.0 hardening & metrics fidelity (Shipped: 2026-06-07)

**Phases completed:** 3 phases, 10 plans, 19 tasks

**Key accomplishments:**

- RunResult list fields are now nullable and write_metrics propagates `None` to JSON `null` on disk — the core of CON-01 and the on-disk half of CON-02.
- Per-row metrics_provided boolean + top-level unmeasured_counts + list-variance lengths block; row normalisation and _batch_row pass null through unchanged.
- Aggregation tests assert the new `metrics_provided` / `unmeasured_counts` / list-`lengths` shape; the adapter guide documents the null-vs-zero contract and a regression doc test guards the new wording.
- `MetricsExtractor` Protocol + four extractors + `is_claude_model` routing predicate, with a full D-16 unit-test suite against synthetic jsonl transcripts.
- EphemeralNanoclawAdapter now routes by `is_claude_model(self.model)` to a deferred Anthropic or no-op extractor at __init__ time, invokes the extractor after the poll loop, merges token / coverage fields with the base result, and logs a D-14 breadcrumb on missing transcript — backed by end-to-end integration tests and D-17 metrics_provided tests.
- D-20 docs addendum (MetricsExtractor extension point, Anthropic vs no-op routing rule, cache fold note) added to `docs/adapter-guide.md` and regression-locked by a new doc test. The D-18 / D-19 live verification run on `corporate-ma/compare-matter-plan-against-engagement-letter` is deferred to the operator — Task 2 of this plan is `checkpoint:human-verify` (operator-executed) and is OUT OF SCOPE for autonomous execution.
- TIMEOUT 600s documented with p99=586.2s/n=137/max=596.1s rationale; inventory() rewritten to emit human-readable counts header + bare result-directory paths consumable by xargs with no FAILED/MISSING: prefix
- Per-run .attempted/.failed marker tracking in run_one plus tally_summary() and check_failures() giving CI a pass-rate summary line and actionable non-zero exit with per-failed-run log paths
- Code review of four post-v1.0 sweep.sh commits with verified git facts; replay of hardened inventory against 170-run live results confirms 136 clean + 34 timeout and reconciles ROADMAP's stale 174 figure

---

## v1.0 MVP (Shipped: 2026-06-02)

**Phases completed:** 4 phases, 13 plans, 25 tasks

**Stats:** 91 files changed (+14,719 / −74) · 99 tests passing · 2026-05-30 → 2026-06-02

**Requirements:** 22/22 active satisfied; 2/2 deferred accounted for (REQ-23 additional adapters, REQ-24 public publishing)

**Key accomplishments:**

- Verified live LAB and nanoclaw-lq contracts and proved LAB scoring with a hand-made result skeleton
- Built a harness-neutral package core: `TaskSpec`/`RunResult`/`Adapter` protocol, task reader, result builder, metrics writer, and LAB evaluator wrapper
- Implemented the nanoclaw-lq adapter with a Node dispatch shim, read-only document / read-write output mounts, `STATUS:` poll loop, and wall-clock timeout
- Ran one LAB task end-to-end through nanoclaw, producing the expected `discrepancy-analysis-memo.docx` deliverable
- Added benchmark status semantics (timeout-with-deliverable → benchmark-clean) and a primary benchmark command preserving LAB score, report, and dashboard artifacts
- Added multi-task/multi-seed batch aggregation with variance reporting and a practical third-party adapter guide

---
