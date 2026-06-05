---
phase: 06
slug: metrics-extraction-and-model-routing
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-05
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Operator-supplied `nanoclaw_dir` / `group_id` → transcript resolver | `NanoclawAdapter.__init__` validates `group_id` via `_reject_unsafe_relative_path`; `nanoclaw_dir` is `.expanduser().resolve()`-d; the resolver globs `nanoclaw_dir / data / v2-sessions / <group_id> / .claude-shared / projects / -workspace-agent / *.jsonl` | Path strings; filesystem resolution |
| Transcript jsonl content (in-container) → extractor code | The Anthropic extractor reads each line via `json.loads`. Lines come from the agent's runtime, which is operator-controlled. The extractor only does structural reads; no `eval` or arbitrary execution | JSON-parsed dicts |
| `documents_read_list` → `metrics.json` on disk | The verbatim `file_path` strings collected from `Read` tool_use blocks are passed to `write_metrics` and serialised to `metrics.json`. They are container-internal paths, not user-controlled paths | Container-internal path strings |
| Operator-supplied `model` arg → `is_claude_model` predicate | The `--model` arg flows from `scripts/run_benchmark.py` to `EphemeralNanoclawAdapter(model=...)` to `is_claude_model(self.model)` to the routing decision (D-11) | Model name string |
| Inner `NanoclawAdapter._dispatch` shim stdout → `shim_session_id` | The shim stdout is JSON-parsed by `_dispatch`; the `sessionId` field is captured to `self.shim_session_id` (D-03) | Shim stdout JSON |
| Per-group transcript jsonl on disk → `AnthropicTranscriptExtractor` | The deferred extractor's `set_binding` is called with the per-group `transcript_dir` and the shim's `sessionId`; the resolver globs the jsonl and matches on `sessionId` (D-04) | Disk files |
| `extracted` RunResult → merged RunResult → outer `EphemeralNanoclawAdapter.run` return | The merge preserves the base `end_state` / `wall_clock_seconds` and replaces only the token / coverage fields (D-13) | RunResult fields |
| `docs/adapter-guide.md` → future adapter authors | The new `## Metrics Extraction` section is the human-readable contract; the regression test in `tests/test_docs.py` is the machine-readable guard | Doc text + regression assertions |
| Live run operator → nanoclaw transcript on disk | The operator inspects `data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` manually after `--keep-failed` retains the group | Operator-only access to retained group |
| `metrics.json` on disk → downstream consumer (LAB's `evaluation.compare`, future consumers) | The `input_tokens` / `output_tokens` / `documents_read_list` fields carry the measured run's evidence; the cache fold note in the doc tells the consumer what `input_tokens` means on a Claude run | Metric field values |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Path Traversal / Information Disclosure | Transcript resolver (globs `nanoclaw_dir/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/*.jsonl`; crafted `group_id` could read another group's transcript) | mitigate | `NanoclawAdapter.__init__` enforces `_reject_unsafe_relative_path(group_id, "group_id")` (nanoclaw_adapter.py:56) before any path is built; `self.nanoclaw_dir` is `.expanduser().resolve()`-d (nanoclaw_adapter.py:57); the resolver receives an already-validated `group_id` (T-03-05 mitigation) | closed |
| T-06-02 | Denial of Service (oversized jsonl) | `AnthropicUsageExtractor` / `DocumentReadExtractor` reading a long transcript | mitigate | Both extractors stream the jsonl line-by-line via `_iter_jsonl` (metrics_extraction.py:111-119) which yields `for line in handle:` inside `with path.open(...)`; no `path.read_text()` / `path.read_bytes()`; bounded by the resolved `nanoclaw_dir` | closed |
| T-06-03 | Tampering via malformed jsonl | `_iter_jsonl` | mitigate | `except (json.JSONDecodeError, OSError): continue` per line (metrics_extraction.py:116); regression test `test_malformed_lines_are_skipped` (tests/test_metrics_extraction.py:245-281) verifies a `not-json-at-all` line is skipped without raising | closed |
| T-06-04 | Information Disclosure via `documents_read_list` | `DocumentReadExtractor` → `write_metrics` → `metrics.json` | accept | Container-internal paths (e.g. `/tmp/engagement.txt`) leak the agent's working directory layout if `metrics.json` is exposed widely. This is the Phase 5/6 design contract "what the agent read" (D-08) — downstream consumer can apply `os.path.basename` if it wants basenames. D-08 anchored this; PROJECT.md does not restrict LAB result dir visibility | closed |
| T-06-05 | Tampering / Privilege Escalation | `EphemeralNanoclawAdapter(model=...)` | accept | `is_claude_model` is a prefix check only; it does not construct any path. The `transcript_dir` is built from `self.nanoclaw_dir` (already `.expanduser().resolve()`-d) + `group_id` (already validated by `_reject_unsafe_relative_path` in `NanoclawAdapter.__init__`). Operator who can set `model` already controls the run. Risk: low | closed |
| T-06-06 | Denial of Service (deferred extractor) | `_DeferredAnthropicExtractor.extract` (nanoclaw_adapter.py:361-370) | mitigate | Delegates to `AnthropicTranscriptExtractor(...).extract(messages_out)`, which uses the streaming `_iter_jsonl` iterator (T-06-02 evidence). Same line-by-line streaming applies | closed |
| T-06-07 | Information Disclosure (stderr breadcrumb leaks sessionId) | `EphemeralNanoclawAdapter.run` D-14 breadcrumb (nanoclaw_adapter.py:513-517) | accept | The sessionId is a nanoclaw-generated uuid4 (not a secret). The breadcrumb format matches the existing teardown-warning style (`[ephemeral] keeping failed group` / `[ephemeral] WARNING: failed to destroy group`) | closed |
| T-06-08 | Tampering via inner adapter mock | `test_ephemeral_extracts_metrics_for_claude_model` (tests/test_nanoclaw_adapter.py:471-530) | mitigate | Test asserts BOTH invariant preservation (`result.end_state == "clean"`, `result.wall_clock_seconds == 42.0`, `result.run_id == task_spec.run_id`) AND extractor-output replacement (`result.input_tokens == 300`, `result.output_tokens == 130`, `result.documents_read == 1`, `result.documents_read_list == ["/tmp/foo.txt"]`). The merge is field-by-field: end_state + wall_clock_seconds + run_id from inner; metric fields from extractor. The NoOp test (`test_ephemeral_noop_for_non_claude_model`) asserts the inverse (all fields None) | closed |
| T-06-09 | Information Disclosure (docs) | `docs/adapter-guide.md` ## Metrics Extraction | accept | The doc names `NoOpExtractor`, `is_claude_model`, and the cache fold. The doc is for adapter authors and operators; the names are intentional. The "runner stays thin" lock (PROJECT.md) does not restrict doc detail | closed |
| T-06-10 | Tampering via doc drift | `tests/test_docs.py::test_adapter_guide_documents_metrics_extraction_section` (L106-154) | mitigate | Regression test asserts all 11 required substrings including `cache_creation_input_tokens` and `cache_read_input_tokens` (L140-141). A future edit that drops the cache fold wording fails the test | closed |
| T-06-11 | Live-run schema deviation (D-19) | Resolver matching rule against `data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl` | mitigate | D-19 amendment is a small resolver change (e.g. glob for newest jsonl OR scan every line for `sessionId`), no Protocol surface change. Unit tests against synthetic fixtures (Plan 01) and integration tests against the conftest fixture (Plan 02) remain valid. Operator reports deviation in the resume signal | closed |
| T-06-12 | Live-run group retention | `--keep-failed` flag (operator's debug toggle) | accept | Per-run only; explicit operator action. Container-internal paths in `documents_read_list` are already accepted as the contract per D-08 ("what the agent read"). The retention is per-run, not per-sweep | closed |
| T-06-SC | Tampering (supply chain) | `pyproject.toml` dependencies + new module imports | mitigate | `pyproject.toml` `dependencies = []`; no `requirements.txt` / `requirements-*.txt` / `uv.lock` added. `metrics_extraction.py` imports only stdlib (`from __future__ import annotations`, `import json`, `from pathlib import Path`, `from typing import Protocol, runtime_checkable`) plus internal `from lab_harness_runner.adapter import RunResult`. No new packages installed | closed |

*Status: closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| T-06-04 | T-06-04 | Verbatim `file_path` strings (e.g. `/tmp/engagement.txt`) in `metrics.json` reveal the container-internal layout. The D-08 contract is "what the agent read", not "what is in `documents_dir`". Downstream consumers that want basenames can apply `os.path.basename`; the existing data is per-run, in the operator-controlled LAB result dir. PROJECT.md does not restrict LAB result dir visibility | PLAN (operator-equivalent trust level) | 2026-06-05 |
| T-06-05 | T-06-05 | `is_claude_model` is a prefix check; it does not construct paths. `transcript_dir` is built from `self.nanoclaw_dir` (resolved) + `group_id` (validated by `_reject_unsafe_relative_path`). The operator who can set `model` already controls the run. Risk: low | PLAN (operator-equivalent trust level) | 2026-06-05 |
| T-06-07 | T-06-07 | The D-14 stderr breadcrumb prints the shim's `sessionId`. The sessionId is a nanoclaw-generated uuid4 (not a secret). The breadcrumb matches the existing teardown-warning style (`[ephemeral] keeping failed group`, `[ephemeral] WARNING: failed to destroy group`) | PLAN (operator-equivalent trust level) | 2026-06-05 |
| T-06-09 | T-06-09 | The `## Metrics Extraction` section in `docs/adapter-guide.md` names `NoOpExtractor`, `is_claude_model`, and the cache fold. The doc is for adapter authors and operators; the names are intentional. The "runner stays thin" lock (PROJECT.md) does not restrict doc detail | PLAN (operator-equivalent trust level) | 2026-06-05 |
| T-06-12 | T-06-12 | `--keep-failed` retains the ephemeral group + transcript for debugging (per-run, not per-sweep). Container-internal paths in `documents_read_list` are already accepted as the D-08 contract. Operator-only access; explicit debug toggle | PLAN (operator-equivalent trust level) | 2026-06-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-05 | 13 (T-06-01..12 + T-06-SC) | 13 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-05
