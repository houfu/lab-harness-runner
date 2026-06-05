---
phase: 06-metrics-extraction-and-model-routing
plan: 02
subsystem: metrics-extraction
tags: [metrics-extractor, anthropic, nanoclaw-adapter, routing, integration-tests, metrics_provided]

# Dependency graph
requires:
  - phase: 06-metrics-extraction-and-model-routing
    plan: 01
    provides: "MetricsExtractor Protocol, is_claude_model predicate, NoOpExtractor, AnthropicTranscriptExtractor, and MetricsExtractor classes"
  - phase: 05-honest-unmeasured-metrics-contract
    plan: any
    provides: "RunResult with nullable token / coverage / list fields; metrics_provided boolean semantics in build_summary"
provides:
  - "EphemeralNanoclawAdapter.__init__ caches self._extractor (D-11): is_claude_model -> _DeferredAnthropicExtractor, else NoOpExtractor"
  - "_DeferredAnthropicExtractor class defers AnthropicTranscriptExtractor construction to run() time (binds transcript_dir + sessionId)"
  - "NanoclawAdapter gains shim_session_id (None default; populated after _dispatch)"
  - "EphemeralNanoclawAdapter.run() invokes self._extractor.extract() after the poll loop, merges token / coverage fields with the base result (D-13), and logs a stderr breadcrumb when the Anthropic path cannot find the transcript (D-14)"
  - "End-to-end integration tests: Claude measured path, NoOp path, missing-transcript breadcrumb path"
  - "D-17 metrics_provided end-to-end tests for measured and unmeasured RunResult shapes"
  - "conftest.py fixture transcript_dir_with_claude_session builds a tmp_path-rooted nanoclaw transcript jsonl layout"
