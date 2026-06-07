---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Post-v1.0 hardening & metrics fidelity
status: Awaiting next milestone
last_updated: "2026-06-07T23:11:37.527Z"
last_activity: 2026-06-07 — Milestone v1.1 completed and archived
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 10
  completed_plans: 10
  percent: 100
---

# State

Updated: 2026-06-05

## Current Mode

Milestone v1.1 Post-v1.0 hardening & metrics fidelity in planning. Requirements
and roadmap are defined; awaiting phase execution.

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-05)

**Core value:** Run Harvey LAB tasks through external agent harnesses (starting with nanoclaw-lq) and score them with LAB's own evaluator, without modifying LAB.
**Current focus:** Phase 07 — sweep driver hardening and lab aggregation

## Source Documents

- `lab-nanoclaw-plan.md` classified as DOC.
- `.planning/REQUIREMENTS.md` v1.1 — 13 requirements across CON / EXT / SWP / LAB categories.
- `.planning/ROADMAP.md` v1.1 — 3 phases, 13/13 requirements mapped.

## Next Action

`/gsd:plan-phase 6` (or `/gsd:discuss-phase 6` to revisit context).

## Decisions

- NanoclawAdapter.run() stubbed with NotImplementedError — dispatch wired in Plan 02 (03-01)
- outbound_db fixture appended to conftest.py for shared use across tests (03-01)
- Mount configuration uses two hardcoded relative containerPaths (lab-documents, lab-output) — no caller-controlled paths (03-02)
- Central DB path is nanoclaw_dir/data/v2.db confirmed from nanoclaw-lq/src/index.ts (03-02)
- Shim JSON stdout carries both sessionId and outboundDbPath so adapter needs no path reconstruction (03-02)
- Phase 3 Plan 03 accepted deliverable presence as sufficient for the phase exit criterion while preserving `end_state: "timeout"` as a truthful metric. Phase 4 must clarify mixed states where output exists but no clean terminal STATUS signal is observed. (03-03)
- [Phase 04]: Timeout runs with all expected deliverables present derive benchmark_status=clean while preserving raw_end_state=timeout.
- [Phase 04]: Metrics diagnostics merge after LAB-compatible keys and omit JSON null values.
- [Phase 04]: run_benchmark.py is the primary nanoclaw benchmark CLI; nanoclaw_run.py delegates to it for compatibility.
- [Phase 04]: LAB compare/dashboard generation is score-dependent and preserves dashboard artifacts at LAB-created comparison paths.
- [Phase 04]: Batch summaries are metadata-only at results/batches/<batch-id>/summary.json and never create aggregate scores.json.
- [Phase 04]: Batch seeds are recorded as metadata only unless an adapter later implements deterministic seeding.
- [Phase 04]: Adapter documentation treats RunResult.end_state as raw protocol evidence and benchmark_status as deliverable-validation-derived reporting state.
- [Phase 04]: Second-adapter guidance is deferred checklist documentation only; no production adapter files were added.

## Notes

- Conflict gate passed with 0 blockers and 0 warnings.
- One informational conflict entry records that the source document was found by
  heuristic rather than directory convention.

- Phase 1 completed on 2026-05-30 with live LAB judge scoring left as an
  explicit manual command because it can require paid external API credentials.

- Phase 3 Plan 01 completed on 2026-05-31: NanoclawAdapter core logic (poll loop,
  end-state mapping, D-04/D-05 footer) implemented and unit-tested against synthetic
  outbound.db. 52 tests pass. Duration: 157 seconds.

- Phase 3 Plan 02 completed on 2026-05-31: Node shim (send-lab-message.ts) in nanoclaw-lq
  repo, NanoclawAdapter.run() wired (mounts + dispatch + poll + result), nanoclaw_run.py CLI,
  subprocess-mock dispatch test. 53 tests pass. Duration: ~480 seconds.

- Phase 4 Plan 03 completed on 2026-06-01: task x seed batch expansion, metadata-only
  aggregation under LAB results/batches, and variance fields across score/timing/token/document
  metrics. 86 tests pass. Duration: 5 minutes.

- Phase 4 Plan 04 completed on 2026-06-01: practical adapter guide, doc tests for
  required contract/status terms, and no second-adapter implementation. 89 tests
  pass. Duration: 2 minutes 26 seconds.

## Session Log

- 2026-05-31T00:32:39Z: Completed 03-01-PLAN.md (NanoclawAdapter core logic and tests)
- 2026-05-31T00:40:15Z: Completed 03-02-PLAN.md (dispatch shim, mount wiring, CLI, dispatch test)
- 2026-05-31: Paused 03-03-PLAN.md at blocking human-action checkpoint (Task 1) — awaiting mount-allowlist edit + Anthropic-Claude LAB group id. Phase verification intentionally NOT run; phase remains incomplete.
- 2026-06-01: Resumed 03-03-PLAN.md. Mount allowlist contains `/Users/houfu/Projects/harvey-labs`, nanoclaw logs show group `lab-runner` id `820628bb-c260-4bb4-bd60-b5a3b9ce4f58`, and proof deliverable exists for run `69f75ee0-84e2-44ca-a906-0bca7da7baae`; paused at human-verify because metrics recorded `end_state: "timeout"` rather than `clean`.
- 2026-06-01T02:53:47Z: User approved run `69f75ee0-84e2-44ca-a906-0bca7da7baae` as sufficient for Phase 3 despite `end_state: "timeout"` because the expected `discrepancy-analysis-memo.docx` exists and contains generated analysis. Created 03-03-SUMMARY.md and marked Phase 3 complete.
- 2026-06-01T16:09:10Z: Completed 04-01-PLAN.md (benchmark-facing status derivation and enriched metrics diagnostics). 62 tests pass.
- 2026-06-01T16:16:14Z: Completed 04-02-PLAN.md (primary benchmark command, report preservation, and optional LAB compare/dashboard paths). 78 tests pass.
- 2026-06-01T16:22:59Z: Completed 04-03-PLAN.md (multi-task/multi-seed aggregation and variance reporting). 86 tests pass; no aggregate scores.json under LAB results/batches.
- 2026-06-01T16:28:46Z: Completed 04-04-PLAN.md (practical adapter guide and second-adapter compatibility check). 89 tests pass; no second adapter production file added.
- 2026-06-05T05:30:00Z: Phase 5 context gathered. Decisions: per-row `metrics_provided` boolean + top-level `unmeasured_counts` (CON-03); `documents_read_list` / `documents_skipped_list` nullable on `RunResult` (CON-01); `_without_null_values` still strips `None` from `extra_fields`; list-field variance reports length statistics over measured rows. CONTEXT.md at `.planning/phases/05-honest-unmeasured-metrics-contract/05-CONTEXT.md`.
- 2026-06-05T08:35:54Z: Phase 6 context gathered. Decisions: `MetricsExtractor` Protocol returns full `RunResult` (replaces base adapter result after poll); routing predicate `model.startswith("claude")` selects AnthropicTranscriptExtractor, otherwise no-op; cache_creation + cache_read both folded into `input_tokens`; transcript resolved by `sessionId` match against `data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/*.jsonl`; container file paths kept verbatim in `documents_read_list`; live `--keep-failed` run on `corporate-ma/compare-matter-plan-against-engagement-letter` is verification only. CONTEXT.md at `.planning/phases/06-metrics-extraction-and-model-routing/06-CONTEXT.md`.

## Current Position

Phase: Milestone v1.1 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-06-07 — Milestone v1.1 completed and archived

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
