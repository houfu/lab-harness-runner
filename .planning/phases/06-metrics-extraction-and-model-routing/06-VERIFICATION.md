---
phase: 06-metrics-extraction-and-model-routing
verified: 2026-06-08T00:00:00Z
status: human_needed
score: 9/10 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run one live ephemeral-group task against a real nanoclaw-lq deployment with --model claude-opus-4-8 --keep-failed"
    expected: "metrics.json for the completed run contains non-null input_tokens and output_tokens matching the transcript's summed usage blocks, and a non-empty documents_read_list reflecting the agent's Read tool calls"
    why_human: "Requires docker daemon, nanoclaw-lq runtime, and a running Anthropic API key; cannot be exercised in unit tests; the ROADMAP exit criteria explicitly call this out as a required live verification step"
---

# Phase 6: Metrics Extraction and Model Routing — Verification Report

**Phase Goal:** Wire a `MetricsExtractor` protocol into the nanoclaw adapter so a run's `messages_out` is parsed (via the transcript) for token usage and document-read identifiers, with the right extractor selected by the configured model and the Ollama path returning null metrics without raising.

**Verified:** 2026-06-08

**Status:** human_needed

**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `MetricsExtractor` protocol importable from `lab_harness_runner.metrics_extraction` with `extract(messages_out) -> RunResult` contract; Protocol is `@runtime_checkable` | ✓ VERIFIED | `metrics_extraction.py` L50-60: `@runtime_checkable class MetricsExtractor(Protocol)` with one `extract` method; `isinstance` check confirmed working |
| 2 | `AnthropicUsageExtractor` sums `input_tokens` + `output_tokens` across assistant messages, folding cache fields; D-16 anchor: 2587+9846=12433, 181+89688=89869 | ✓ VERIFIED | `metrics_extraction.py` L162-167; live probe confirmed 12433/89869; `test_anthropic_usage_sums_two_assistant_messages` and `test_anthropic_usage_folds_cache_fields` pass |
| 3 | `DocumentReadExtractor` collects verbatim `file_path` from `Read` tool_use blocks, deduplicated with order preserved, leaving `documents_skipped*` as None | ✓ VERIFIED | `metrics_extraction.py` L183-252; `test_document_read_dedup` and `test_documents_skipped_fields_remain_none` pass; live dedup probe confirmed |
| 4 | `AnthropicTranscriptExtractor` composes both extractors and returns a single merged `RunResult` with both token and document fields populated | ✓ VERIFIED | `metrics_extraction.py` L255-319; `test_combined_anthropic_path_populates_both_fields` asserts `input_tokens == 100` AND `documents_read_list == ["/tmp/engagement.txt"]` |
| 5 | `NoOpExtractor` returns all token/coverage fields as `None`, never raises, ignores `messages_out` | ✓ VERIFIED | `metrics_extraction.py` L322-344; `test_noop_extractor_returns_none_metrics` and `test_noop_extractor_does_not_raise_on_non_dict_messages` pass |
| 6 | `is_claude_model` returns True for `claude` prefix, False for None/empty/other strings (case-sensitive) | ✓ VERIFIED | `metrics_extraction.py` L38-46; `test_is_claude_model_routes_correctly` covers all boundary cases including `Claude-opus-4-8` (capital C) → False |
| 7 | `EphemeralNanoclawAdapter` caches the right extractor at `__init__` time: claude-prefix → `_DeferredAnthropicExtractor`, else → `NoOpExtractor`; invokes it after poll loop; merges metric fields with base RunResult | ✓ VERIFIED | `nanoclaw_adapter.py` L415-542; runtime probe confirms `model='claude-opus-4-8'` → `_DeferredAnthropicExtractor`, `model=None` and `model='deepseek-v4-flash:cloud'` → `NoOpExtractor`; three integration tests pass |
| 8 | When Anthropic extractor cannot find transcript, adapter logs `[ephemeral] metrics: transcript not found for session <id>; skipping extraction` to stderr and returns base RunResult with None metric fields | ✓ VERIFIED | `nanoclaw_adapter.py` L513-525; `test_ephemeral_logs_breadcrumb_on_missing_transcript` asserts exact breadcrumb substring via `capsys` |
| 9 | Ollama path (non-claude model) returns null metrics without raising; no stderr breadcrumb emitted | ✓ VERIFIED | `nanoclaw_adapter.py` L426-428 (NoOpExtractor selected); `test_ephemeral_noop_for_non_claude_model` asserts all None fields and no stderr output |
| 10 | Live `--keep-failed` run on a real task with `--model claude-opus-4-8` produces `metrics.json` with non-null `input_tokens`/`output_tokens` and non-empty `documents_read_list` | ? UNCERTAIN | ROADMAP Exit Criteria item 4; Plan 06-03 Task 2 is a `checkpoint:human-verify` gate explicitly deferred to operator; not yet executed against live nanoclaw |

**Score:** 9/10 truths verified

---

### Deferred Items

