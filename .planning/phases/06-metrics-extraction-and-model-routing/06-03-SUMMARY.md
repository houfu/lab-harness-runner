---
phase: 06-metrics-extraction-and-model-routing
plan: 03
subsystem: docs-and-verification
tags: [docs, adapter-guide, regression-test, d-20, live-verification-deferred]

# Dependency graph
requires:
  - phase: 06-metrics-extraction-and-model-routing
    plan: 01
    provides: "MetricsExtractor Protocol, is_claude_model predicate, NoOpExtractor, AnthropicTranscriptExtractor, is_claude_model"
  - phase: 06-metrics-extraction-and-model-routing
    plan: 02
    provides: "EphemeralNanoclawAdapter wiring + integration tests + D-17 metrics_provided tests; conftest fixture for synthetic transcript jsonl"
  - phase: 05-honest-unmeasured-metrics-contract
    plan: any
    provides: "RunResult with nullable token / coverage / list fields; null-vs-zero contract on disk"
provides:
  - "D-20 docs addendum: new '## Metrics Extraction' section in docs/adapter-guide.md with three paragraphs (extension point, routing rule, cache fold note)"
  - "Regression test test_adapter_guide_documents_metrics_extraction_section asserting all 11 required substrings (D-20 wording is locked)"
  - "Live verification run instructions for the operator (D-18) — Task 2 deferred to operator"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern: doc addendum + regression doc test is the same shape as Phase 5 D-15 / D-16 (test_adapter_guide_documents_null_vs_zero_distinction) — D-20 follows the same convention so a future edit that drops the wording fails the test"

key-files:
  modified:
    - docs/adapter-guide.md
    - tests/test_docs.py

key-decisions:
  - "Placed the protocol signature 'extract(messages_out: list[dict]) -> RunResult' on its own line (kept line short) so the regression test's substring check matches verbatim against the on-disk text — the line-wrap from the suggested paragraph text would have broken the substring match"
  - "Kept the 'Results are whole agent-system outcomes' invariant at L165 (now L196) unchanged — D-20 explicit anchor; the new section is additive only"

patterns-established:
  - "Pattern: regression doc tests for adapter-guide contract wording are added alongside their doc addenda, with one substring per topic the plan promises to document. Each missing substring produces a per-term error message that quotes the lost term"

requirements-completed: [EXT-01, EXT-02, EXT-03, EXT-04]

# Metrics
duration: 4min
completed: 2026-06-05
---

# Phase 6 Plan 3: D-20 Docs Addendum + Live Verification Run Outline

**D-20 docs addendum (MetricsExtractor extension point, Anthropic vs no-op routing rule, cache fold note) added to `docs/adapter-guide.md` and regression-locked by a new doc test. The D-18 / D-19 live verification run on `corporate-ma/compare-matter-plan-against-engagement-letter` is deferred to the operator — Task 2 of this plan is `checkpoint:human-verify` (operator-executed) and is OUT OF SCOPE for autonomous execution.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-05T10:22:45Z
- **Completed:** 2026-06-05T10:26:30Z (Task 1 only; Task 2 deferred to operator)
- **Tasks:** 1 of 2 executed autonomously (Task 2 = `checkpoint:human-verify`, deferred to operator per plan)
- **Files modified:** 2 (1 doc, 1 test)

## Accomplishments

- `docs/adapter-guide.md` now has a new `## Metrics Extraction` section (L44) between `## Contract` and `## Implementing run()` per D-20. The section is exactly three paragraphs:
  1. **Extension point + protocol contract + end_state semantics**: `MetricsExtractor` Protocol from `lab_harness_runner.metrics_extraction` with the one-method contract `extract(messages_out: list[dict]) -> RunResult`. The adapter base class builds its own `RunResult` from the poll loop and replaces the token / coverage fields with the extractor's output. The extractor's return `end_state` is `"clean"` by definition.
  2. **Routing rule**: `is_claude_model(model)` predicate at `EphemeralNanoclawAdapter` construction time — non-empty string starting with case-sensitive `claude` selects `AnthropicTranscriptExtractor`; anything else (`None`, `""`, `ollama`, `deepseek-v4-flash:cloud`, `qwen2.5`) selects the no-op `NoOpExtractor` that returns every token / coverage field as `None` and never raises. The Ollama / unknown-model path is covered by the no-op (EXT-04).
  3. **Cache fold note**: `input_tokens` on a Claude run is the **sum of the raw `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens` fields** on each line — both cache fields are folded, matching the user-facing Anthropic bill. No sidecar cache breakdown is preserved.
