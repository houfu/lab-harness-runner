# Phase 6: Metrics Extraction And Model Routing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 6-Metrics Extraction And Model Routing
**Areas discussed:** Extractor surface shape, Cache token handling, Model routing predicate, Document path normalization, Transcript path resolution, Missing-transcript semantics, Live run policy, Extractor wiring location, Cache fold arithmetic

---

## Extractor surface (EXT-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Returns metric dict only | `extract(messages) -> dict`; adapter builds a base RunResult then `.update()`s | |
| Returns full RunResult | `extract(messages) -> RunResult` with `end_state="clean"`; adapter replaces its base result | ✓ |
| Returns typed dataclass | `extract(messages) -> ExtractedMetrics`; adapter copies fields | |

**User's choice:** Returns full RunResult
**Notes:** User picked the strongest-typing option. Adapter does a single replacement
after the poll loop. The "no-op" extractor returns a RunResult with all token /
coverage fields None, mirroring the Ollama / unknown-model path. The end_state
on the extractor's return is "clean" by definition — the extractor only sees a
successful transcript; adapter-level error mapping stays in the adapter.

---

## Cache token handling (EXT-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Fold cache into input_tokens | input_tokens = raw + cache_creation + cache_read (matches bill) | ✓ |
| Report raw only, cache as diagnostics | Add cache_read_tokens / cache_creation_tokens sidecar fields | |
| Raw only, no cache | Drop the cache info | |

**User's choice:** Fold cache into input_tokens
**Notes:** The follow-up question on fold arithmetic confirmed both
`cache_creation_input_tokens` AND `cache_read_input_tokens` are folded. The
RunResult surface stays unchanged (no new fields). The cache fold will be
documented in the docs addendum so a downstream consumer of `metrics.json`
understands `input_tokens` on a Claude run is the cached bill, not the raw
input.

---

## Model routing predicate (EXT-04)

| Option | Description | Selected |
|--------|-------------|----------|
| String prefix match 'claude' | `model.startswith("claude")` | ✓ |
| Explicit allowlist of model names | Known list of Claude models | |
| Negative match — non-Ollama is Anthropic | Anything non-Ollama is Anthropic | |
| Function-based predicate | `is_claude_model(model)` function | |

**User's choice:** String prefix match 'claude'
**Notes:** A `is_claude_model(model)` helper wraps the one-line check so the
test surface has a clean assertion. The "Ollama path returns null metrics
without raising" EXT-04 clause is satisfied by the no-op extractor
(everything not starting with `claude` routes to no-op, including Ollama).

---

## Document path normalization (EXT-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep container paths as-is | e.g. `/tmp/engagement.txt` verbatim | ✓ |
| Map via lab-documents mount prefix | Strip `/workspace/extra/lab-documents/` to basename | |
| Keep both: container path AND basename | Two fields | |

**User's choice:** Keep container paths as-is
**Notes:** The contract is "what the agent read", not "what is in
documents_dir". A downstream consumer that wants basenames can apply
`os.path.basename`; the runner does not pre-normalize. Document dedup with
order preserved (first occurrence wins) is the standard list-dedup pattern.

---

## Transcript path resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Walk group_id/.claude-shared/projects/-workspace-agent/, newest jsonl | Newest by mtime | |
| Resolve by sessionId from shim_result | Match jsonl whose sessionId == shim's sessionId | ✓ |
| Use nanoclaw_dir/data/.tmp/ | Wrong layout | |

**User's choice:** Resolve by sessionId from shim_result
**Notes:** The shim's `send-lab-message.ts` already returns `sessionId` in
its JSON result (the existing dispatch contract). The adapter scans the
candidate jsonls and matches on top-level `sessionId` field. Defensive
against the case where the group has older sessions from prior runs (the
v1.0 proof group `820628bb-...` exists already, and any future
`EphemeralNanoclawAdapter` run targeting that group would see it).

---

## Missing-transcript semantics

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot scan after poll, log + skip if absent | Scan once; if missing, keep base RunResult, log to stderr | ✓ |
| Retry with short timeout | Up to 5s wait for the jsonl to appear | |
| Log a warning, never raise | Stderr breadcrumb | |

**User's choice:** One-shot scan after poll, log + skip if absent
**Notes:** The poll loop already runs for up to `timeout_seconds` after
dispatch, so the jsonl must exist by the time we scan. No retry / no
deadline extension. The adapter logs a one-line stderr breadcrumb and keeps
the base `RunResult` (all token / coverage fields stay `None`). The
"never raise" rule applies regardless.

---

## Live run with --keep-failed

| Option | Description | Selected |
|--------|-------------|----------|
| Use scoped task per ROADMAP, --keep-failed, manual jsonl inspection | corporate-ma/compare-matter-plan-against-engagement-letter, --keep-failed | ✓ |
| Use scoped task, normal teardown, trust metrics.json | No --keep-failed | |
| Both: --keep-failed + metrics.json check | Belt-and-suspenders | |

**User's choice:** Use scoped task per ROADMAP, --keep-failed, manual jsonl
inspection
**Notes:** The live run is for **schema discovery** (D-18 in CONTEXT), not a
benchmark. The goal is to confirm the synthetic fixture shape (used in unit
tests) matches reality. After the run, the operator inspects
`data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl`
manually. If the path layout differs, the plan is amended to add a
fallback resolution method (small change, no surface change).

---

## Extractor wiring location

| Option | Description | Selected |
|--------|-------------|----------|
| Inside EphemeralNanoclawAdapter, selected by self.model | `self._extractor` cached in `__init__` | ✓ |
| Inside NanoclawAdapter, add model arg | Per-group, model known | |
| Free function select_extractor(model) | Stateless | |

**User's choice:** Inside EphemeralNanoclawAdapter, selected by self.model
**Notes:** `EphemeralNanoclawAdapter` is the only place the model is known
(the base `NanoclawAdapter` is model-neutral, used for tests and the
legacy CLI). The routing surface is `EphemeralNanoclawAdapter.__init__`;
the extraction happens in `EphemeralNanoclawAdapter.run()` after the
poll loop completes. `NanoclawAdapter` does **not** gain a model arg —
out of scope for Phase 6.

---

## Claude's Discretion

- Module name: `metrics_extraction.py` is the suggested default; planner
  may pick `extraction.py` or split based on file boundaries.
- Synthetic fixture format in `tests/test_metrics_extraction.py`.
- Whether the combined Anthropic path is a class
  (`AnthropicTranscriptExtractor`) or a thin combine function — both
  satisfy the protocol.
- Exact wording of the docs addendum (D-20).
- Implementation shape of `is_claude_model` (one-liner vs helper).

## Deferred Ideas

- **Per-task token / duration histogram in the sweep driver** — already
  on the deferred list from v1.0. Phase 6 produces the data; the
  histogram is Phase 7+ material.
- **Read-tool path normalization against `lab-documents` mount** —
  consumer concern, not an extractor concern. If a downstream consumer
  needs basename-only paths, that is a follow-up.