No items deferred to later phases. The live verification is a Phase 6 exit criterion, not a later-phase item.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lab_harness_runner/metrics_extraction.py` | MetricsExtractor Protocol, AnthropicUsageExtractor, DocumentReadExtractor, AnthropicTranscriptExtractor, NoOpExtractor, is_claude_model | ✓ VERIFIED | 345 lines; all six exports present and importable; `@runtime_checkable` Protocol |
| `tests/test_metrics_extraction.py` | 16 tests covering all D-16 scenarios | ✓ VERIFIED | 551 lines; 16 tests, all pass; `_write_transcript` helper is local to the file |
| `lab_harness_runner/nanoclaw_adapter.py` | `_DeferredAnthropicExtractor`; `self._extractor` cached in `__init__`; `run()` invokes extractor + merges + breadcrumb | ✓ VERIFIED | Lines 344-564; all wiring present; 5 `self._extractor` references, 4 `_DeferredAnthropicExtractor` references, exact breadcrumb format |
| `tests/test_nanoclaw_adapter.py` | 3 new integration tests + 1 updated assertion | ✓ VERIFIED | `test_ephemeral_extracts_metrics_for_claude_model`, `test_ephemeral_noop_for_non_claude_model`, `test_ephemeral_logs_breadcrumb_on_missing_transcript` all present at confirmed line numbers |
| `tests/test_metrics.py` | 2 new D-17 metrics_provided end-to-end tests | ✓ VERIFIED | `test_metrics_provided_true_for_measured_run` (L359) and `test_metrics_provided_false_for_no_op_run` (L408) present |
| `tests/conftest.py` | `transcript_dir_with_claude_session` fixture | ✓ VERIFIED | Present at L94; builds `<tmp_path>/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` with two assistant messages (input=300, output=130) and one Read block |
| `docs/adapter-guide.md` | New `## Metrics Extraction` section with 3 paragraphs per D-20 | ✓ VERIFIED | Section at L44; contains all 11 required substrings: `## Metrics Extraction`, `MetricsExtractor`, `extract(messages_out: list[dict]) -> RunResult`, `is_claude_model`, `claude`, `NoOpExtractor`, `Ollama`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `Results are whole agent-system outcomes`, `"clean"` |
| `tests/test_docs.py` | `test_adapter_guide_documents_metrics_extraction_section` regression test | ✓ VERIFIED | Present at L106; asserts all 11 required substrings |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `nanoclaw_adapter.py::EphemeralNanoclawAdapter.__init__` | `metrics_extraction.py::is_claude_model` | `is_claude_model(self.model)` in `_select_extractor()` | ✓ WIRED | L426: `if is_claude_model(self.model):` |
| `nanoclaw_adapter.py::EphemeralNanoclawAdapter.run` | `metrics_extraction.py::MetricsExtractor.extract` | `self._extractor.extract(messages_out=[])` after poll loop | ✓ WIRED | L511: `extracted = self._extractor.extract(messages_out=[])` |
| `nanoclaw_adapter.py::NanoclawAdapter.run` | `shim_session_id` stash | `self.shim_session_id = str(shim_result["sessionId"])` after `_dispatch` | ✓ WIRED | L301: assignment present; `NanoclawAdapter.shim_session_id: str | None = None` initialised at L65 |
| `metrics_extraction.py::AnthropicUsageExtractor.extract` | `adapter.py::RunResult` | Returns `RunResult(...)` with token fields | ✓ WIRED | L174-180: `return RunResult(run_id="", end_state="clean", ...)` |
| `metrics_extraction.py::_TranscriptReader._resolve_transcript` | nanoclaw data dir layout | Globs `*.jsonl` in `transcript_dir`, matches `sessionId` field | ✓ WIRED | L96-102: `for candidate in self.transcript_dir.glob("*.jsonl")` |
| `tests/test_metrics.py::test_metrics_provided_true_for_measured_run` | `aggregation.py::build_summary` | `build_summary([row])` asserts `metrics_provided: True` | ✓ WIRED | L359 (confirmed in file); integration exercises the full write_metrics → build_summary round-trip |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `EphemeralNanoclawAdapter.run` | `extracted.input_tokens`, `extracted.documents_read_list` | `_DeferredAnthropicExtractor.extract()` → `AnthropicTranscriptExtractor` → jsonl on disk | Yes (reads real transcript or synthetic fixture) | ✓ FLOWING |
| `NoOpExtractor.extract` | all metric fields | None (returns None for everything) | By design — null metrics for non-Claude models | ✓ FLOWING (intentional None) |
| `AnthropicUsageExtractor.extract` | `input_tokens`, `output_tokens` | `_iter_jsonl` streaming `usage` blocks from transcript jsonl | Yes — sums real `usage` dict values | ✓ FLOWING |
| `DocumentReadExtractor.extract` | `documents_read_list` | `_iter_jsonl` streaming `content[]` blocks looking for `Read` tool_use | Yes — collects real `file_path` strings | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| D-16 anchor: 2587+9846=12433, 181+89688=89869 | `.venv/bin/python` probe against synthetic jsonl | `input_tokens=12433, output_tokens=89869` | ✓ PASS |
| D-07 dedup: two Read blocks for same path → list length 1 | `.venv/bin/python` probe | `documents_read_list=['/tmp/engagement.txt'], count=1` | ✓ PASS |
| `is_claude_model('claude-opus-4-8')` True; `is_claude_model(None)` False | Runtime import probe | Confirmed | ✓ PASS |
| Adapter routing: claude model → `_DeferredAnthropicExtractor`, non-claude → `NoOpExtractor` | Runtime construction probe | Confirmed for both model=None and model='deepseek-v4-flash:cloud' | ✓ PASS |
| Full test suite | `.venv/bin/python -m pytest -q` | 139 passed in 1.21s | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| EXT-01 | 06-01, 06-02, 06-03 | `MetricsExtractor` protocol with `extract(messages_out) -> RunResult` | ✓ SATISFIED | `@runtime_checkable class MetricsExtractor(Protocol)` in `metrics_extraction.py`; `isinstance` check works; `test_protocol_is_satisfied_by_extract_method` passes |
| EXT-02 | 06-01, 06-02 | `AnthropicUsageExtractor` reads `usage` from assistant messages, sums `input_tokens`/`output_tokens` | ✓ SATISFIED | Implementation in `metrics_extraction.py` L122-180; D-16 anchor values verified programmatically; cache fold at L162-166 |
| EXT-03 | 06-01, 06-02 | Document-read extractor enumerates `Read` tool_use blocks, collects into `documents_read_list` | ✓ SATISFIED | `DocumentReadExtractor` in `metrics_extraction.py` L183-252; dedup with `seen: set[str]`; verbatim paths |
| EXT-04 | 06-01, 06-02 | `NanoclawAdapter` (ephemeral) instantiates right extractor by model; Ollama path returns null without raising | ✓ SATISFIED | `_select_extractor()` in `nanoclaw_adapter.py` L417-428; `NoOpExtractor` never raises; `test_ephemeral_noop_for_non_claude_model` passes with zero stderr output |

