---
status: complete
phase: 06-metrics-extraction-and-model-routing
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md
started: 2026-06-05T10:55:00Z
updated: 2026-06-05T11:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Routing predicate is_claude_model
expected: is_claude_model("claude-opus-4-8") is True; is_claude_model(None), is_claude_model(""), is_claude_model("Ollama"), is_claude_model("deepseek-v4-flash:cloud") are False; is_claude_model("Claude-opus-4-8") is False (case-sensitive).
result: pass

### 2. MetricsExtractor Protocol structural satisfaction
expected: A class defining only `extract(self, messages_out: list[dict]) -> RunResult` passes `isinstance(x, MetricsExtractor)` (the Protocol is @runtime_checkable).
result: pass

### 3. AnthropicUsageExtractor — D-05 cache fold
expected: Given a synthetic transcript with assistant usage blocks, input_tokens sums raw + cache_creation_input_tokens + cache_read_input_tokens, and output_tokens sums output_tokens across assistant messages.
result: pass

### 4. DocumentReadExtractor — D-07 dedup, D-08 verbatim paths
expected: Two Read tool_use blocks for the same file_path yield a single entry (dedup, first-wins); non-Read tool_use blocks (Bash, etc.) contribute nothing; paths are kept verbatim (no basename, no remapping).
result: pass

### 5. NoOpExtractor — D-10 never-raises
expected: extract([]) returns a RunResult with all token / coverage fields as None and end_state="clean"; never raises for any input shape.
result: pass

### 6. AnthropicTranscriptExtractor — D-09 composed output
expected: Calling extract on a transcript that has BOTH assistant usage and Read tool_use returns a RunResult with BOTH input_tokens/output_tokens AND documents_read/documents_read_list populated.
result: pass

### 7. EphemeralNanoclawAdapter wiring — D-11 routing at construction
expected: Constructing the adapter with model=None or model="Ollama" selects the NoOpExtractor; constructing with model="claude-opus-4-8" selects the deferred Anthropic extractor.
result: pass

### 8. EphemeralNanoclawAdapter end-to-end Claude path — D-13 merge
expected: A successful run with a Claude-prefixed model on a tmp_path transcript fixture returns a RunResult with input_tokens, output_tokens, documents_read, and documents_read_list all populated from the fixture; end_state and wall_clock_seconds are preserved from the inner adapter.
result: pass

### 9. EphemeralNanoclawAdapter end-to-end no-op path — D-10
expected: A successful run with a non-Claude model returns a RunResult with all metric fields None; no breadcrumb is logged to stderr.
result: pass

### 10. EphemeralNanoclawAdapter missing-transcript breadcrumb — D-14
expected: A Claude run whose sessionId does not match any jsonl in the group dir logs exactly `[ephemeral] metrics: transcript not found for session <id>; skipping extraction` to stderr and preserves the inner adapter's end_state.
result: pass

### 11. metrics_provided end-to-end — D-17 measured vs unmeasured
expected: A measured RunResult (all token / coverage fields populated) round-trips through write_metrics + build_summary with metrics_provided=True; a no-op RunResult (all metric fields None) round-trips with metrics_provided=False.
result: pass

### 12. D-20 docs addendum locked by regression test
expected: docs/adapter-guide.md contains a `## Metrics Extraction` section between `## Contract` and `## Implementing run()` with the protocol signature, is_claude_model routing rule, NoOpExtractor reference, and cache fold note; tests/test_docs.py::test_adapter_guide_documents_metrics_extraction_section passes and locks the wording.
result: pass

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
