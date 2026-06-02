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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 4 | Established verify-contracts-first opening and harness-agnostic core boundary |

### Cumulative Quality

| Milestone | Tests | Zero-Dep Additions |
|-----------|-------|-------------------|
| v1.0 | 99 | core package (uv + black) |

### Top Lessons (Verified Across Milestones)

1. Verify external contracts with a real run before designing around them. *(v1.0)*
