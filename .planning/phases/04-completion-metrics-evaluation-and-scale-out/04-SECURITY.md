---
phase: 04
slug: 04-completion-metrics-evaluation-and-scale-out
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-02
---

# Phase 04 - Security

Per-phase security contract: plan-time threat register verification for completion metrics, evaluation, and scale-out.

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| output_dir filesystem -> status derivation | Adapter-produced files affect benchmark-facing status. | Expected deliverable names and output files. |
| adapter RunResult -> metrics/reporting | Raw adapter protocol state enters metrics and aggregate reporting. | `RunResult.end_state`, timing, token, and document metrics. |
| CLI -> filesystem | User task/run/group/batch flags influence LAB paths and adapter configuration. | `task_id`, `run_id`, `group_id`, `batch_id`, task lists, seed metadata. |
| runner -> LAB evaluator | Runner invokes LAB scoring and comparison subprocesses. | Subprocess arguments and LAB working directory. |
| aggregate metadata -> LAB result tree | Batch summaries live near LAB artifacts. | Batch rows, scores paths, variance summaries. |
| docs -> benchmark interpretation | Documentation shapes future adapter behavior and result interpretation. | Adapter contract, status semantics, examples. |

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status | Evidence |
|-----------|----------|-----------|-------------|------------|--------|----------|
| T-04-01-R | Repudiation | status diagnostics | mitigate | Preserve raw protocol/status evidence separately from `benchmark_status`. | closed | `lab_harness_runner/status.py:37` returns `raw_end_state`, `terminal_status_seen`, `completion_signal`, `expected_deliverables_present`, and `missing_deliverables` alongside `benchmark_status`; `tests/test_status.py:32` covers timeout plus valid deliverables. |
| T-04-01-T | Tampering | expected deliverable validation | mitigate | Reject absolute/traversal expected deliverables before joining to `output_dir`. | closed | `lab_harness_runner/status.py:17` validates each expected deliverable through `_reject_unsafe_relative_path` before `(output_dir / deliverable_path)`; helper rejects absolute/traversal at `lab_harness_runner/task_reader.py:10`; test coverage at `tests/test_status.py:106`. |
| T-04-02-T | Tampering | CLI path inputs | mitigate | Validate `task_id`, `run_id`, `group_id`, and batch metadata before filesystem joins. | closed | `scripts/run_benchmark.py:114` validates single-run `task`, `run_id`, and `group_id`; `scripts/run_benchmark.py:131` and `scripts/run_benchmark.py:143` validate task-file entries and expanded tasks; `scripts/run_benchmark.py:238` validates `batch_id`; `lab_harness_runner/aggregation.py:100` validates `batch_id` before writing under results. |
| T-04-02-E | Elevation of privilege | scoring/report subprocess | mitigate | Use list-form subprocess calls with `shell=False` default and `cwd=lab_path`; no user input interpolated into shell strings. | closed | `lab_harness_runner/evaluator.py:45` invokes `subprocess.run([...], cwd=lab_path, check=True, ...)` for scoring; `lab_harness_runner/evaluator.py:90` builds list-form compare args and `lab_harness_runner/evaluator.py:109` invokes `subprocess.run(cmd, cwd=lab_path, ...)`; tests assert list args and cwd at `tests/test_evaluator.py:9`, `tests/test_evaluator.py:46`, and `tests/test_evaluator.py:285`. |
| T-04-02-R | Repudiation | command output | mitigate | Print/write `benchmark_status` and `raw_end_state` for every run. | closed | `scripts/run_benchmark.py:295` derives diagnostics; `scripts/run_benchmark.py:303` writes diagnostics to metrics; `scripts/run_benchmark.py:309` includes `benchmark_status` and `raw_end_state` in returned/printed summary; `scripts/nanoclaw_run.py:32` prints both fields for compatibility output. |
| T-04-03-T | Tampering | aggregate summary placement | mitigate | Write metadata-only `summary.json`; never write aggregate `scores.json` or fake LAB config. | closed | `lab_harness_runner/aggregation.py:100` writes only `results/batches/<batch-id>/summary.json`; `lab_harness_runner/aggregation.py:108` fixes filename to `summary.json`; tests assert no batch `scores.json` at `tests/test_aggregation.py:108` and `tests/test_run_benchmark.py:318`. |
| T-04-03-R | Repudiation | variance reporting | mitigate | Store per-run rows and variance fields traceable to run IDs and score paths. | closed | `lab_harness_runner/aggregation.py:19` defines required row fields including `run_id`, paths, status fields, scores, and metrics; `lab_harness_runner/aggregation.py:85` returns rows plus variance; `scripts/run_benchmark.py:192` builds per-run rows with `run_id`, `scores_path`, and variance inputs; tests assert rows and variance at `tests/test_aggregation.py:37`. |
| T-04-03-D | Denial of Service | batch expansion | accept | Batch size is user-selected local CLI work; no service endpoint is exposed. | closed | Accepted risk logged below as `AR-04-03-D`; plan disposition is accept in `04-03-PLAN.md`. |
| T-04-04-R | Repudiation | failure semantics docs | mitigate | Document `raw_end_state` and `benchmark_status` as separate fields with timeout-valid-output example. | closed | `docs/adapter-guide.md:110` separates `raw_end_state` from `benchmark_status`; `docs/adapter-guide.md:114` gives timeout-with-valid-deliverables example; `docs/adapter-guide.md:125` states timeout remains diagnostic evidence. |
| T-04-04-I | Information disclosure | examples | mitigate | Use placeholder paths and no credentials/secrets in examples. | closed | `docs/adapter-guide.md:142` uses placeholder CLI values (`<area>/<task>`, `<path>`, `<id>`); `docs/adapter-guide.md:229` explicitly forbids exposing secrets, credentials, or private API keys. |
| T-04-04-T | Tampering | future adapter path handling | mitigate | Document adapters must write only to provided `output_dir` and must not move LAB artifacts. | closed | `docs/adapter-guide.md:52` states adapters write only to `output_dir` and must not move LAB result folders; `docs/adapter-guide.md:76` forbids absolute/traversal paths; `docs/adapter-guide.md:217` repeats the implementation checklist. |

Status vocabulary: `closed` means the declared mitigation was found in implementation or documentation evidence appropriate to its disposition. `open` means a declared mitigation was absent.

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-03-D | T-04-03-D | Batch expansion is local CLI work selected by the operator. There is no remote service endpoint, scheduler, or untrusted public caller in Phase 04 scope. | Plan-time threat register | 2026-06-02 |

## Threat Flags

| Flag | Source | Mapping | Status |
|------|--------|---------|--------|
| threat_flag: evaluator-subprocess | `04-02-SUMMARY.md` | T-04-02-E | closed |

No unregistered threat flags.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-02 | 11 | 11 | 0 | Codex gsd-secure-phase |

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

Approval: verified 2026-06-02