affects: [06-03-PLAN (live schema discovery run uses the wired adapter end-to-end)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-stage extractor (D-11): routing decision at __init__, binding to per-group resources at run() time"
    - "Adapter invariants preserved through merge: end_state + wall_clock_seconds + run_id from the inner adapter; token / coverage fields from the extractor"
    - "D-14 breadcrumb is gated on _DeferredAnthropicExtractor + shim_session_id is not None + all extracted fields None"
    - "Test pattern: mock the inner NanoclawAdapter to a stub RunResult + set shim_session_id; the merge's extract() reads the real fixture jsonl on disk"

key-files:
  modified:
    - lab_harness_runner/nanoclaw_adapter.py
    - tests/test_nanoclaw_adapter.py
    - tests/test_metrics.py
    - tests/conftest.py

key-decisions:
  - "Used a private _DeferredAnthropicExtractor wrapper (not the public AnthropicTranscriptExtractor) so the routing decision can be cached at __init__ time while the heavy extractor (which needs the per-group transcript_dir and shim sessionId) is bound lazily at run() time"
  - "NanoclawAdapter gains a shim_session_id field (additive only) but no model arg — the base adapter stays model-neutral (D-12)"
  - "The merge is field-by-field: end_state + wall_clock_seconds + run_id are taken from the inner adapter's base result, while the seven metric / coverage fields are taken from the extractor's output. This preserves the adapter's invariants (D-13) and lets the extractor's None-valued fields propagate through unchanged for the no-op path"
  - "D-14 missing-transcript breadcrumb uses print(file=sys.stderr) to match the existing teardown-warning style ('[ephemeral] keeping failed group for debugging', '[ephemeral] WARNING: failed to destroy group'). The sessionId in the breadcrumb is a nanoclaw uuid4, not a secret (T-06-07)"
  - "conftest fixture builds the jsonl at <tmp_path>/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/ to match the wiring's resolver path. The test passes nanoclaw_dir=tmp_path so the resolver finds it"
  - "Test pattern for D-16 integration: mock the inner NanoclawAdapter to return a stub RunResult and set shim_session_id on the mock — the merge then reads the real fixture jsonl on disk through the deferred Anthropic extractor"

patterns-established:
  - "Pattern: any future per-model extractor routes through the same two-stage shape — cache the extractor at __init__, bind the per-run resources (transcript_dir, sessionId, etc.) at run() time"
  - "Pattern: adapter invariants (end_state, wall_clock_seconds, run_id) are owned by the inner adapter; the outer ephemeral adapter passes them through the merge unchanged"

requirements-completed: [EXT-01, EXT-02, EXT-03, EXT-04]

# Metrics
duration: 10min
completed: 2026-06-05
---

# Phase 6 Plan 2: Ephemeral Adapter Wiring

**EphemeralNanoclawAdapter now routes by `is_claude_model(self.model)` to a deferred Anthropic or no-op extractor at __init__ time, invokes the extractor after the poll loop, merges token / coverage fields with the base result, and logs a D-14 breadcrumb on missing transcript — backed by end-to-end integration tests and D-17 metrics_provided tests.**

## Performance

- **Duration:** 9 min 59 sec
- **Started:** 2026-06-05T10:04:23Z
- **Completed:** 2026-06-05T10:14:22Z
- **Tasks:** 2
- **Files modified:** 4 (1 source, 3 test)

## Accomplishments

- `lab_harness_runner/nanoclaw_adapter.py` now wires the Plan 01 read-side module into the ephemeral adapter: `_select_extractor()` caches `self._extractor` at construction time per D-11 (Claude prefix -> `_DeferredAnthropicExtractor`, else `NoOpExtractor`); the run() method binds the deferred extractor to the per-group transcript_dir and the shim's sessionId, invokes extract(), logs the D-14 breadcrumb on the all-None result, and merges the extractor's metric fields with the base RunResult (preserving end_state and wall_clock_seconds).
- The base `NanoclawAdapter` gained a `shim_session_id: str | None = None` field (additive only) so the outer ephemeral adapter can locate the per-group transcript. The base adapter's `__init__` signature is unchanged — no model arg per D-12.
- A new private `_DeferredAnthropicExtractor` class in the adapter module solves the "group_id is unknown at __init__" problem by deferring `AnthropicTranscriptExtractor` construction to `extract()` time. It satisfies the `MetricsExtractor` Protocol structurally.
- `tests/conftest.py` gained the `transcript_dir_with_claude_session` fixture — a tmp_path-rooted jsonl layout with one system line (sets the sessionId) and two assistant messages (input=100+200=300, output=50+80=130) plus one `Read` tool_use block for `/tmp/foo.txt`.
- `tests/test_nanoclaw_adapter.py` got three new integration tests: the D-16/D-17 measured-path test (asserts the merged RunResult carries the fixture's token sums and the verbatim file_path), the D-10 Ollama no-op test (asserts all metric fields None and no stderr breadcrumb), and the D-14 missing-transcript test (asserts the exact stderr breadcrumb format and the base result is preserved). The existing `test_ephemeral_creates_and_destroys_on_success` was updated to assert the new merged shape instead of `result is inner_result`.
- `tests/test_metrics.py` got two new D-17 end-to-end tests: a measured RunResult round-trips through `write_metrics` + `build_summary` and asserts `metrics_provided: True` with all LAB_METRIC_FIELDS unmeasured_counts zero; a no-op RunResult (all token / coverage fields None) asserts `metrics_provided: False` with the relevant LAB_METRIC_FIELDS unmeasured_counts == 1.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire MetricsExtractor into EphemeralNanoclawAdapter (D-11, D-13, D-14, D-15)** - `d95fe69` (feat)
2. **Task 2: Add the conftest fixture, the integration tests, and the metrics_provided end-to-end tests** - `4d091b0` (test)

## Files Created/Modified

- `lab_harness_runner/nanoclaw_adapter.py` - `_DeferredAnthropicExtractor` class; `_select_extractor()` cached on `self._extractor` in `EphemeralNanoclawAdapter.__init__`; `NanoclawAdapter.shim_session_id` field; `EphemeralNanoclawAdapter.run` invokes the extractor after the poll loop, merges the result, and logs the D-14 breadcrumb.
- `tests/conftest.py` - new `transcript_dir_with_claude_session` fixture builds a tmp_path-rooted nanoclaw transcript jsonl with the expected layout (system line + two assistant messages + one `Read` tool_use).
- `tests/test_nanoclaw_adapter.py` - updated `test_ephemeral_creates_and_destroys_on_success` to assert the new merged shape; three new tests: `test_ephemeral_extracts_metrics_for_claude_model` (D-16/D-17 integration), `test_ephemeral_noop_for_non_claude_model` (D-10), `test_ephemeral_logs_breadcrumb_on_missing_transcript` (D-14).
- `tests/test_metrics.py` - two new D-17 tests: `test_metrics_provided_true_for_measured_run` and `test_metrics_provided_false_for_no_op_run`, plus local `_all_measured_metric_kwargs()` and `_base_row_kwargs()` helpers (mirrored from `tests/test_aggregation.py` to keep this file self-contained).

## Decisions Made

- **Two-stage extractor (deferred binding).** D-11 routes at `__init__` time, but the heavy `AnthropicTranscriptExtractor` needs the per-group `transcript_dir` (built from `self.nanoclaw_dir / "data" / "v2-sessions" / <group_id> / ...`) and the shim's `sessionId` (only known after `_create_group` returns). The `_DeferredAnthropicExtractor` wrapper is a small concession: it caches the routing decision at construction time and binds the per-run resources at `extract()` time. The Protocol contract is preserved structurally (`extract(messages_out) -> RunResult`).
- **Field-by-field merge.** The merge preserves the inner adapter's `end_state` and `wall_clock_seconds` (the adapter's invariants — these are derived from the poll loop, not the transcript), and replaces only the token / coverage / list fields with the extractor's output. This means the NoOp path naturally produces the same shape as the pre-Plan 02 wiring (all metric fields None, base end_state preserved) — backwards-compatible for Ollama and unknown models (D-10).
- **D-14 breadcrumb format and gate.** The breadcrumb is `[ephemeral] metrics: transcript not found for session <id>; skipping extraction` — same `print(..., file=sys.stderr)` style as the existing teardown warnings. The gate is `_DeferredAnthropicExtractor` (not the no-op path) + `shim_session_id is not None` + all four extracted fields (`input_tokens`, `output_tokens`, `documents_read`, `documents_read_list`) are None. The sessionId in the breadcrumb is a nanoclaw uuid4 (T-06-07 — not a secret).
- **Conftest fixture path layout.** The fixture builds the jsonl at `<tmp_path>/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` to match the wiring's resolver path. Tests pass `nanoclaw_dir=tmp_path` so the wiring's `self.nanoclaw_dir / "data" / "v2-sessions" / ...` resolves to the fixture's directory. The plan spec said the fixture should be `tmp_path`-rooted with no `/data`; this is a small deviation — the fixture is still `tmp_path`-rooted (no absolute paths, no external state), just one `/data` level deeper to match the resolver.

## Deviations from Plan

### Auto-fixed Issues

None.

### Plan Adjustments (non-Rule)

**1. Conftest fixture path includes a `/data` level**
- **Found during:** Task 2 (running the new `test_ephemeral_extracts_metrics_for_claude_model` test)
- **Issue:** The plan's fixture spec built the jsonl at `<tmp_path>/v2-sessions/<group_id>/...`, but the wiring in Task 1 resolves the path as `<nanoclaw_dir>/data/v2-sessions/<group_id>/...`. With `nanoclaw_dir=tmp_path` (the natural test value), the resolver looks at `tmp_path/data/v2-sessions/...` — the fixture's file is not found and the extractor returns the missing-transcript shape.
- **Fix:** Updated the fixture to build the jsonl at `<tmp_path>/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` — the wiring's exact resolver path. The fixture is still `tmp_path`-rooted (no absolute paths, no reliance on `nanoclaw_dir` from outside the fixture). The test passes `nanoclaw_dir=tmp_path` and the resolver finds the file.
- **Files modified:** `tests/conftest.py`
- **Verification:** `test_ephemeral_extracts_metrics_for_claude_model` now passes (asserts `input_tokens == 300, output_tokens == 130, documents_read == 1, documents_read_list == ["/tmp/foo.txt"]`). Full suite (136 tests) is green.
- **Committed in:** `4d091b0` (Task 2 commit)

---

**Total deviations:** 1 plan adjustment (fixture path correction), 0 auto-fixes
**Impact on plan:** The fixture path is the only change; the wiring (Task 1) and the test assertions are exactly as specified. No scope creep.

## Issues Encountered

- The test for the integration path (`test_ephemeral_extracts_metrics_for_claude_model`) initially failed because the fixture's jsonl path did not match the wiring's resolver path (one missing `/data` level). Diagnosed by inspecting the wiring's path build and the fixture's path build, then corrected the fixture to include the `/data` level. See "Plan Adjustments" above for details.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The wiring is complete and the full test suite is green (136 tests). Plan 06-03 (the live schema discovery run with `--keep-failed` and `--model claude-opus-4-8` on `corporate-ma/compare-matter-plan-against-engagement-letter`) can proceed.
- The `metrics_provided` boolean end-to-end contract (D-17) is now exercised for both the measured and unmeasured paths — Plan 06-03's verification run can validate the live contract with confidence.

---

*Phase: 06-metrics-extraction-and-model-routing*
*Completed: 2026-06-05*