- The `## Metrics Extraction` heading is at L44, between `## Contract` (L8) and `## Implementing run()` (L76) — the new section sits AFTER the RunResult field list and BEFORE the run() implementation guidance, as the plan specified.
- The existing `Results are whole agent-system outcomes` invariant at L196 is preserved unchanged (D-20 explicit anchor; additive only). `grep -c` returns exactly 1 match.
- `tests/test_docs.py` has a new `test_adapter_guide_documents_metrics_extraction_section` test that asserts all 11 required substrings from the D-20 docs addendum. The test runs a per-substring loop with a per-term error message that quotes the lost substring, so a future edit that drops any of the 11 terms points at the exact wording that was removed.
- Full test suite is green: **137 passed in 1.28s** (was 136 from Plan 02 + 1 new doc test).

## Task Commits

Each autonomous task was committed atomically:

1. **Task 1a: Add `## Metrics Extraction` section to `docs/adapter-guide.md`** - `5aa66e4` (docs)
2. **Task 1b: Add `test_adapter_guide_documents_metrics_extraction_section` regression test** - `169aee4` (test)
3. **Task 2: Operator-executed live verification run with `--keep-failed` (D-18, D-19)** - **DEFERRED TO OPERATOR** (`checkpoint:human-verify`)

## Files Created/Modified

- `docs/adapter-guide.md` - new `## Metrics Extraction` section inserted between the existing `## Contract` block (L42) and the `## Implementing run()` heading. The new section is exactly three paragraphs separated by blank lines. The protocol signature is on a single line so the regression test's substring check matches verbatim.
- `tests/test_docs.py` - new `test_adapter_guide_documents_metrics_extraction_section` test added after `test_adapter_guide_documents_null_vs_zero_distinction`. Asserts 11 required substrings: the section heading, the protocol name, the exact protocol signature, the routing predicate, the prefix, the no-op class, the Ollama example, both cache field names, the existing invariant sentence, and the end_state semantics.
- No other files modified. `lab_harness_runner/`, `tests/conftest.py`, `tests/test_metrics.py`, `tests/test_nanoclaw_adapter.py`, and `scripts/` are all untouched per the plan's "Do NOT modify" list.

## Decisions Made

- **Protocol signature on a single line.** The plan's suggested paragraph text wraps the signature `extract(messages_out: list[dict]) -> RunResult` across two lines (the `MetricsExtractor` reference is at the end of one line, the protocol name is on the next). A naive `assert substring in text` check on that wrapping would fail because Python's `in` operator does not match across newlines. Restructured the paragraph to keep the signature on one line (kept the line under ~90 chars). This is a phrasing choice, not a content change — the paragraph still names `MetricsExtractor`, the full module path `lab_harness_runner.metrics_extraction`, and the exact signature.
- **Section position.** The plan said to insert the new section "BETWEEN L42 and L44, after the 'core package treats `RunResult.end_state` as adapter/protocol evidence' paragraph and before '## Implementing run()'". The actual insertion is at L44 (the section heading), with the section's first paragraph at L46, well after the anchor paragraph (L41-42) and well before the next heading (L76). The `grep -n "^## "` output shows the order: `## Contract` (L8) → `## Metrics Extraction` (L44) → `## Implementing run()` (L76).
- **Regression test error messages.** Each missing substring produces a per-term error message that quotes the lost term — a future maintainer who drops one of the 11 terms sees the exact wording that was removed, not a generic "test failed" message. This is consistent with the Phase 5 doc test's style.

