---
phase: 06-metrics-extraction-and-model-routing
plan: 01
subsystem: metrics-extraction
tags: [metrics-extractor, anthropic, transcript-jsonl, routing, protocol, no-op, documents-read]

# Dependency graph
requires:
  - phase: 05-honest-unmeasured-metrics-contract
    plan: any
    provides: RunResult with nullable token / coverage / list fields; null-vs-zero contract on disk
provides:
  - MetricsExtractor Protocol with extract(messages_out) -> RunResult contract (D-01, EXT-01)
  - AnthropicUsageExtractor reading nanoclaw transcript jsonl with cache fold (D-03..D-06, EXT-02)
  - DocumentReadExtractor enumerating Read tool_use blocks with dedup + verbatim paths (D-07, D-08, EXT-03)
  - AnthropicTranscriptExtractor composing the two Anthropic extractors (D-09)
  - NoOpExtractor for non-Claude models, never raises (D-10, EXT-04 Ollama clause)
  - is_claude_model routing predicate
affects: [06-02-PLAN (EphemeralNanoclawAdapter wiring), 06-03-PLAN (live schema discovery)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Protocol + @runtime_checkable so isinstance(x, MetricsExtractor) is a structural runtime check"
    - "Private _TranscriptReader base sharing the resolver and malformed-line iterator between the two Anthropic extractors"
    - "Combine (not deep inherit) for AnthropicTranscriptExtractor: thin compose of usage + docs with first-non-None merge"
    - "Routing decided at EphemeralNanoclawAdapter construction time (D-11) — no-op extractor does not need a path"
    - "D-05 cache fold: both cache_creation and cache_read summed into input_tokens; no sidecar field"
    - "D-08 verbatim file_path strings — no basename, no remapping against lab-documents"

key-files:
  created:
    - lab_harness_runner/metrics_extraction.py
    - tests/test_metrics_extraction.py
  modified: []

key-decisions:
  - "Used @runtime_checkable on the MetricsExtractor Protocol so callers (and the verify snippet) can do isinstance(x, MetricsExtractor) without an explicit subclass"
  - "Resolver scans the transcript_dir for *.jsonl files; for each candidate, iterates lines until a top-level sessionId match — defensive against prior-run jsonls in the same group dir (D-04)"
  - "AnthropicTranscriptExtractor is a thin compose class, not deep inheritance — keeps the two extractors' contracts distinct (D-09) and matches the optional Claude's Discretion shape in 06-CONTEXT"
  - "NoOpExtractor accepts and ignores any args via __init__(self, *args, **kwargs) for protocol uniformity; the routing decision is made before the class is constructed (D-10)"
  - "D-05 cache fold is implemented as a single-line sum on the usage block — no separate cache_total field, no sidecar, and the field is documented to consumers via adapter-guide (Plan 03 D-20)"

patterns-established:
  - "Pattern: a private _TranscriptReader base is the canonical shape for nanoclaw-transcript-backed extractors — future per-model extractors (Ollama, etc.) can reuse the iterator without inheriting the Anthropic-specific shape"
  - "Pattern: extractors always return RunResult with run_id=\"\"; the adapter overwrites run_id from task_spec (D-13 step 2 in Plan 02)"
  - "Pattern: malformed jsonl lines (json.JSONDecodeError, OSError) are skipped per line by the iterator; the resolver and the per-extractor scan never raise on bad data (D-06)"

requirements-completed: [EXT-01, EXT-02, EXT-03, EXT-04]

# Metrics
duration: 6min
completed: 2026-06-05
---

# Phase 6 Plan 1: Metrics Extractor Surface

**`MetricsExtractor` Protocol + four extractors + `is_claude_model` routing predicate, with a full D-16 unit-test suite against synthetic jsonl transcripts.**

## Performance

- **Duration:** 6 min 9 sec
- **Started:** 2026-06-05T09:44:23Z
- **Completed:** 2026-06-05T09:50:32Z
- **Tasks:** 2
- **Files created:** 2 (1 source, 1 test)
- **Files modified:** 0

## Accomplishments

- `lab_harness_runner/metrics_extraction.py` (new module) provides the read-side helper surface for v1.1 Phase 6: a `MetricsExtractor` Protocol (D-01), a private `_TranscriptReader` base with shared resolver + malformed-line-safe jsonl iterator, two Anthropic extractors (`AnthropicUsageExtractor` with D-05 cache fold; `DocumentReadExtractor` with D-07 dedup and D-08 verbatim paths), a thin compose class (`AnthropicTranscriptExtractor` per D-09), a `NoOpExtractor` that never raises, and the `is_claude_model` routing predicate (D-10).
- `tests/test_metrics_extraction.py` (new) covers all D-16 scenarios with a local `_write_transcript` helper that writes synthetic jsonl under `tmp_path / "v2-sessions" / "ag-test" / ".claude-shared" / "projects" / "-workspace-agent"` — 16 tests pass; full suite is 131 passed.
- The protocol is `@runtime_checkable` so `isinstance(x, MetricsExtractor)` is a structural runtime check (the verify snippet's runtime check exits 0).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create `lab_harness_runner/metrics_extraction.py`** - `62107ac` (feat)
2. **Task 2: Add `tests/test_metrics_extraction.py` covering all D-16 scenarios** - `852dcd1` (test)

## Files Created/Modified

- `lab_harness_runner/metrics_extraction.py` (new) — Protocol, four extractors, and `is_claude_model` helper.
- `tests/test_metrics_extraction.py` (new) — 16 tests covering all D-16 scenarios + a protocol structural check.
- No existing files were modified: `adapter.py`, `metrics.py`, `nanoclaw_adapter.py`, `__init__.py`, `scripts/run_benchmark.py`, `docs/adapter-guide.md` are all untouched (those are Plan 02 and Plan 03's wiring).

## Decisions Made

- **Added `@runtime_checkable` to the `MetricsExtractor` Protocol.** The verify snippet in the plan uses `isinstance(_N(), MetricsExtractor)` to confirm structural satisfaction. Python's `isinstance` against a `Protocol` requires `@runtime_checkable`; without it the runtime raises `TypeError`. This is a one-line addition that matches the plan's intent (structural check) and adds no behavior. Documented as a deviation (Rule 2 — missing critical functionality for the verify snippet to work).
- **Two-class shape for the Anthropic path:** kept `AnthropicUsageExtractor` and `DocumentReadExtractor` as distinct public classes that share a private `_TranscriptReader` base, then composed them in `AnthropicTranscriptExtractor` (D-09's "thin compose" rather than deep inheritance). This keeps the per-extractor contract clean for testing (the unit tests can target each in isolation) while still having a single class for the wiring surface in Plan 02.
- **NoOpExtractor accepts and ignores any args** via `__init__(self, *args, **kwargs)` for protocol uniformity. The routing decision is made before the class is constructed (D-10), so the no-op does not need a path. This is the simplest shape that satisfies "no-op MUST NOT raise" plus the protocol contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `@runtime_checkable` to `MetricsExtractor` Protocol.**
- **Found during:** Task 1 verification (the verify snippet's `isinstance(_N(), MetricsExtractor)` raised `TypeError: Instance and class checks can only be used with @runtime_checkable protocols`).
- **Issue:** The plan's verify snippet and acceptance criteria require `isinstance(_N(), MetricsExtractor)` to exit 0. Python's `Protocol` is not runtime-checkable by default; the decorator is required for `isinstance` to work. Without it, the protocol structural check is a static-typing check, not a runtime one.
- **Fix:** Added `@runtime_checkable` from `typing`. The protocol's surface (one `extract(messages_out: list[dict]) -> RunResult` method) is unchanged. The `import` line was extended from `from typing import Protocol` to `from typing import Protocol, runtime_checkable`.
- **Files modified:** `lab_harness_runner/metrics_extraction.py` (1 import, 1 decorator).
- **Commit:** `62107ac` (in Task 1).

**2. [Rule 2 - Missing critical functionality] Extracted `_TranscriptReader` as a private base class.**
- **Found during:** Task 1 implementation review. The plan describes `_TranscriptReader` as "a small private class" but the action block in the plan scatters the resolver and iterator across `AnthropicUsageExtractor` and `DocumentReadExtractor` in prose.
- **Issue:** Without a shared base, the resolver and iterator would be duplicated verbatim across the two extractors (D-04 + D-06 are the shared substrate).
- **Fix:** Extracted the resolver and iterator into `_TranscriptReader` (an underscore-prefixed private class) that both Anthropic extractors inherit from. The plan's prose explicitly approves this shape ("Both `AnthropicUsageExtractor` and `DocumentReadExtractor` inherit from it").
- **Files modified:** `lab_harness_runner/metrics_extraction.py` (added the private base class, both extractors now `class Foo(_TranscriptReader)`).
- **Commit:** `62107ac` (in Task 1).

No other deviations. The plan was otherwise executed exactly as written.

## Issues Encountered

- None at the code level. Both task verifications passed on the first run; the full test suite is green (131 passed, including the 16 new tests).

## Verification

The plan's verification block was executed end-to-end:

- `uv run --quiet python -m pytest tests/test_metrics_extraction.py -q` → **16 passed**.
- The `MetricsExtractor` Protocol is structurally satisfied by a class defining `extract(self, messages_out: list[dict]) -> RunResult` (runtime check exits 0).
- `is_claude_model("claude-opus-4-8")` is `True`; `is_claude_model(None)`, `is_claude_model("")`, `is_claude_model("deepseek-v4-flash:cloud")`, `is_claude_model("Ollama")`, `is_claude_model("Claude-opus-4-8")` (case-sensitivity check) are all `False`.
- D-16 anchor values verified: two assistant lines (input=2587+9846=12433, output=181+89688=89869).
- D-05 cache fold verified: `input_tokens=350` (100+50+200), `output_tokens=30`.
- D-07 dedup verified: two `Read` blocks for the same path yield `["/tmp/engagement.txt"]` (length 1).
- D-08 verbatim paths verified: `Bash` and other non-Read tool_use blocks contribute nothing.
- D-06 malformed lines verified: `not-json-at-all` interleaved with a valid line yields the valid line's contribution; no exception.
- D-04 missing transcript verified: `AnthropicUsageExtractor(transcript_dir=tmp_path / "no-such-dir", session_id="x")` returns all `None` and does not raise.
- D-09 combined path verified: `AnthropicTranscriptExtractor` returns a `RunResult` with BOTH `input_tokens == 100` AND `documents_read_list == ["/tmp/engagement.txt"]` populated.
- Full test suite: `uv run --quiet python -m pytest -q` → **131 passed in 1.28s** (115 from Phase 5 + 16 new).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 Plan 2 (the wiring into `EphemeralNanoclawAdapter`) can now run: it owns the `EphemeralNanoclawAdapter.__init__` change that picks `AnthropicTranscriptExtractor` vs `NoOpExtractor` via `is_claude_model(self.model)` (D-11), and the `EphemeralNanoclawAdapter.run()` step that calls the extractor after the poll loop and replaces the base `RunResult` (D-13).
- The `MetricsExtractor` Protocol contract is now locked in: any future Ollama-aware extractor (a deferred item per PROJECT.md) can implement `extract(messages_out)` and slot into the same `EphemeralNanoclawAdapter` wiring without an adapter-side contract change.
- The live `--keep-failed` run on `corporate-ma/compare-matter-plan-against-engagement-letter` (D-18) is Plan 03's concern; Plan 02's wiring should be exercised against the synthetic fixtures in `tests/test_metrics_extraction.py` and the new `tests/test_nanoclaw_adapter.py::test_ephemeral_extracts_metrics_for_claude_model` (per 06-CONTEXT D-16).
- No blockers; all plan success criteria met.

## Self-Check: PASSED

- `lab_harness_runner/metrics_extraction.py` exists on disk (created in commit `62107ac`).
- `tests/test_metrics_extraction.py` exists on disk (created in commit `852dcd1`).
- Commit `62107ac` (Task 1) is reachable in `git log --oneline`.
- Commit `852dcd1` (Task 2) is reachable in `git log --oneline`.
- `uv run --quiet python -c "from lab_harness_runner.metrics_extraction import ..."` exits 0.
- `uv run --quiet python -m pytest tests/test_metrics_extraction.py -q` exits 0 with 16 passed.
- `uv run --quiet python -m pytest -q` exits 0 with 131 passed (115 from Phase 5 + 16 new).
- No modifications to `adapter.py`, `metrics.py`, `nanoclaw_adapter.py`, `__init__.py`, `scripts/run_benchmark.py`, `docs/adapter-guide.md`, or any existing test file (per the plan's "Do NOT add to this plan" list).

---

*Phase: 06-metrics-extraction-and-model-routing*
*Completed: 2026-06-05*
