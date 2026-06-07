# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-06-02
**Phases:** 4 | **Plans:** 13 | **Tests:** 99 passing

### What Was Built
- Harness-neutral package core: `TaskSpec`/`RunResult`/`Adapter` protocol, task reader, result builder, metrics writer, LAB evaluator wrapper
- nanoclaw-lq adapter: Node dispatch shim, read-only doc / read-write output mounts, `STATUS:` poll loop, wall-clock timeout
- Benchmark layer: status semantics (timeout-with-deliverable → benchmark-clean), primary benchmark command, LAB score/report/dashboard preservation
- Multi-task / multi-seed batch aggregation with variance reporting and a third-party adapter guide

### What Worked
- Front-loading live contract verification (Phase 1) against real LAB and nanoclaw surfaces before writing package code avoided building on assumptions from the source brief
- Keeping package-owned code harness-agnostic and isolating nanoclaw specifics to the adapter/CLI kept the core clean and the second-adapter path credible
- The end-to-end proof run surfaced the timeout-vs-deliverable semantics gap early enough to design Phase 4 around it

### What Was Inefficient
- Phase 3 stalled at a human-action checkpoint (mount-allowlist edit + LAB group setup) spanning two sessions — an external-dependency setup that could have been scheduled earlier
- Several SUMMARY.md files lacked clean one-liner frontmatter, so automated accomplishment extraction produced noise that needed manual cleanup at milestone close
- Phase 3 shipped without a formal `03-VERIFICATION.md`; closure relied on scattered equivalent evidence

### Patterns Established
- Verify-external-contracts-first as the opening phase for integration-heavy projects
- Distinguish raw protocol end-state (`end_state`) from reporting-derived `benchmark_status` so harness failures are never silently scored as model failures
- Batch summaries are metadata-only and never synthesize an aggregate `scores.json`

### Key Lessons
1. For integration projects, prove the external contract with a real run before committing to package design — the brief is a hypothesis, not a spec.
2. Enforce SUMMARY.md frontmatter discipline so milestone close can extract accomplishments without manual fixup.
3. Schedule human/external-dependency setup steps (allowlists, group provisioning) ahead of the phase that blocks on them.

### Cost Observations
- Sessions: ~4 (2026-05-30 → 2026-06-02)
- Notable: most plans ran in 2-8 minutes of execution; the long pole was external setup latency, not compute

---

## Milestone: v1.1 — Post-v1.0 hardening & metrics fidelity

**Shipped:** 2026-06-08
**Phases:** 3 | **Plans:** 10 | **Tests:** 141 passing

### What Was Built
- Honest unmeasured-metrics contract: nullable `RunResult` fields, `write_metrics` propagates `None`→JSON `null`, per-row `metrics_provided` + `unmeasured_counts` + list-variance lengths in aggregation (CON-01..03)
- `MetricsExtractor` protocol + four extractors + `is_claude_model` routing wired into the nanoclaw adapter; Ollama path returns nulls without raising (EXT-01..04)
- Hardened `sweep.sh`: empirically-grounded `TIMEOUT` rationale, CI-consumable `inventory` dual-output, post-run `summary:` line, non-zero exit with per-run stderr (SWP-01..04)
- Opt-in `LAB_COMPARE` shell-out to LAB's `evaluation.compare` — no new aggregator in the runner (LAB-01..02)

### What Worked
- The Phase 6 `checkpoint:human-verify` live-run gate did exactly its job: it caught the D-19 session-id mismatch that every synthetic unit test missed. Schema-discovery against reality is irreplaceable for integration code.
- Code review caught 6 real defects in Phase 7 (incl. a clean-sweep `set -u` crash) before they shipped; the deterministic fixture UAT closed Phase 7's human item in seconds instead of a 1251-task run.
- Worktree-isolated parallel execution merged cleanly across all waves with no conflicts.

### What Was Inefficient
- Phase 6 was fully executed and UAT'd but never formally verified or closed — its ROADMAP/REQUIREMENTS tracking sat stale at "0/3 Planned" and was only discovered at milestone-close, forcing a verify-and-close detour mid-archive.
- The Phase 7 requirements traceability rows lagged at TBD/pending even after the phase completed — `phase.complete` did not propagate them, requiring a manual reconciliation.
- The synthetic test fixtures encoded an unverified assumption (shim session id == transcript `sessionId`) that reality disproved; the assumption survived all the way to the live run.

### Patterns Established
- Never close a milestone without confirming every in-scope phase actually reached `VERIFICATION status: passed` — "has SUMMARY.md" ≠ "verified and closed."
- For extractors that parse external tool output, a per-group/per-run scoping fallback beats an id-equality filter when the id namespaces are not provably the same.
- Treat a live human-verify gate as a schema-discovery instrument, not a rubber stamp — its findings can be load-bearing.

### Key Lessons
1. A passing unit suite proves the code matches its fixtures, not that the fixtures match reality — keep at least one live gate for integration boundaries.
2. Phase close-out is part of execution, not bookkeeping: an unverified-but-built phase silently breaks milestone accounting.
3. When `phase.complete` leaves tracking rows stale, reconcile REQUIREMENTS/ROADMAP explicitly before archiving.

### Cost Observations
- Sessions: spanned multiple (2026-06-05 → 2026-06-08); model mix Opus (orchestration) + Sonnet (executors/verifiers/reviewers)
- Notable: parallel worktree executors kept per-wave wall-clock low; the expensive step was the operator-run live verification (one full agent run)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 4 | Established verify-contracts-first opening and harness-agnostic core boundary |
| v1.1 | 3 | Live human-verify gates as schema-discovery; close-out discipline (verified ≠ built) surfaced as a milestone-accounting risk |

### Cumulative Quality

| Milestone | Tests | Zero-Dep Additions |
|-----------|-------|-------------------|
| v1.0 | 99 | core package (uv + black) |
| v1.1 | 141 | metrics_extraction module; sweep.sh hardening (bash, no new deps) |

### Top Lessons (Verified Across Milestones)

1. Verify external contracts with a real run before designing around them. *(v1.0, reaffirmed v1.1)*
2. A green unit suite proves code-matches-fixtures, not fixtures-match-reality — keep a live gate at every integration boundary. *(v1.1)*
3. Phase close-out (verification + tracking) is part of execution; a built-but-unverified phase silently corrupts milestone accounting. *(v1.1)*