## Deviations from Plan

### Auto-fixed Issues

None.

### Plan Adjustments (non-Rule)

**1. Signature line reflowed to a single line.**
- **Found during:** Task 1a (after the first edit). The plan's suggested paragraph wraps the protocol signature across two lines, but the regression test (Task 1b) asserts `"extract(messages_out: list[dict]) -> RunResult"` as a substring — a cross-line substring match is not possible with `assert substring in text` because newlines break the match.
- **Issue:** A naive `in` check would have failed the test even though the signature text was present (just line-wrapped). The plan's verification step (`uv run --quiet python -m pytest tests/test_docs.py -v`) would have failed.
- **Fix:** Reflowed the first paragraph to keep the signature on a single line. The signature is now at L48 as `\`extract(messages_out: list[dict]) -> RunResult\`,` — a single line. The protocol name, module path, and all other content from the suggested text is preserved verbatim.
- **Files modified:** `docs/adapter-guide.md`
- **Verification:** `test_adapter_guide_documents_metrics_extraction_section` now passes (`'extract(messages_out: list[dict]) -> RunResult' in text` is `True`).
- **Committed in:** `5aa66e4` (Task 1a commit; reflow was part of the same edit).

---

**Total deviations:** 1 plan adjustment (signature line reflow), 0 auto-fixes
**Impact on plan:** The signature is unchanged in content — the only change is line-wrapping. All 11 required substrings match verbatim; the regression test passes.

## Issues Encountered

- The protocol signature line-wrap was caught during Task 1b (writing the test). A naive `assert substring in text` check on the suggested two-line wrap would have failed the test. Reflowed the first paragraph to keep the signature on a single line before running the test.

## Verification

- `uv run --quiet python -m pytest tests/test_docs.py -q` → **6 passed** (5 existing + 1 new).
- `uv run --quiet python -m pytest -q` (full suite) → **137 passed in 1.28s** (136 from Plan 02 + 1 new doc test).
- `grep -n "^## " docs/adapter-guide.md` shows the heading order: `## Contract` (L8) → `## Metrics Extraction` (L44) → `## Implementing run()` (L76) → ... — the new section sits between the RunResult field list (inside `## Contract`) and the run() implementation guidance, as the plan specified.
- `grep -c "## Metrics Extraction" docs/adapter-guide.md` → 1 (one section heading).
- `grep -c "MetricsExtractor" docs/adapter-guide.md` → 2 (section heading + paragraph body).
- `grep -c "is_claude_model" docs/adapter-guide.md` → 1.
- `grep -c "NoOpExtractor" docs/adapter-guide.md` → 1.
- `grep -c "cache_creation_input_tokens" docs/adapter-guide.md` → 1.
- `grep -c "cache_read_input_tokens" docs/adapter-guide.md` → 1.
- `grep -c "Results are whole agent-system outcomes" docs/adapter-guide.md` → 1 (D-20 anchor; invariant preserved).
- `grep -c "test_adapter_guide_documents_metrics_extraction_section" tests/test_docs.py` → 1 (regression test present).
- All 11 required substrings from the plan's action block are present in the doc (verified by the regression test's loop). The 11 substrings: `## Metrics Extraction`, `MetricsExtractor`, `extract(messages_out: list[dict]) -> RunResult`, `is_claude_model`, `claude`, `NoOpExtractor`, `Ollama`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `Results are whole agent-system outcomes`, `"clean"`.

## Task 2: Live Verification Run — DEFERRED TO OPERATOR

Task 2 of this plan is `checkpoint:human-verify` (operator-executed). It is OUT OF SCOPE for autonomous execution per the plan's explicit scope boundary ("the executor does NOT run the live command in this plan"). The full instructions for the operator are reproduced below so the orchestrator can present them to the user.

### What was built (the autonomous portion of this plan)

