# Requirements: v1.1 — Post-v1.0 hardening & metrics fidelity

**Status:** DRAFT (awaiting roadmap traceability)

## Milestone Goal

Make nanoclaw-backed metrics honest (measured vs. unmeasured) and harden the
post-v1.0 sweep driver, without changing the runner's role as a thin
orchestrator over Harvey LAB.

## Active

### Contract & metrics honesty (CON)

- [ ] **CON-01**: `RunResult` distinguishes "adapter measured 0" from
  "adapter did not measure". An adapter that did not measure a field
  must be representable in `RunResult` and `metrics.json` as distinct
  from a field whose value is genuinely zero.
- [ ] **CON-02**: `write_metrics` writes `null` (not `0`) for unmeasured
  fields; aggregation (`build_summary`, `summarize_variance`,
  `write_batch_summary`) skips null entries in mean / sum / variance
  computations.
- [ ] **CON-03**: Aggregation results that include unmeasured entries
  are visibly annotated in the batch summary and any per-row metric
  output, so a downstream reader can tell which entries were measured
  vs. unmeasured (e.g. a `metrics_provided` field, a count of unmeasured
  rows, or equivalent).

### Metrics extraction (EXT)

- [ ] **EXT-01**: `MetricsExtractor` protocol with one method returning
  the metric fields of a `RunResult` from the agent's `messages_out`.
- [ ] **EXT-02**: `AnthropicUsageExtractor` reads `usage` from assistant
  messages in `messages_out` and sums `input_tokens` / `output_tokens`
  across the run.
- [ ] **EXT-03**: Document-read extractor enumerates `tool_use` blocks in
  assistant messages and collects document filenames (or equivalent
  read-tool identifiers) into `documents_read_list`.
- [ ] **EXT-04**: `NanoclawAdapter` instantiates the right extractor
  based on the configured model; the Ollama path returns null metrics
  without raising.

### Sweep driver hardening (SWP)

- [ ] **SWP-01**: `sweep.sh` defaults are documented in the script;
  the `TIMEOUT` default has a rationale grounded in existing
  `results/` wall-clock data, not a guess.
- [ ] **SWP-02**: `sweep.sh inventory` output is both machine-readable
  (one path per line, suitable for `xargs`) and human-readable (per-task
  status counts).
- [ ] **SWP-03**: `sweep.sh` post-run summary prints counts of
  `clean` / `agent_error` / `timeout` / `missing-deliverable` runs
  derived from the `metrics.json` files it wrote.
- [ ] **SWP-04**: Sweep failures exit non-zero with a per-run error log
  path printed to stderr, so a CI consumer can act without re-scanning
  the results tree.

### LAB-aggregation integration (LAB)

- [ ] **LAB-01**: `sweep.sh` produces output compatible with LAB's
  existing batch-summary tool (no new aggregator lives in the runner).
- [ ] **LAB-02**: After a sweep, `sweep.sh` can invoke LAB's
  comparison / aggregation as a final step (opt-in via flag or
  environment).

## Quality

- Stay thin: no aggregation logic in the runner that duplicates LAB.
- The contract change must be testable in isolation (no live nanoclaw
  run required for Phase 1).
- The AnthropicUsageExtractor must be verified against a real nanoclaw
  run before Phase 2 closes.
- Sweep hardening must be verifiable against existing `results/` data;
  no new live sweep is required if the data is sufficient.

## Deferred (carried from v1.0)

- REQ-23: Additional adapters beyond nanoclaw-lq (deferred until a real
  second harness needs one).
- REQ-24: Public package publishing and broader community onboarding.
- Upstream LAB documentation PR for stable task/result contracts.
- Sweep driver work to add a per-task token/duration histogram (defer
  until metrics extraction lands and gives us real data to plot).

## Out of Scope

- A second reference adapter (REQ-23). v1.1 has no second-harness
  signal to drive its design.
- A new aggregation tool in the runner. LAB remains the source of
  scoring and report generation (PROJECT.md locked decision).
- Changing the runner's role from "thin orchestrator" to a heavier
  framework. Sweep integration with LAB must use LAB's existing tools.
- Live judge-backed scoring changes. LAB judge remains
  environment-dependent per the v1.0 milestone note.
- The deliverable-gated poll short-circuit (introduced in `5974d69`).
  v1.1 inherits it as-is; tightening the gate is a future discussion
  if false-positive "deliverable present" cases appear.

## Traceability

| Requirement | Phase | Plan(s) | Status |
| ----------- | ----- | ------- | ------ |
| CON-01 | Phase 5 | TBD | pending |
| CON-02 | Phase 5 | TBD | pending |
| CON-03 | Phase 5 | TBD | pending |
| EXT-01 | Phase 6 | TBD | pending |
| EXT-02 | Phase 6 | TBD | pending |
| EXT-03 | Phase 6 | TBD | pending |
| EXT-04 | Phase 6 | TBD | pending |
| SWP-01 | Phase 7 | TBD | pending |
| SWP-02 | Phase 7 | TBD | pending |
| SWP-03 | Phase 7 | TBD | pending |
| SWP-04 | Phase 7 | TBD | pending |
| LAB-01 | Phase 7 | TBD | pending |
| LAB-02 | Phase 7 | TBD | pending |
