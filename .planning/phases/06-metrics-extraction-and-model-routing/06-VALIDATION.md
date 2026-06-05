---
phase: 6
slug: metrics-extraction-and-model-routing
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-05
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (dev dependency: `pytest>=9.0.3`); `tests/conftest.py` for shared fixtures |
| **Quick run command** | `uv run --quiet python -m pytest tests/test_metrics_extraction.py -q` |
| **Full suite command** | `uv run --quiet python -m pytest -q` |
| **Estimated runtime** | ~1.2 seconds for full suite (137 tests) |

## Sampling Rate

- **After every task commit:** Run `uv run --quiet python -m pytest tests/test_metrics_extraction.py -q` (Plan 01 surface) or the relevant plan's test file
- **After every plan wave:** Run `uv run --quiet python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~1.2 seconds (full suite)

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | EXT-01 | T-06-03 | No eval of transcript content; structural reads only | unit | `uv run --quiet python -c "from lab_harness_runner.metrics_extraction import MetricsExtractor, NoOpExtractor, is_claude_model; ..."` | ✅ | ✅ green |
| 06-01-02 | 01 | 1 | EXT-01, EXT-02, EXT-03, EXT-04 | T-06-02, T-06-03 | Streamed jsonl iteration; malformed lines skipped | unit | `uv run --quiet python -m pytest tests/test_metrics_extraction.py -q` | ✅ | ✅ green |
| 06-02-01 | 02 | 2 | EXT-01, EXT-04 | T-06-05, T-06-06, T-06-07 | Routing at `__init__`; `is_claude_model` is prefix-only; stderr breadcrumb exposes only nanoclaw uuid | unit | `uv run --quiet python -c "from pathlib import Path; from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter; ..."` | ✅ | ✅ green |
| 06-02-02 | 02 | 2 | EXT-01, EXT-02, EXT-03, EXT-04 | T-06-08 | Inner adapter mocked; merge preserves invariants; no-op path emits no breadcrumb | integration | `uv run --quiet python -m pytest tests/test_nanoclaw_adapter.py -q` | ✅ | ✅ green |
| 06-03-01a | 03 | 3 | EXT-01, EXT-04 | — | Doc substring regression | unit | `uv run --quiet python -m pytest tests/test_docs.py -q` | ✅ | ✅ green |
| 06-03-02 | 03 | 3 | EXT-02, EXT-03 | — | Live schema discovery | manual | operator-executed `scripts/run_benchmark.py --keep-failed` per D-18 | ⬜ deferred | ⬜ pending (operator-deferred) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [x] `tests/test_metrics_extraction.py` — 16 tests covering D-16 scenarios (Plan 01)
- [x] `tests/test_nanoclaw_adapter.py` — 3 new integration tests (Plan 02)
- [x] `tests/test_metrics.py` — 2 new metrics_provided end-to-end tests (Plan 02)
- [x] `tests/test_docs.py` — 1 new D-20 regression test (Plan 03)
- [x] `tests/conftest.py` — `transcript_dir_with_claude_session` fixture (Plan 02)
- [x] pytest framework already installed (dev dep in `pyproject.toml`)

*Existing infrastructure covers all phase requirements.*

## Per-Requirement Coverage Detail

### EXT-01 — `MetricsExtractor` protocol with `extract(messages_out) -> RunResult`

| Test | File | Line | Verifies |
|------|------|------|----------|
| `test_protocol_is_satisfied_by_extract_method` | `tests/test_metrics_extraction.py` | L149 | Protocol is `@runtime_checkable`; structural `isinstance` check passes |
| `test_noop_extractor_returns_none_metrics` | `tests/test_metrics_extraction.py` | L119 | NoOpExtractor conforms to protocol; ignores `messages_out`; all fields None |
| `test_noop_extractor_does_not_raise_on_non_dict_messages` | `tests/test_metrics_extraction.py` | L136 | D-10 never-raise contract |

### EXT-02 — `AnthropicUsageExtractor` reads `usage` from assistant messages

| Test | File | Line | Verifies |
|------|------|------|----------|
| `test_anthropic_usage_sums_two_assistant_messages` | `tests/test_metrics_extraction.py` | L166 | D-16 anchor: 2587+9846=12433 / 181+89688=89869 |
| `test_anthropic_usage_folds_cache_fields` | `tests/test_metrics_extraction.py` | L196 | D-05 cache fold: 100+50+200=350 |
| `test_empty_transcript_returns_none` | `tests/test_metrics_extraction.py` | L224 | D-04 / D-06: empty jsonl → all None |
| `test_malformed_lines_are_skipped` | `tests/test_metrics_extraction.py` | L245 | T-06-03: malformed lines do not raise |
| `test_transcript_missing_returns_none` | `tests/test_metrics_extraction.py` | L284 | D-04 missing-transcript path returns all None |
| `test_anthropic_usage_ignores_non_assistant_lines_with_usage_block` | `tests/test_metrics_extraction.py` | L304 | Only `type=="assistant"` lines contribute |
| `test_ephemeral_extracts_metrics_for_claude_model` | `tests/test_nanoclaw_adapter.py` | L471 | D-13 integration: end-to-end run with fixture jsonl |
| `test_metrics_provided_true_for_measured_run` | `tests/test_metrics.py` | L359 | D-17: measured path round-trip |

### EXT-03 — Document-read extractor enumerates `Read` `tool_use` blocks

| Test | File | Line | Verifies |
|------|------|------|----------|
| `test_document_read_dedup` | `tests/test_metrics_extraction.py` | L341 | D-07 dedup, first-wins, order preserved |
| `test_document_read_skips_non_read_tool_use` | `tests/test_metrics_extraction.py` | L382 | D-07 / D-08: Bash/Glob/etc. contribute nothing; paths verbatim |
| `test_documents_skipped_fields_remain_none` | `tests/test_metrics_extraction.py` | L421 | D-07 anchor: no skip signal in transcript |
| `test_document_read_preserves_order_with_duplicates_across_messages` | `tests/test_metrics_extraction.py` | L452 | D-07 dedup with three messages |
| `test_combined_anthropic_path_populates_both_fields` | `tests/test_metrics_extraction.py` | L514 | D-09: AnthropicTranscriptExtractor merges usage + docs |

### EXT-04 — Routing by model; Ollama / unknown returns null metrics without raising

| Test | File | Line | Verifies |
|------|------|------|----------|
| `test_is_claude_model_routes_correctly` | `tests/test_metrics_extraction.py` | L77 | D-10: prefix check, case-sensitive, boundary `claude` is True |
| `test_routing_predicate_direct` | `tests/test_metrics_extraction.py` | L98 | Regression guard on routing predicate |
| `test_ephemeral_noop_for_non_claude_model` | `tests/test_nanoclaw_adapter.py` | L533 | D-10 / EXT-04: `model="ollama"` → NoOpExtractor; no stderr breadcrumb |
| `test_ephemeral_logs_breadcrumb_on_missing_transcript` | `tests/test_nanoclaw_adapter.py` | L587 | D-14: stderr breadcrumb; base result preserved |
| `test_metrics_provided_false_for_no_op_run` | `tests/test_metrics.py` | L408 | D-17: unmeasured path round-trip; `metrics_provided: False` |
| `test_adapter_guide_documents_metrics_extraction_section` | `tests/test_docs.py` | L106 | D-20 regression: 11 required substrings present |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| D-18 Live schema discovery: real nanoclaw transcript shape matches synthetic fixture | EXT-02, EXT-03 | Requires docker daemon + nanoclaw runtime + operator-issued CLI; out of scope for autonomous unit tests | Run `uv run python scripts/run_benchmark.py --task corporate-ma/compare-matter-plan-against-engagement-letter --adapter nanoclaw --nanoclaw-dir ~/Projects/nanoclaw-lq --model claude-opus-4-8 --keep-failed --output-dir ~/Projects/harvey-labs/results`; inspect `~/Projects/nanoclaw-lq/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` and the per-run `metrics.json` |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (Plan 06-03 Task 2 is the only manual-only item — operator-deferred per plan)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags
- [x] Feedback latency < 2s (full suite runs in ~1.2s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-05 — all EXT-01..04 requirements have automated verification. 137/137 tests pass; 55 Phase 6-specific tests pass. D-20 doc regression test guards the adapter-guide wording. The only remaining manual item is the operator-executed D-18 live schema-discovery run on `corporate-ma/compare-matter-plan-against-engagement-letter`, which is deferred per the plan's `checkpoint:human-verify` gate and is a `06-03 Task 2` artifact rather than a Nyquist gap.