**Note on REQUIREMENTS.md tracking:** The EXT-01..04 checkbox items in REQUIREMENTS.md still show `[ ]` (unchecked) and the traceability table still shows `pending` for all four. This is an administrative gap — the code fully satisfies all four requirements, but the tracking document was not updated after phase execution. This is a documentation-only gap; the implementation is complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none found) | — | — | — | — |

No `TBD`, `FIXME`, or `XXX` markers found in `lab_harness_runner/metrics_extraction.py` or `lab_harness_runner/nanoclaw_adapter.py`. No stub returns, placeholder components, or hollow wiring detected. All data-flow paths reach real jsonl parsing or intentional null returns.

---

### Human Verification Required

#### 1. Live schema discovery run (ROADMAP Exit Criterion 4)

**Test:** Execute the following command on a machine with nanoclaw-lq checked out and docker daemon running:

```bash
uv run python scripts/run_benchmark.py \
  --task corporate-ma/compare-matter-plan-against-engagement-letter \
  --adapter nanoclaw \
  --nanoclaw-dir ~/Projects/nanoclaw-lq \
  --model claude-opus-4-8 \
  --keep-failed \
  --output-dir ~/Projects/harvey-labs/results
```

Then inspect:
- `~/Projects/nanoclaw-lq/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` — confirm assistant messages carry `usage.input_tokens`, `usage.output_tokens`, `usage.cache_creation_input_tokens`, `usage.cache_read_input_tokens`, and `Read` tool_use blocks with `input.file_path`
- `~/Projects/harvey-labs/results/<run_id>/metrics.json` — confirm `input_tokens` and `output_tokens` are non-null integers, and `documents_read_list` is a non-empty list

**Expected:** `metrics.json` contains non-null `input_tokens` / `output_tokens` matching the transcript's summed usage blocks, and `documents_read_list` contains at least one entry. `end_state` is `"clean"`. The transcript path layout matches the resolver's assumption (sessionId on first line or findable by scan).

**Why human:** Requires docker daemon, nanoclaw-lq runtime, and a valid claude-opus-4-8 API credential. Cannot be automated in CI. This is ROADMAP Exit Criterion 4 and was explicitly scoped as a `checkpoint:human-verify` gate in Plan 06-03 Task 2. The unit tests verify extractor behavior against synthetic fixtures; this step confirms the real nanoclaw transcript matches that shape.

---

### Gaps Summary

No blocking gaps. The single human_needed item is the ROADMAP-required live schema discovery run. All code-level must-haves are verified — the `MetricsExtractor` protocol, all four extractor classes, the routing predicate, the adapter wiring (including the deferred extractor, the merge, and the stderr breadcrumb), the integration tests, and the docs addendum are all present, substantive, and wired.

**Administrative gap (non-blocking):** `REQUIREMENTS.md` checkbox items EXT-01..04 are still `[ ]` and the traceability table still says `pending`. These should be updated to `[x]` / `complete` to close out the traceability. This is a documentation-only gap that does not affect whether the goal is achieved.

---

_Verified: 2026-06-08_
_Verifier: Claude (gsd-verifier)_