The MetricsExtractor module (Plan 01), the EphemeralNanoclawAdapter wiring + integration tests (Plan 02), and the D-20 docs addendum + regression doc test (Plan 03 Task 1) are all in place. The unit tests prove the extractor works against synthetic fixtures. Task 2 is the D-18 / D-19 schema-discovery verification: one live ephemeral-group run on the v1.0 proof task with `--keep-failed`, followed by manual inspection of the resulting nanoclaw transcript jsonl and the per-run `metrics.json`.

The live run goal is **schema discovery**, not a benchmark. The unit tests' synthetic fixture shape (assistant messages with `usage.input_tokens` / `usage.output_tokens` / `usage.cache_creation_input_tokens` / `usage.cache_read_input_tokens`, and `Read` tool_use blocks with `input.file_path`) is verified against reality by inspecting the real nanoclaw transcript. The 1251-task sweep is Phase 7's concern; this run is verification, not throughput.

### How to verify (operator-executed)

The operator executes the following sequence on a machine that has the `nanoclaw-lq` repo checked out and the docker daemon running (the v1.0 proof environment):

1. Run the scoped task with `--keep-failed` so the ephemeral group + transcript survive for inspection:
   ```bash
   uv run python scripts/run_benchmark.py \
     --task corporate-ma/compare-matter-plan-against-engagement-letter \
     --adapter nanoclaw \
     --nanoclaw-dir ~/Projects/nanoclaw-lq \
     --model claude-opus-4-8 \
     --keep-failed \
     --output-dir ~/Projects/harvey-labs/results
   ```
   The `--keep-failed` flag retains the ephemeral group regardless of success or failure (it is the operator's debug toggle; the run is expected to succeed for the v1.0 proof task).

2. After the run completes, identify the surviving `group_id`. The script prints `[ephemeral] keeping failed group for debugging: <group_id>` to stderr ONLY if the run failed; for a successful run, the group is destroyed by default — so for a SUCCESSFUL run the operator must pass `--keep-failed` (which the command above already does; verify the per-run summary / final `summary.json` to confirm the group was kept). If the run succeeded and the group was destroyed, the schema-discovery step still works against the LAST run's transcript if the operator notes the `group_id` from the logs (the run_benchmark.py output includes a "kept group" line; alternatively inspect the most recent `data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/*.jsonl`).

3. Inspect the transcript jsonl:
   ```bash
   ls ~/Projects/nanoclaw-lq/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/
   cat ~/Projects/nanoclaw-lq/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl | head -20
   ```
   Confirm:
   - Assistant messages carry `message.usage.input_tokens`, `message.usage.output_tokens`, `message.usage.cache_creation_input_tokens`, `message.usage.cache_read_input_tokens` (the four fields the extractor reads).
   - Assistant messages carry `message.content[]` blocks of type `tool_use` with `name: "Read"` and `input.file_path` set to a container-internal path.
   - The `sessionId` field appears at a known location (top-level on the first line, per the test helper's assumption, OR on every line, OR on a per-message basis — the resolver's "first line's sessionId matches the shim's sessionId" rule needs verification).

4. Inspect the per-run `metrics.json`:
   ```bash
   cat ~/Projects/harvey-labs/results/<run_id>/metrics.json
   ```
   Confirm:
   - `input_tokens` is a non-null integer equal to the sum of `raw + cache_creation + cache_read` across the assistant messages (D-05 cache fold).
   - `output_tokens` is a non-null integer equal to the sum of `output_tokens` across the assistant messages.
   - `documents_read_list` is a non-empty list of container-internal paths (one entry per `Read` tool_use block, deduplicated with order preserved).
   - `documents_read` equals `len(documents_read_list)`.
   - `end_state` is `"clean"` (the v1.0 proof task is a well-formed run that produced a `STATUS: DONE`).
   - `metrics_provided` is `true` in the batch summary (after `write_batch_summary`).

5. If the transcript path layout DIFFERS from D-04's expected layout (e.g. `sessionId` is not on the first line, or the file naming pattern is different), the resolver in `lab_harness_runner/metrics_extraction.py` may need a small amendment (D-19). The amendment is a small change — e.g. glob for the newest jsonl in the group dir, or change the `sessionId` match to scan every line — and does NOT change the extractor surface. Flag the deviation in this SUMMARY (or a follow-up patch) so a follow-up resolver amendment can be planned.

6. After the live run confirms the schema, run the full unit test suite one more time:
   ```bash
   uv run --quiet python -m pytest -q
   ```
   All tests should remain green.

The verification is complete when the operator confirms (via typing "approved") that the live transcript matches the synthetic fixture shape and `metrics.json` carries the expected non-null values. If the layout differs, the operator describes the deviation so a follow-up amendment can be planned.

### Resume signal

Type "approved" once the live run's `metrics.json` shows non-null `input_tokens` / `output_tokens` matching the transcript sums and a non-empty `documents_read_list`. If the transcript path layout differs from D-04 (e.g. `sessionId` is on every line, not just the first), describe the deviation so a follow-up patch can amend the resolver per D-19.

### Deferred to follow-up plans (if D-19 amendment is needed)

If the operator reports a D-19 deviation, the orchestrator should plan a follow-up plan that:
- Amends the resolver in `lab_harness_runner/metrics_extraction.py` (small change: glob for the newest jsonl OR scan every line for the `sessionId` match, per D-19).
- Adds a regression test using a synthetic transcript that exercises the new resolution rule.
- Re-runs the full unit test suite to confirm green.
- Does NOT change the `MetricsExtractor` Protocol surface (D-19 explicit: "small amendment, no surface change").

The 1251-task sweep remains Phase 7's concern regardless of the D-19 outcome.

## User Setup Required

None for the autonomous portion (Task 1). The live verification run (Task 2) requires:
- A machine with `nanoclaw-lq` checked out at `~/Projects/nanoclaw-lq`.
- Docker daemon running (the v1.0 proof environment).
- A valid `harvey-labs` checkout at `~/Projects/harvey-labs` (for the `output-dir`).
- Access to the `claude-opus-4-8` model (the `nanoclaw` model list).

## Next Phase Readiness

- The D-20 docs addendum is in place and regression-locked; the cache fold note is no longer a quiet contract.
- Phase 6 Plan 03's autonomous work is complete (1 of 2 tasks). Task 2 is operator-deferred.
- The live run (Task 2) is the schema-discovery verification; the synthetic fixture shape has been verified against the v1.0 proof group by hand (per 06-CONTEXT canonical references), but the wired adapter has not been exercised against a live `claude-opus-4-8` ephemeral group end-to-end. The 1251-task sweep remains Phase 7's concern.

## Self-Check: PASSED

- `docs/adapter-guide.md` exists on disk and contains the new `## Metrics Extraction` section at L44.
- `tests/test_docs.py` exists on disk and contains the new `test_adapter_guide_documents_metrics_extraction_section` test.
- Commit `5aa66e4` (docs addendum) is reachable in `git log --oneline`.
- Commit `169aee4` (regression test) is reachable in `git log --oneline`.
- `uv run --quiet python -m pytest tests/test_docs.py -q` exits 0 with 6 passed (5 existing + 1 new).
- `uv run --quiet python -m pytest -q` exits 0 with 137 passed (136 from Plan 02 + 1 new doc test).
- The "Results are whole agent-system outcomes" invariant is preserved unchanged (`grep -c` returns exactly 1).
- All 11 required substrings from the plan's action block are present in the doc (verified by the regression test's loop).
- The new section is inserted between `## Contract` (L8) and `## Implementing run()` (L76), as the plan specified.
- No modifications to `lab_harness_runner/`, `tests/conftest.py`, `tests/test_metrics.py`, `tests/test_nanoclaw_adapter.py`, or `scripts/` (per the plan's "Do NOT modify" list).

---

*Phase: 06-metrics-extraction-and-model-routing*
*Completed: 2026-06-05 (Task 1; Task 2 deferred to operator)*
