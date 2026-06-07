# lab-nanoclaw

## Purpose

Build a harness-agnostic runner package that can execute Harvey LAB tasks through
external agent harnesses, starting with nanoclaw-lq, and score those runs using
LAB's existing evaluator and reporting pipeline.

## Scope

This project owns the glue around LAB task reading, result directory creation,
adapter invocation, metrics capture, evaluator invocation, and run aggregation.
It treats Harvey LAB as an unmodified dependency and nanoclaw-lq as the first
reference adapter.

## Goals

- Prove LAB scoring with a manually created output before integrating nanoclaw.
- Provide a narrow adapter contract:
  `run(task_spec, output_dir) -> RunResult`.
- Implement a nanoclaw-lq adapter that can run a LAB task and produce
  deliverables in LAB's expected output directory.
- Preserve LAB's existing `scores.json`, report, and dashboard generation.
- Record run end-state so harness failures are not silently treated as model
  failures.
- Document the adapter contract for future community harnesses.

## Non-Goals

- Do not fork or modify Harvey LAB.
- Do not replace LAB's evaluator or reporting system.
- Do not implement speculative additional adapters before a real second harness
  needs one.
- Do not make package-owned code responsible for harness sandboxing.

## Runtime And Tooling

- Language/runtime: Python, managed with `uv`.
- Command convention: use `uv run ...` for project commands.
- Formatting: `black`.
- External dependencies: a local Harvey LAB clone, nanoclaw-lq, Docker for
  nanoclaw, and LAB's judge API configuration.

## Locked Decisions

<decisions>
- Harvey LAB is an unmodified dependency; this project must not edit or fork it.
- Integration depends on LAB's filesystem and evaluator surfaces: task metadata,
  result directories, and `evaluation.run_eval`.
- nanoclaw-lq runs in its own Docker container, not inside LAB's podman sandbox.
- Deliverables should land directly in `results/<run-id>/output/`.
- Run completion is detected by a structured terminal `STATUS:` signal plus a
  wall-clock timeout.
- The runner records whether each run ended cleanly, with agent error, or by
  timeout.
- LAB remains the source of scoring and report generation.
- The reusable adapter interface is `run(task_spec, output_dir) -> RunResult`.
- The first implemented adapter is nanoclaw-lq.
- Use `uv` and `black`.
</decisions>

## Success Metric

A single LAB task can be run through nanoclaw-lq end to end, producing expected
deliverables, `metrics.json`, LAB `scores.json`, and a recorded run end-state
without modifying LAB.

## Shipped Milestone: v1.1 — Post-v1.0 hardening & metrics fidelity ✅ (2026-06-08)

**Goal:** Make nanoclaw-backed metrics honest (measured vs. unmeasured) and
harden the post-v1.0 sweep driver, without changing the runner's role as a
thin orchestrator over Harvey LAB. **Shipped:** 3 phases, 10 plans, 19 tasks,
141 tests passing. All 10 requirements (CON-01..03, EXT-01..04, SWP-01..04,
LAB-01..02) verified.

**Target features:**

- Honest "unmeasured" semantics in `RunResult` & `metrics.json` (CON-01..03).
- `MetricsExtractor` protocol with an `AnthropicUsageExtractor` reading
  `usage` from nanoclaw's transcript jsonl, plus a document-read extractor
  and model-based routing that returns nulls for the Ollama path
  (EXT-01..04).
- `sweep.sh` hardening grounded in observed `results/` wall-clock data,
  dual-output `inventory`, post-run summary, non-zero exit with per-run
  stderr, and an opt-in flag that shells out to LAB's `evaluation.compare`
  (SWP-01..04, LAB-01..02).

## Current State

**Shipped:** v1.0 MVP (2026-06-02) — Phases 1-4, 13 plans, 99 tests passing.
v1.1 Post-v1.0 hardening & metrics fidelity (2026-06-08) — Phases 5-7, 10 plans,
141 tests passing.

