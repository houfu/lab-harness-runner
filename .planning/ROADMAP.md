# Roadmap: lab-nanoclaw

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-06-02)
- 🚧 **v1.1 Post-v1.0 hardening & metrics fidelity** — Phases 5-7 (planning)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-06-02</summary>

- [x] Phase 1: Verify External Contracts And Scoring Pipeline (1/1 plans) — completed 2026-05-30
- [x] Phase 2: Build Harness-Neutral Package Core (5/5 plans) — completed 2026-05-30
- [x] Phase 3: Implement Nanoclaw-LQ Adapter (3/3 plans) — completed 2026-06-01
- [x] Phase 4: Completion, Metrics, Evaluation, And Scale-Out (4/4 plans) — completed 2026-06-01

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>🚧 v1.1 Post-v1.0 hardening & metrics fidelity (Phases 5-7) — PLANNING</summary>

- [ ] Phase 5: Honest Unmeasured Metrics Contract
- [ ] Phase 6: Metrics Extraction And Model Routing
- [ ] Phase 7: Sweep Driver Hardening And LAB Aggregation

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| ----- | --------- | -------------- | ------ | --------- |
| 1. Verify External Contracts And Scoring Pipeline | v1.0 | 1/1 | Complete | 2026-05-30 |
| 2. Build Harness-Neutral Package Core | v1.0 | 5/5 | Complete | 2026-05-30 |
| 3. Implement Nanoclaw-LQ Adapter | v1.0 | 3/3 | Complete | 2026-06-01 |
| 4. Completion, Metrics, Evaluation, And Scale-Out | v1.0 | 4/4 | Complete | 2026-06-01 |
| 5. Honest Unmeasured Metrics Contract | v1.1 | 2/3 | In Progress|  |
| 6. Metrics Extraction And Model Routing | v1.1 | 0/? | Planned | — |
| 7. Sweep Driver Hardening And LAB Aggregation | v1.1 | 0/? | Planned | — |

---

# v1.1 — Post-v1.0 hardening & metrics fidelity

## Milestone Goal

Make nanoclaw-backed metrics honest (measured vs. unmeasured) and harden the
post-v1.0 sweep driver, without changing the runner's role as a thin
orchestrator over Harvey LAB.

**Scope anchors (from v1.0):**

- The runner stays thin: no new aggregation tool in the runner; LAB is the
  source of truth for scoring and reporting.
- `RunResult` is adapter protocol evidence; `benchmark_status` is the
  deliverable-derived reporting state — these are two different signals and
  must stay distinguishable (per Phase 4 decisions).
- The post-v1.0 sweep driver (commits `3a1fd89`, `17d3eb7`, `3e0dd71`,
  `2884ae7`) already exists; Phase 7 hardens what is there, it does not
  rewrite it.
- Anthropic-token metrics live in nanoclaw's transcript jsonl
  (`data/v2-sessions/<group>/.claude-shared/.../<session>.jsonl`), not in
  `messages_out`. The extractor must read the transcript, not the outbound DB.
  (Verified: claude-opus-4-8 transcripts contain `message.usage.input_tokens`
  and `message.usage.output_tokens`; non-claude model transcripts under
  `messages_out` carry no `usage` block — they are routed to a no-raise null
  path.)
- Read-tool document identification is also a transcript-level signal: the
  assistant message `content[]` blocks contain `{"type": "tool_use", "name":
  "Read", "input": {"file_path": ...}}`. Same data source as the usage block.

