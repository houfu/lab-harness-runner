# Phase 6: Metrics Extraction And Model Routing - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

## Phase Boundary

Wire a `MetricsExtractor` protocol into the nanoclaw adapter so a run's
transcript jsonl is parsed for token usage and document-read identifiers, with
the right extractor selected by the configured model and the Ollama / unknown
model path returning null metrics without raising. The contract is "take the
raw messages from the agent's outbound stream, return a full `RunResult`" — the
adapter's existing poll loop and end-state semantics are unchanged.

## Implementation Decisions

### Extractor surface (EXT-01)

- **D-01:** `MetricsExtractor` is a `Protocol` with one method
  `extract(messages_out: list[dict]) -> RunResult`. The returned `RunResult`
  carries `end_state="clean"` (the extractor sees only a successful
  transcript — adapter-level error mapping is the adapter's job, not the
  extractor's). The adapter builds a base `RunResult` from its poll loop,
  then replaces it with the extractor's output via a single
  `base_run = extractor.extract(messages)`. Token / coverage fields the
  extractor does not populate remain `None`.
- **D-02:** Module location: `lab_harness_runner/metrics_extraction.py`
  (per ROADMAP suggestion). One module per extractor class, each with
  a `__init__` that takes whatever the extractor needs (the
  `AnthropicUsageExtractor` takes the path to the transcript jsonl;
  the `DocumentReadExtractor` takes the same).

### AnthropicUsageExtractor (EXT-02)

- **D-03:** `AnthropicUsageExtractor.extract()` reads
  `data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl`
  where `<group_id>` and `<session_id>` come from the
  `NanoclawAdapter._dispatch` result (the shim already returns
  `sessionId` and `outboundDbPath` in its JSON line; the same
  shim can be extended to also surface the transcript path, or
  the adapter can derive it from
  `nanoclaw_dir / "data" / "v2-sessions" / group_id / ".claude-shared" / "projects" / "-workspace-agent"`).
  Session jsonl is the **single source of truth** — `messages_out`
  is the wrong source (the v1.1 anchor is explicit on this).
- **D-04:** Transcript resolution: locate the jsonl whose
  `sessionId` (top-level field) matches the shim's
  `sessionId`. If multiple jsonls exist for a group (defensive),
  the matching one wins. If none match (or the file does not
  exist), return a `RunResult` with all token / coverage fields
  as `None` — **never raise**. The same one-shot scan happens
  after the poll loop completes; no retry / no deadline
  extension. The rationale: the shim returns the session id at
  dispatch time, and the poll loop already runs for up to
  `timeout_seconds` after that, so the jsonl must exist by
  the time we scan.
- **D-05:** Usage arithmetic: for every line in the jsonl whose
  top-level `type` is `"assistant"` and whose `message.usage`
  is a dict, sum `input_tokens`, `cache_creation_input_tokens`,
  and `cache_read_input_tokens` into a single `input_tokens`
  total; sum `output_tokens` into a single `output_tokens`
  total. **Both** cache fields are folded (per "Fold both
  cache_creation and cache_read" decision). This matches the
  user-facing Anthropic bill; the cache breakdown is **not**
  preserved as a sidecar field — RunResult's surface stays
  unchanged. A one-line note in
  `docs/adapter-guide.md` will record that
  `input_tokens` on a Claude run is "raw + cache_creation +
  cache_read", so a downstream consumer is not surprised.
- **D-06:** Lines with no `message.usage` block (e.g.
  `type: "user"`, `type: "queue-operation"`, `type: "system"`,
  tool-result messages) are skipped. A line whose
  `message.usage` exists but is missing `input_tokens` /
  `output_tokens` is treated as if it had `0` for the missing
  key (the rest still contributes). Lines with malformed
  JSON are skipped, not raised.

### DocumentReadExtractor (EXT-03)

- **D-07:** `DocumentReadExtractor.extract()` reads the same
  transcript jsonl (the one resolved in D-04) and enumerates
  `tool_use` blocks in assistant messages' `content[]`. For
  every block with `"name": "Read"`, the value of
  `input.file_path` is collected into `documents_read_list`,
  **deduplicated with order preserved** (the first occurrence
  wins on ties). Non-Read `tool_use` blocks (e.g. `Bash`,
  `Write`, `Edit`, `Glob`, `Grep`) are skipped. The
  `documents_read_list` length is also written to
  `documents_read` (per the v1.0 contract — count + list both
  populated). `documents_skipped` and `documents_skipped_list`
  remain `None` (no skip signal in the transcript).
- **D-08:** File paths are kept **verbatim as the agent saw
  them** — e.g. `/tmp/engagement.txt`, not basename. No
  remapping against `lab-documents` mount. The contract is
  "what the agent read", not "what is in `documents_dir`".
  A downstream consumer that wants the basename can apply
  `os.path.basename`; the runner does not pre-normalize.
- **D-09:** `AnthropicUsageExtractor` and
  `DocumentReadExtractor` share the same transcript jsonl.
  The combined Anthropic path runs **both** extractors and
  merges the two `RunResult`s field-by-field (each fills
  different fields — tokens from usage, document list from
  tool_use). The merged result is returned as a single
  `RunResult` from a thin combined-class
  (`AnthropicTranscriptExtractor`) that owns both.

### Model routing (EXT-04)

- **D-10:** Routing predicate: a function
  `is_claude_model(model: str | None) -> bool` returning
  `True` if `model` is a non-empty string and starts with the
  case-sensitive prefix `"claude"`. Anything else — `None`,
  `""`, `"ollama"`, `"deepseek-v4-flash:cloud"`, `"qwen2.5"`
  — routes to the **no-op extractor**. The no-op returns a
  `RunResult` with `end_state="clean"`, `wall_clock_seconds`
  from the adapter's clock, and **all** token / coverage
  fields as `None`. It MUST NOT raise. The Ollama path is
  covered by the no-op (it is just a non-claude model).
- **D-11:** The model string the routing function sees is
  `EphemeralNanoclawAdapter.model` — the same value the
  create shim already forwards. Routing is decided **at
  `EphemeralNanoclawAdapter` construction time** and the
  resulting extractor is stored on the instance as
  `self._extractor`. `EphemeralNanoclawAdapter.run()` runs
  the extractor after the poll loop completes. (Per "Inside
  EphemeralNanoclawAdapter, selected by self.model"
  decision — the routing surface is the ephemeral adapter,
  not the base `NanoclawAdapter`.)
- **D-12:** `NanoclawAdapter` (the fixed-group adapter) does
  **not** gain a model arg. It is the per-group, model-neutral
  surface used by tests and the legacy CLI; metrics
  extraction for it is out of scope for Phase 6 — the
  "model known" assumption only holds for the ephemeral
  adapter path. Tests covering the fixed adapter continue
  to assert `None` token / coverage fields.

### Wiring and integration (EXT-04)

- **D-13:** `EphemeralNanoclawAdapter.run()` ordering:
  1. Existing poll loop produces a base `RunResult` with
     `end_state` and `wall_clock_seconds` only.
  2. **After** the poll loop, the adapter instantiates the
     selected extractor (cached on `self._extractor` per D-11)
     with the resolved transcript path + session id, calls
     `extract(messages_out)`, and replaces the base result.
  3. `metrics_provided` is then correctly `True` for the
     measured Anthropic run and `False` for the no-op
     non-claude run (per CON-03 from Phase 5).
- **D-14:** Missing-transcript semantics: if the
  AnthropicTranscriptExtractor cannot find the jsonl, the
  adapter logs a one-line warning to stderr
  (`[ephemeral] metrics: transcript not found for session <id>; skipping extraction`)
  and **keeps the base `RunResult`** (i.e. all token /
  coverage fields stay `None`). This is the same null path
  as the no-op extractor — the metrics surface is identical,
  the operator gets a stderr breadcrumb. The base
  `end_state` and `wall_clock_seconds` are preserved.
- **D-15:** The shim's `send-lab-message.ts` is **not**
  modified to surface the transcript path. The adapter
  derives the jsonl path from
  `nanoclaw_dir + group_id + session_id` per D-04. If
  D-04's resolution proves fragile in the live run, a
  follow-up shim change is a Phase 7+ concern (or a
  small amendment to this phase's plan if the
  verification run finds a different path layout).

### Tests (EXT-01..04)

- **D-16:** `tests/test_metrics_extraction.py` (new) covers:
  - **Usage sum across multiple assistant messages** —
    synthetic transcript with two assistant lines
    (input=2587, output=181 and input=9846, output=89688)
    → `AnthropicUsageExtractor` returns
    `input_tokens=12433, output_tokens=89869` (no cache in
    the synthetic fixture; that case is in a separate test).
  - **Cache fold** — synthetic transcript with one
    assistant line
    (input_tokens=100, cache_creation=50, cache_read=200,
    output_tokens=30) → `input_tokens=350,
    output_tokens=30`. Documents the fold behavior.
  - **Document dedup** — synthetic transcript with two
    `Read` blocks for the same `file_path` →
    `documents_read_list` contains that path once
    (order preserved).
  - **Document with non-Read tool_use** — mixed
    `Read` + `Bash` blocks → only `Read` blocks contribute.
  - **Empty transcript** — jsonl with no assistant
    messages → token / coverage fields all `None`.
  - **Malformed lines** — jsonl with one bad line
    interleaved with valid lines → valid lines still
    contribute; no exception.
  - **Transcript missing** — extractor pointed at a
    nonexistent path → no exception; all fields `None`.
  - **Routing** — `is_claude_model("claude-opus-4-8")`
    is `True`; `is_claude_model(None)`,
    `is_claude_model("")`,
    `is_claude_model("deepseek-v4-flash:cloud")`,
    `is_claude_model("Ollama")` are all `False`. The
    `NoOpExtractor` is tested with a representative
    `messages_out` and asserts all token / coverage
    fields are `None` and no exception is raised.
  - **Combined Anthropic path** — a synthetic transcript
    that exercises both usage and `Read` blocks →
    `AnthropicTranscriptExtractor` returns a `RunResult`
    with both `input_tokens` and `documents_read_list`
    populated.
- **D-17:** The `metrics_provided` boolean (Phase 5
  CON-03) is exercised end-to-end in a test that runs
  `write_metrics` on the extractor's output and asserts
  `metrics_provided: true` for a measured Anthropic run
  and `metrics_provided: false` for the no-op path. This
  is a new assertion; the Phase 5 metric tests continue
  to cover the contract.

### Live run with `--keep-failed`

- **D-18:** The live verification run is on
  `corporate-ma/compare-matter-plan-against-engagement-letter`,
  with `--keep-failed` and `--model claude-opus-4-8`.
  The goal is **schema discovery**, not a benchmark:
  the operator runs the command, inspects
  `data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl`
  manually, and confirms the unit tests' synthetic
  fixture shape matches reality. After confirmation, the
  resulting `metrics.json` is checked for non-null
  `input_tokens` / `output_tokens` and a non-empty
  `documents_read_list`.
- **D-19:** If the live run reveals a transcript path
  shape that differs from D-04's expected layout, the
  plan is amended to add a fallback resolution method
  (e.g. glob for the newest jsonl) — this is a small
  code change and does not change the extractor surface.
  The "schema discovery" framing is explicit so the
  plan can absorb this without re-discussion.

### Docs

- **D-20:** `docs/adapter-guide.md` gets a new section
  "Metrics Extraction" with three paragraphs:
  (a) the `MetricsExtractor` extension point and the
  one-method contract;
  (b) the Anthropic vs no-op routing rule (the
  `is_claude_model` predicate with the `claude` prefix
  rule);
  (c) a note that
  `input_tokens` on a Claude run includes both
  `cache_creation_input_tokens` and
  `cache_read_input_tokens` (per D-05), so a downstream
  consumer of `metrics.json` is not surprised.
  The "Results are whole agent-system outcomes" line
  is unchanged (additive only).

### Claude's Discretion

- The exact module name
  (`metrics_extraction.py` is the suggestion but the
  planner may pick `extraction.py` or split into
  `metrics_extractors.py` based on file-boundary
  aesthetics).
- The synthetic fixture format in
  `tests/test_metrics_extraction.py` — the planner may
  use a single helper that returns a list of dicts, or
  per-test inline jsonl strings.
- Whether `AnthropicTranscriptExtractor` is its own
  class or a thin function
  `combine(usage_result, doc_result) -> RunResult` —
  either is fine; the protocol contract is the same.
- The exact wording of the D-20 docs addendum.
- The implementation of `is_claude_model` — a one-liner
  `model.startswith("claude") if model else False` is
  the suggested default; the planner may factor it
  out as a helper if there are multiple call sites.

## Canonical References

Downstream agents MUST read these before planning or implementing.

### Project-level
- `.planning/PROJECT.md` — the "runner stays thin" lock
  (no new aggregator in the runner; the
  `MetricsExtractor` is a thin read-side helper, not
  an aggregator) and the "no fork LAB" lock (the
  extractor does not change LAB's evaluator).
- `.planning/REQUIREMENTS.md` v1.1 — EXT-01, EXT-02,
  EXT-03, EXT-04 are the binding requirements for
  this phase. The EXT-04 "Ollama path returns null
  metrics without raising" clause is what D-10 and
  D-14 satisfy.
- `.planning/ROADMAP.md` v1.1 — Phase 6 Goal /
  Context / Deliverables / Exit Criteria. The
  verification posture ("Phase 6 closes on unit
  tests against the extractor with synthetic
  `messages_out`-shaped fixtures plus ONE live
  ephemeral-group run with `--keep-failed` for real
  schema discovery on a scoped task. The live run
  is verification, not a benchmark.") sets the
  test/live-run mix.
- `.planning/phases/05-honest-unmeasured-metrics-contract/05-CONTEXT.md`
  — the prior phase's decisions on null vs zero
  (CON-01), `metrics_provided` boolean (CON-03),
  and `documents_read_list` nullability (D-07 in
  Phase 5) all flow into Phase 6: the extractor's
  "no schema found" path returns a `RunResult`
  with `None` fields and the resulting
  `metrics.json` will have `metrics_provided: false`.

### Source code (the wiring surface)
- `lab_harness_runner/adapter.py` —
  `RunResult` dataclass with its `None`-defaulted
  token / coverage / list fields. The extractor
  builds a `RunResult` (D-01), so it must respect
  the same `None` semantics; the Phase 5 changes
  to `documents_read_list` (now `None`-defaulted
  per Phase 5 D-07) apply here.
- `lab_harness_runner/nanoclaw_adapter.py` —
  `NanoclawAdapter._dispatch()` already returns
  a dict with `sessionId` and `outboundDbPath`
  (D-03 needs `sessionId`); the
  `EphemeralNanoclawAdapter.run()` is the routing
  surface (D-11, D-13). The `_FOOTER_TEMPLATE`
  and `_CENTRAL_DB_NAME` constants are the
  nanoclaw-side anchors.
- `scripts/run_benchmark.py` — the `--model` arg
  is wired to `EphemeralNanoclawAdapter(model=...)`
  in `_adapter_from_args`; no change needed
  beyond what the adapter's `__init__` now does
  with the model string. The `--keep-failed` flag
  is wired to `EphemeralNanoclawAdapter(keep_failed=...)`
  and is the live-run toggle (D-18).

### Tests (the test surface to add)
- `tests/test_nanoclaw_adapter.py` — existing
  tests cover the base `NanoclawAdapter` with
  synthetic `messages_out`; they continue to
  apply because `NanoclawAdapter` does not gain
  a model arg (D-12). One new test
  (`test_ephemeral_extracts_metrics_for_claude_model`)
  covers the `EphemeralNanoclawAdapter` +
  `AnthropicTranscriptExtractor` integration
  end-to-end with a mocked shim that returns
  a known `sessionId` and a fixture jsonl on
  disk.
- `tests/test_metrics.py` — Phase 5 contract
  tests continue to apply (D-17 adds the
  metrics_provided assertion as a new test).
- `tests/conftest.py` — a fixture providing
  a synthetic transcript jsonl path (a
  `tmp_path`-rooted file with two assistant
  messages, one `Read` block, and one
  non-Read `tool_use` block) is the base
  for the new test file.

### Docs
- `docs/adapter-guide.md` — the "Metrics
  Extraction" section (D-20) goes after the
  existing "RunResult" field list. The
  "Results are whole agent-system outcomes"
  invariant at the bottom of the file is
  preserved (additive only).

### Existing data (schema anchors)
- `~/Projects/nanoclaw-lq/data/v2-sessions/820628bb-c260-4bb4-bd60-b5a3b9ce4f58/.claude-shared/projects/-workspace-agent/36229df1-67a2-4bd6-87e6-fb669185f4fc.jsonl`
  — the v1.0 proof transcript, confirmed by
  hand to carry `usage.input_tokens`,
  `usage.output_tokens`,
  `usage.cache_creation_input_tokens`,
  `usage.cache_read_input_tokens` on every
  assistant message, and `Read` `tool_use`
  blocks with `input.file_path`. The Phase 6
  synthetic fixtures mirror this layout.
  This file is **not** committed to the
  repo — it is the live-run inspection
  target (D-18).

## Existing Code Insights

### Reusable Assets
- `NanoclawAdapter._dispatch` returns a dict
  with `sessionId` and `outboundDbPath`; the
  same dict is the seed for D-03 / D-04's
  transcript resolution. No shim change needed
  (D-15).
- `EphemeralNanoclawAdapter._create_group` and
  the `model` field on its instance are
  already wired through `scripts/run_benchmark.py`
  → `--model` arg. Phase 6 reads from this
  field, no new plumbing.
- `metrics_provided` (Phase 5 CON-03) and the
  null-vs-zero contract (Phase 5 CON-01) mean
  the extractor's "no schema" / "no Ollama"
  paths naturally produce a `metrics.json` that
  signals its unmeasured-ness to the downstream
  consumer — no separate "extractor succeeded"
  flag needed.

### Established Patterns
- "Add, don't rewrite" — Phase 5's contract
  change is the model here: the new module is
  additive to the existing adapter; the base
  `NanoclawAdapter` and its tests are unchanged.
- "Two-tier state" — `RunResult.end_state` is
  the raw protocol signal (set by the poll
  loop); the extractor's job is to **enrich**
  the token / coverage fields without touching
  `end_state`. The merged `RunResult` keeps
  the adapter's `end_state` (D-13 step 2's
  "replace" applies only to the token /
  coverage fields, not `end_state`).
- "Verification, not benchmark" — the live
  run is for schema discovery (D-18, D-19).
  The 1251-task sweep is Phase 7's concern;
  Phase 6 stays at one scoped task.

### Integration Points
- `EphemeralNanoclawAdapter.run()` is the
  single integration point: the extractor
  selection happens in `__init__`, the
  extraction happens after the poll loop in
  `run()`. The `RunResult` returned to
  `scripts/run_benchmark.py` is the
  extractor's output for measured fields
  and the adapter's base result for the
  rest.
- `lab_harness_runner/metrics.write_metrics`
  is the next sink: it consumes the
  `RunResult` and writes `metrics.json`
  with the Phase 5 null-vs-zero semantics.
  No change to `write_metrics` is needed;
  the extractor's `None` fields flow through
  unchanged.
- `nanoclaw_dir / data / v2-sessions /
  <group_id> / .claude-shared / projects /
  -workspace-agent / <session_id>.jsonl` is
  the file the extractor reads. The
  `nanoclaw_dir` is the
  `EphemeralNanoclawAdapter` instance field
  already resolved at construction time
  (D-11).

## Specific Ideas

- The "cache fold" decision (D-05) is a
  conscious trade-off: the user-facing
  Anthropic bill is the primary unit, so
  `input_tokens` on a Claude run is the
  cached bill, not the raw input. The
  one-line docs addendum (D-20) is the
  single place a downstream consumer
  needs to look to understand the value.
- The "container paths as-is" decision
  (D-08) keeps the contract identical
  to what the agent saw; any basename /
  documents-dir mapping is a consumer
  concern. This also means the extractor
  does not need access to
  `task_spec.documents_dir` — it is
  self-contained.
- The "transcript path resolved from
  sessionId" decision (D-04) is more
  precise than "newest jsonl in the
  group" because the group may have
  older sessions from prior runs (the
  v1.1 anchor mentions one group
  already exists from the v1.0 proof
  run). The sessionId match avoids
  reading the wrong transcript.
- The "no raise" rule for missing
  transcripts (D-14) is the same shape
  as the no-op extractor (D-10): a
  failed extraction is indistinguishable
  from an unmeasured run, with a
  stderr breadcrumb for the operator.
  `end_state` is preserved either way.

## Deferred Ideas

None — discussion stayed within phase scope.
A few items surfaced that **belong elsewhere**:

- **Per-task token / duration histogram in
  the sweep driver** (already in
  `REQUIREMENTS.md` "Deferred (carried from
  v1.0)") — not part of Phase 6; this
  phase produces the token / duration data
  the histogram would plot, but the
  histogram itself is Phase 7+ material.
- **Read-tool path normalization against
  `lab-documents` mount** — could be a
  follow-up if a downstream consumer
  needs basename-only paths, but it is not
  required for Phase 6 and is a consumer
  concern, not an extractor concern.

---

*Phase: 6-Metrics Extraction And Model Routing*
*Context gathered: 2026-06-05*