The success metric is met: one LAB task (`corporate-ma/compare-matter-plan-against-engagement-letter`)
ran end to end through the nanoclaw-lq adapter, producing
`discrepancy-analysis-memo.docx`, `metrics.json`, and a recorded run end-state.
The same task served as the v1.1 Phase 6 live verification, confirming real
token + document-read extraction from the nanoclaw transcript.

**Post-v1.0 merges (4 Jun 2026, outside GSD):** `5974d69` (deliverable-gated
poll + ephemeral groups), `637228c` (per-run agent model), `3a1fd89`
(resumable parallel sweep driver), `17d3eb7` (FD-exhaustion / xargs-abort
fix), `3e0dd71` (TIMEOUT knob), `2884ae7` (destroy-shim stderr surfacing).
v1.1 Phase 7 hardens these commits and gives them a GSD-tracked verification
path. The 4 Jun 1251-task sweep crashed ~193/1251 with ENFILE before the FD
fix; the 600 s `TIMEOUT` default is empirically defensible (p99 of 137 clean
runs = 586.2s, max = 596.1s).

**Root gap of v1.1 — RESOLVED:** `RunResult` previously declared `int | None`
for token/coverage fields, but `NanoclawAdapter.run()` never populated them and
`write_metrics` silently coerced `None → 0`. v1.1 closed this end-to-end:
CON-01..03 made the contract honest (null-vs-zero), EXT-01..04 added real
transcript extraction, and the Phase 6 live run proved real values flow to
`metrics.json` (`input_tokens=436181`, `output_tokens=4701`, 2 documents read).
The live run also surfaced + fixed a D-19 session-id mismatch (the nanoclaw
agent-shared session id never matches Claude's in-container session UUID, so
the per-group transcript is now resolved by fallback — commit `1f928fd`).

### Validated

- ✓ Harness-neutral package core (`TaskSpec`/`RunResult`/`Adapter` protocol, task
  reader, result builder, metrics writer, evaluator wrapper) — v1.0
- ✓ nanoclaw-lq adapter: Node dispatch shim, read-only doc / read-write output
  mounts, `STATUS:` poll loop, wall-clock timeout — v1.0
- ✓ LAB evaluator invocation preserving `scores.json`, reports, and dashboards — v1.0
- ✓ Run end-state recording (clean / agent-error / timeout) plus benchmark status
  semantics (timeout-with-deliverable → benchmark-clean) — v1.0
- ✓ Multi-task / multi-seed batch aggregation with variance reporting — v1.0
- ✓ Documented third-party adapter contract — v1.0
- ✓ Deliverable-gated poll short-circuit + ephemeral per-run nanoclaw groups
  (`5974d69`) — post-v1.0
- ✓ Optional per-run agent model with Ollama routing for non-claude models
  (`637228c`) — post-v1.0
- ✓ Resumable parallel `sweep.sh` with FD-exhaustion fix, `TIMEOUT` knob, and
  destroy-shim stderr surfacing (`3a1fd89`, `17d3eb7`, `3e0dd71`, `2884ae7`)
  — post-v1.0
- ✓ Honest unmeasured-metrics contract: nullable `RunResult` fields,
  `write_metrics` propagates `None`→JSON `null`, per-row `metrics_provided` +
  `unmeasured_counts` + list-variance lengths in aggregation (CON-01..03)
  — Validated in Phase 5 (v1.1)
- ✓ `MetricsExtractor` protocol + `AnthropicUsageExtractor` (D-05 cache fold),
  document-read extractor, and model-routed selection wired into the nanoclaw
  adapter (Ollama path returns nulls without raising); D-19 per-group
  transcript resolution proven against a live claude-opus-4-8 run
  (EXT-01..04) — Validated in Phase 6 (v1.1)
- ✓ Hardened `sweep.sh` driver: documented `TIMEOUT` rationale, CI-consumable
  `inventory` dual-output, post-run `summary:` line, non-zero exit on hard
  failure, and opt-in `LAB_COMPARE` shell-out to LAB's `evaluation.compare`
  (no new runner aggregator) — Validated in Phase 7 (v1.1)

### Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| LAB is an unmodified dependency, integrated via filesystem/evaluator surfaces | Keep runner portable and avoid forking LAB | ✓ Good |
| Adapter contract `run(task_spec, output_dir) -> RunResult` | Narrow, reusable boundary for future harnesses | ✓ Good |
| Completion = terminal `STATUS:` signal + wall-clock timeout | Distinguish clean completion from hangs | ✓ Good |
| Benchmark status derives clean from valid deliverables while preserving raw `end_state: timeout` | Honest reporting when output exists but no terminal signal observed | ✓ Resolved by v1.1 (real metrics path replaces the gap that surfaced this Revisit) |
| Node dispatch shim lives in the nanoclaw-lq repo (Option A) | Avoid reimplementing nanoclaw message protocol in Python | ✓ Good |
| Anthropic token usage lives in nanoclaw's transcript jsonl, not `messages_out` | Discovered during v1.1 planning; verified against the v1.0 proof group `820628bb-c260-4bb4-bd60-b5a3b9ce4f58` | ✓ Good (v1.1 Phase 6) |
| Sweep driver `TIMEOUT` 600s default | Empirically defends p99 of clean runs (586.2s) while bounding non-deliverable stalls; rationalised in v1.1 Phase 7 | ✓ Good (v1.1 Phase 7) |
| Sweep driver shells out to LAB's `evaluation.compare` for aggregation; no new aggregator lives in the runner | Keep the runner thin; defer to Harvey LAB | ✓ Good (v1.1 Phase 7) |
| `MetricsExtractor` is a pluggable Protocol; Ollama path returns nulls without raising | Model-neutral default; future Ollama-aware extractor slots in without contract change | ✓ Good (v1.1 Phase 6) |

### Context / Known Limitations

- Live judge-backed scoring and real dashboard generation remain
  environment-dependent (require local credentials/runtime). Subprocess paths,
  artifact checks, and preservation behavior are tested.
- REQ-02: `read_task()` supports the verified current LAB shape
  (`task.json["instructions"]`). A move to `instructions.md` would be a contract change.
- Phase 3 lacks a formal `03-VERIFICATION.md`; closure evidence lives in UAT,
  security, validation, summaries, tests, and the proof deliverable.
- Cache-token handling (D-05): `AnthropicUsageExtractor` folds
  `cache_creation_input_tokens` and `cache_read_input_tokens` into the
  reported `input_tokens` total (live run example: 8904 raw + 62352 creation
  + 364925 read = 436181). This is a deliberate v1.1 choice; the raw split is
  not preserved separately. Downstream consumers wanting the discount-adjusted
  breakdown would need an extractor change (no contract change).
- Document-read metric records container-internal `file_path` strings (e.g.
  `/tmp/engagement.txt`) — not LAB `documents_dir` filenames. The contract
  is "what the agent read", not "what is in `documents_dir`".

## Next Milestone Goals

Deferred from v1.1, candidates for a later milestone:

- **REQ-23**: Additional adapters beyond nanoclaw-lq (deferred until a real
  second harness needs one). v1.1 deliberately did not include a second
  adapter; the `Adapter` contract remains unexercised in production.
- **REQ-24**: Public package publishing and broader community onboarding.
  v1.1 ships the metrics-honest contract that would be the natural
  reference point for a v1.1-era public release.
- **Upstream LAB documentation PR** for stable task/result contracts. v1.1
  adds a new coupling (sweep driver → LAB `evaluation.compare`) that
  becomes worth upstreaming once v1.1 has been used in production.
- **Per-task token / duration histogram in sweep driver** — deferred until
  v1.1 Phase 6 metrics extraction lands and gives real data to plot.
- **Tightening the deliverable-gated poll short-circuit** (introduced in
  `5974d69`) — deferred; v1.1 inherits the gate as-is, and tightening
  waits for any false-positive "deliverable present" cases to surface.

---

_Last updated: 2026-06-08 after v1.1 milestone (Post-v1.0 hardening & metrics fidelity)_