**Existing data (anchors Phase 7's `TIMEOUT` rationale):**

- 174 task directories in `~/Projects/harvey-labs/results/` with `metrics.json`.
- `wall_clock_seconds` on clean runs (n=137, excluding timeout hits): p50
  325.7s, p75 390.8s, p90 456.0s, p95 521.0s, p99 586.2s, max 596.1s, mean
  325.3s. So 600s catches p99+ of clean runs while still bounding non-deliverable
  stalls.
- 34 timeout runs (~20% of total) — the poll's deliverable short-circuit
  means `TIMEOUT` only caps tasks that produce no deliverable; a 600s ceiling
  bounds worker stall without truncating the clean-run distribution.

**Verification posture for v1.1:**

- Phase 5 closes on unit tests against the contract change. No live nanoclaw
  run is required.
- Phase 6 closes on unit tests against the extractor with synthetic
  `messages_out`-shaped fixtures plus ONE live ephemeral-group run with
  `--keep-failed` for real schema discovery on a scoped task. The live run is
  verification, not a benchmark.
- Phase 7 closes on code review of the four post-v1.0 sweep.sh commits
  (`3a1fd89`, `17d3eb7`, `3e0dd71`, `2884ae7`) plus replay analysis against
  the existing `~/Projects/harvey-labs/results/` data, plus integration with
  LAB's existing `evaluation.compare` and `utils.sweep` — no new aggregator
  lives in the runner.

---

## Phase 5: Honest Unmeasured Metrics Contract

Status: planned

Goal: Make `RunResult` distinguish "adapter measured 0" from "adapter did not
measure", and have `write_metrics` and the aggregation layer propagate that
distinction honestly (null for unmeasured; skip nulls in mean / sum / variance;
annotate unmeasured rows in the batch summary).

Context:

- Today's `RunResult` (in `lab_harness_runner/adapter.py`) declares its token
  and coverage fields as `int | None`, but `write_metrics`
  (`lab_harness_runner/metrics.py`) silently coerces `None` to `0`, so an
  unmeasured field is indistinguishable from a measured zero. Every
  `results/.../metrics.json` written by the v1.0 sweep currently shows
  `input_tokens: 0, output_tokens: 0` for the same reason.
- `aggregation.py` already filters with `isinstance(value, int|float)` in
  `_numeric_values`, so a `null` would be skipped naturally — but the
  null-vs-zero distinction has to be preserved in the `metrics.json` payload
  on disk for downstream readers (LAB's `evaluation.compare`, future
  consumers) to honor it.
- `end_state` is the one field that must remain mandatory and non-null — it
  is the raw protocol signal that `derive_benchmark_status` consumes.

Deliverables:

- `RunResult` semantics: the existing `int | None` typing stays, but
  `write_metrics` writes the underlying value unchanged when it is
  `None`/`int`/`list` rather than coercing `None` to `0`/`[]`. `end_state`
  is the only required field; everything else may be `None` (= unmeasured).
- `write_metrics` writes `null` (JSON `null`) for unmeasured fields, never `0`
  or `[]`. The previous "no null values in JSON" guarantee
  (`test_write_metrics_no_null_values`) is replaced by an explicit "unmeasured
  fields are written as `null`" guarantee, except for `end_state` and any
  caller-supplied diagnostic field.
- `build_summary` and `summarize_variance` skip `null` entries in
  mean / min / max / sum / stdev computations. The variance payload records
  the actual count of measured rows, not the row count, for each field.
- `write_batch_summary` adds a visible "unmeasured" annotation per row
  (e.g. a `metrics_provided` boolean or a per-field "unmeasured" flag) and a
  per-field count of unmeasured rows in the summary, so a downstream reader
  can tell which entries were measured vs. unmeasured.
- Updated unit tests covering: explicit zero is still 0; `None` becomes
  `null`; aggregation skips `null`; unmeasured rows are visibly annotated
  in `summary.json`.
- One-line update to `docs/adapter-guide.md` noting that token / coverage
  fields are now nullable in `metrics.json` and that a `null` means
  "not measured", not "zero".

Exit Criteria:

- A `RunResult` constructed without token / coverage fields writes
  `metrics.json` with `null` for those fields (not `0`).
- A `RunResult` constructed with explicit `0` for a token field still writes
  `0` (zero is preserved).
- A batch summary over mixed measured + unmeasured rows reports per-field
  variance counts that exclude the unmeasured rows, and lists the unmeasured
  rows visibly in the per-row payload.
- The existing "Results are whole agent-system outcomes" semantics in
  `docs/adapter-guide.md` are unchanged — the contract change is additive,
  not a rewrite of `end_state` semantics.

Plans: 3 plans

- [x] 05-01-PLAN.md — RunResult field defaults + write_metrics coercion removal (D-01, D-02, D-03, D-07, D-08) + test_metrics.py updates (D-17)
- [x] 05-02-PLAN.md — aggregation.py annotation + write_batch_summary row normalization (D-04, D-05, D-06, D-09, D-10, D-11, D-12) + _batch_row pass-through (D-14)
- [ ] 05-03-PLAN.md — test_aggregation.py mixed/unmeasured coverage (D-18) + docs/adapter-guide.md addendum (D-15, D-16) + doc test

**Requirements satisfied:** CON-01, CON-02, CON-03

---

## Phase 6: Metrics Extraction And Model Routing

Status: planned

Goal: Wire a `MetricsExtractor` protocol into the nanoclaw adapter so a run's
`messages_out` is parsed for token usage and document-read identifiers, with
the right extractor selected by the configured model and the Ollama path
returning null metrics without raising.

Context:

- `NanoclawAdapter` currently returns `RunResult(..., end_state, wall_clock_seconds)`
  with all token / coverage fields unset (the `metrics.json` files in
  `~/Projects/harvey-labs/results/` show this). Anthropic tokens live in the
  nanoclaw transcript jsonl, not in `messages_out`, and need a new read path.
- Verified data sources from inspection of
  `~/Projects/nanoclaw-lq/data/v2-sessions/...`:
  - Token usage: claude-opus-4-8 transcripts carry
    `{"type":"assistant","message":{...,"usage":{"input_tokens":...,"output_tokens":..., "cache_*":...}}}`
    on every assistant message. `cache_creation_input_tokens` and
    `cache_read_input_tokens` exist alongside raw `input_tokens` /
    `output_tokens`; CON-02 only forces honest null-vs-zero — the extractor
    may choose to fold cache reads into `input_tokens` and report the
    breakdown alongside, or stay with the raw `input_tokens` /
    `output_tokens` only. Whichever is chosen must be documented in
    `docs/adapter-guide.md`.
  - Document reads: `{"type":"tool_use","name":"Read","input":{"file_path":...}}`
    blocks in assistant message `content[]`. The `file_path` is the
    container-internal path (e.g. `/tmp/engagement.txt`), so the document-read
    list is a set of container-path strings — not LAB documents-dir
    filenames. This is acceptable: the contract is "what the agent read",
    not "what is in `documents_dir`".
  - Non-claude models (e.g. `deepseek-v4-flash`) carry no `usage` block in
    the transcript and no `Read` `tool_use` blocks in the inspected sample.
    The Ollama path returns null metrics without raising.
- `EphemeralNanoclawAdapter` already takes a `model` arg. Phase 6 routes that
  arg to the right extractor and falls back to a no-op extractor for
  unknown / Ollama-routed models.
- The `messages_out` table is the wrong source for both signals on
  Anthropic runs — the transcript is. The phase MUST read the transcript
  jsonl path. (This is the schema-discovery insight the live run with
  `--keep-failed` will confirm.)
- The "live run is verification, not a benchmark" constraint: pick one
  scoped real task (suggest `corporate-ma/compare-matter-plan-against-engagement-letter`,
  the v1.0 proof run), use `--keep-failed` so the ephemeral group and its
  transcript survive for inspection, and verify the extractor reads the
  same `usage` and `Read` blocks already confirmed to exist in
  `data/v2-sessions/820628bb-c260-4bb4-bd60-b5a3b9ce4f58/`.

Deliverables:

- New module `lab_harness_runner/metrics_extraction.py` (or similar) with:
  - `MetricsExtractor` Protocol — one method, e.g.
    `extract(messages_out: list[dict]) -> RunResult` or
    `extract(messages_out: list[dict]) -> dict` (filled back into `RunResult`).
    Final signature to be decided in CONTEXT, but the contract is "take the
    raw messages from the agent's outbound stream, return the metric fields".
  - `AnthropicUsageExtractor` — reads `usage` from assistant message blocks
    in the transcript jsonl and sums `input_tokens` / `output_tokens` across
    the run. (A `cache_read_input_tokens` / `cache_creation_input_tokens`
    breakdown is optional and may be surfaced as a sidecar field.)
  - `DocumentReadExtractor` — enumerates `tool_use` blocks with
    `name == "Read"` in assistant messages and collects `input.file_path`
    into `documents_read_list` (deduplicated, order preserved).
  - A combined Anthropic path that runs both extractors against the same
    transcript. Both are wired for any `claude-*` model name.
  - A no-op extractor (returns all token / coverage fields as `None`) for
    non-claude models and the explicit `Ollama` path. It MUST NOT raise.
- `NanoclawAdapter` (or `EphemeralNanoclawAdapter`, depending on where the
  model is known) instantiates the right extractor based on the configured
  `model` and applies it before constructing `RunResult`. The Ollama path
  returns null metrics without raising.
- A transcript-path resolver: given a `group_id` and the nanoclaw data
  directory, locate the most recent session jsonl for that group. The live
  run with `--keep-failed` confirms the layout matches
  `data/v2-sessions/<groupId>/.claude-shared/projects/-workspace-agent/<sessionId>.jsonl`.
- Unit tests against a synthetic `messages_out` / transcript fixture
  covering: usage sum across multiple assistant messages; document dedup;
  empty transcript → null metrics; non-claude model → null metrics
  (no raise); transcript missing → null metrics (no raise).
- One live ephemeral-group run with `--keep-failed` on a scoped real task
  for real schema discovery. The run is verification, not a benchmark —
  the goal is to confirm the extractor reads the same `usage` and `Read`
  blocks already verified by hand.
- A short addendum to `docs/adapter-guide.md` describing the
  `MetricsExtractor` extension point and the Anthropic vs Ollama routing.

Exit Criteria:

- A synthetic transcript with two assistant messages (one with
  `input_tokens: 2587, output_tokens: 181`, one with
  `input_tokens: 9846, output_tokens: 89688`) yields
  `input_tokens: 12433, output_tokens: 89869` from `AnthropicUsageExtractor`.
- A synthetic transcript with two `Read` `tool_use` blocks for the same
  `file_path` yields a `documents_read_list` containing that path exactly
  once.
- A non-claude `model` value (e.g. `deepseek-v4-flash:cloud`) routes to
  the no-op extractor; the resulting `RunResult` has token / coverage
  fields all `None`; nothing is raised.
- The live `--keep-failed` run on a scoped task produces
  `metrics.json` with non-null `input_tokens` and `output_tokens` matching
  the transcript's summed `usage` blocks, and a non-empty
  `documents_read_list` reflecting the agent's `Read` tool calls.

Plans: TBD (split per file boundary: protocol + AnthropicUsageExtractor /
 DocumentReadExtractor / model routing + integration /
 live verification run)

**Requirements satisfied:** EXT-01, EXT-02, EXT-03, EXT-04

---

## Phase 7: Sweep Driver Hardening And LAB Aggregation

Status: planned

Goal: Harden the post-v1.0 `sweep.sh` driver and wire it into LAB's existing
aggregation / comparison tools, without introducing a new aggregator in the
runner.

Context:

- The four post-v1.0 sweep.sh commits (`3a1fd89`, `17d3eb7`, `3e0dd71`,
  `2884ae7`) already provide: deterministic per-task run-ids, skip-on-clean
  resumption, `xargs -P` parallelism, venv-direct `python` invocation
  (avoiding uv-cache FD exhaustion that crashed a prior sweep at ~193
  tasks), `TIMEOUT` env var, and stderr surfacing of destroy-shim errors
  in the ephemeral teardown warning. These are the substrate this phase
  hardens.
- Three operator-visible gaps remain in `sweep.sh`:
  - `TIMEOUT`'s 600s default has no documented rationale grounded in
    observed wall-clock data. (Anchored above: 600s is above p99 of clean
    runs at 586.2s and bounds non-deliverable stalls; the rationale is
    a one-paragraph comment update.)
  - `inventory` is human-only (a per-task `FAILED/MISSING` line plus an
    `incomplete: N` count); CI cannot consume it via `xargs` because the
    lines carry a `FAILED/MISSING:` prefix.
  - There is no post-run summary line of `clean` / `agent_error` /
    `timeout` / `missing-deliverable` counts derived from the
    `metrics.json` files the sweep just wrote. A CI consumer has to
    re-scan the results tree to know the pass rate.
  - On sweep failure, `run_one` always returns 0 (per the 17d3eb7 fix to
    prevent xargs abort), so the script's own exit code is uninformative.
    A CI consumer needs a non-zero exit on sweep failure with the
    per-run error log path printed to stderr.
- LAB already ships `evaluation.compare` and `utils.sweep` (visible at
  `~/Projects/harvey-labs/evaluation/compare.py` and
  `~/Projects/harvey-labs/utils/sweep.py`). The runner is NOT a place
  to add a new aggregator; the sweep driver should be able to invoke
  LAB's `evaluation.compare` as a final, opt-in step (LAB-02) and
  produce results compatible with what `evaluation.compare` already
  consumes (LAB-01).
- The replay analysis target is the existing
  `~/Projects/harvey-labs/results/` data: 174 task directories with
  `metrics.json`, 140 benchmark-clean, 34 timeout. That data already
  exercises every code path in `sweep.sh`'s `is_clean` / `inventory` /
  skip-on-clean logic, so no new live sweep is required if the existing
  data is sufficient (per the Quality section of REQUIREMENTS.md).

Deliverables:

- `sweep.sh` documentation update: a header comment in the script
  recording the `TIMEOUT` 600s default rationale (p99 of clean
  wall-clock = 586.2s; bounds non-deliverable stalls) plus a one-line
  summary of how to override it.
- `sweep.sh inventory` becomes dual-output: machine-readable (one path
  per line, suitable for `xargs` consumption — no `FAILED/MISSING:`
  prefix on the path lines) plus a small human-readable header /
  per-task status counts block. The CI consumer reads the path lines;
  the human consumer reads the counts.
- `sweep.sh` post-run summary: a final line of the form
  `summary: clean=N agent_error=M timeout=K missing_deliverable=L`
  derived from the `metrics.json` files the sweep just wrote.
- `sweep.sh` exit-code hardening: track per-run failure count in a
  per-sweep temp file; if any run failed, print each failed run's
  log path to stderr and exit non-zero. A CI consumer can act on the
  exit code alone; the per-run stderr lets an operator jump straight
  to the failing logs without re-scanning the results tree.
- `sweep.sh` integration with LAB's existing
  `evaluation.compare`: an opt-in flag (e.g. `LAB_COMPARE=task|area|all`
  env var, mirroring `run_benchmark.py --compare`) that invokes LAB's
  `evaluation.compare` as the final step of a sweep, reusing the
  results the sweep just produced. The runner does NOT reimplement the
  comparator — it shells out to LAB's tool.
- Code review document (in `.planning/milestones/v1.1-phases/.../REVIEW.md`
  or similar) of the four post-v1.0 sweep.sh commits (`3a1fd89`,
  `17d3eb7`, `3e0dd71`, `2884ae7`), capturing what each commit
  contributed and what v1.1 builds on top of each.
- Replay analysis: a one-off replay of `sweep.sh inventory` against
  the existing `~/Projects/harvey-labs/results/` data confirming the
  inventory output matches the metrics on disk (140 clean + 34 timeout
  = 174 total; 34 incomplete). No new live sweep is run.

Exit Criteria:

- `scripts/sweep.sh` documents the `TIMEOUT` 600s default with a
  one-paragraph rationale grounded in observed `results/` wall-clock
  data (the 174-run sample above), and `inventory` produces one path per
  line on stdout (no `FAILED/MISSING:` prefix) plus a header with task
  counts — that path output is consumable by
  `xargs inventory_output | xargs -I{} ...` in a CI job.
- `scripts/sweep.sh` prints a final
  `summary: clean=N agent_error=M timeout=K missing_deliverable=L`
  line derived from the `metrics.json` files it wrote.
- A sweep with at least one failed run exits non-zero, and the
  per-run error log path for each failed run is on stderr — a CI
  consumer can act on the exit code alone.
- `LAB_COMPARE=task|area|all scripts/sweep.sh` (or equivalent
  opt-in) invokes LAB's `evaluation.compare` as the final step
  against the results the sweep just produced. The runner's source
  contains no new aggregation code (LAB-01 holds: output is
  compatible with LAB's existing batch-summary tool; LAB-02 holds:
  the sweep can opt into LAB's comparison as a final step).
- The replay analysis confirms the inventory of the existing
  `~/Projects/harvey-labs/results/` data matches the on-disk
  metrics: 140 clean, 34 timeout, 34 incomplete.

Plans: TBD (split per change boundary: TIMEOUT doc + inventory shape /
 post-run summary + exit code / LAB compare opt-in /
 review document + replay analysis)

**Requirements satisfied:** SWP-01, SWP-02, SWP-03, SWP-04, LAB-01, LAB-02
