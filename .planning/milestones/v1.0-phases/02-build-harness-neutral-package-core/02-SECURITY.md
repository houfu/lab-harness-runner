---
phase: 02
slug: 02-build-harness-neutral-package-core
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-01T23:39:05Z
---

# Phase 02 - Security

Plan-time threat register verification for Phase 02. This audit verifies declared
mitigations only; it does not add unrelated retroactive threats.

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| pyproject.toml -> uv install | Build/dev packages are resolved by uv | Package names and versions |
| task_id -> filesystem paths | Task ID becomes a path below `lab_path/tasks/` | User/caller-controlled string |
| run_id -> filesystem paths | Run ID becomes a path below `lab_path/results/` | User/caller-controlled string |
| expected_deliverables -> output file checks | Deliverable filenames become paths below `output/` | Task metadata strings |
| HARVEY_LAB_PATH / --lab-path -> filesystem root | Environment or CLI value selects LAB root | Local path |
| run_id/task_id -> subprocess CLI args | Values passed to LAB evaluator process | CLI arguments |
| --score -> subprocess / API cost | Optional scoring invokes LAB evaluator | Explicit user action |
| pytest tmp_path -> filesystem | Tests write fixture data | Temporary local files |

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| 02-01/T-02-01 | Tampering | `pyproject.toml` `requires` | accept | Accepted risk AR-02-01 documents trusted provenance for uv_build/black/pytest. | closed |
| 02-01/T-02-02 | Tampering | `TaskSpec.task_id` path use | mitigate | `read_task` validates task_id with `_reject_unsafe_relative_path` before `task_dir` construction. Evidence: `lab_harness_runner/task_reader.py:10`, `lab_harness_runner/task_reader.py:55`. | closed |
| 02-01/T-02-03 | Tampering | `RunResult.end_state` string | accept | Accepted risk AR-02-03 documents diagnostic-only phase disposition; current code also validates allowed values. Evidence: `lab_harness_runner/adapter.py:28`, `lab_harness_runner/adapter.py:40`. | closed |
| 02-01/T-02-SC | Tampering | uv add installs | mitigate | Provenance assumption recorded as accepted risk AR-02-SC-01 because slopcheck was unavailable in the plan. | closed |
| 02-02/T-02-03 | Tampering | `task_id` path traversal | mitigate | `_reject_unsafe_relative_path` rejects absolute, empty, dot, and dot-dot segments before filesystem access. Evidence: `lab_harness_runner/task_reader.py:10`, `lab_harness_runner/task_reader.py:55`. | closed |
| 02-02/T-02-04 | Tampering | `run_id` path traversal | accept | Accepted risk AR-02-04 documents original phase trust assumption; current implementation also validates run_id in result and scoring paths. Evidence: `lab_harness_runner/result_builder.py:27`, `lab_harness_runner/evaluator.py:25`. | closed |
| 02-02/T-02-05 | Information Disclosure | `HARVEY_LAB_PATH` env var | accept | Accepted risk AR-02-05 documents local development path disclosure as negligible. | closed |
| 02-02/T-02-SC | Tampering | installs | accept | Accepted risk AR-02-SC-02 documents no new packages in plan 02. | closed |
| 02-03/T-02-06 | Tampering | expected deliverables path join | accept | Accepted risk AR-02-06 documents task metadata origin; current implementation also validates each deliverable before checking `output/`. Evidence: `lab_harness_runner/evaluator.py:28`, `lab_harness_runner/evaluator.py:32`. | closed |
| 02-03/T-02-07 | Tampering | run_id/task_id subprocess args | accept | Accepted risk AR-02-07 documents list-form subprocess use; current code validates both inputs before invocation. Evidence: `lab_harness_runner/evaluator.py:25`, `lab_harness_runner/evaluator.py:45`. | closed |
| 02-03/T-02-08 | Elevation of Privilege | `subprocess.run` invokes uv | accept | Accepted risk AR-02-08 documents trusted local uv, `cwd=lab_path`, `check=True`, no shell. Evidence: `lab_harness_runner/evaluator.py:45`, `lab_harness_runner/evaluator.py:59`. | closed |
| 02-03/T-02-09 | Denial of Service | judge model / API cost | accept | Accepted risk AR-02-09 documents scoring as explicit opt-in. Evidence: `scripts/fake_run.py:95`, `scripts/fake_run.py:126`. | closed |
| 02-03/T-02-SC | Tampering | installs | accept | Accepted risk AR-02-SC-03 documents no new packages in plan 03. | closed |
| 02-04/T-02-10 | Tampering | test fixture filesystem writes | accept | Accepted risk AR-02-10 documents pytest `tmp_path` isolation; tests use temporary fixture roots. Evidence: `tests/test_task_reader.py:21`, `tests/test_result_builder.py:10`. | closed |
| 02-04/T-02-11 | Tampering | evaluator subprocess mock | mitigate | Tests patch `lab_harness_runner.evaluator.subprocess.run` at module level and assert missing deliverables do not call subprocess. Evidence: `tests/test_evaluator.py:18`, `tests/test_evaluator.py:116`. | closed |
| 02-04/T-02-SC | Tampering | installs | accept | Accepted risk AR-02-SC-04 documents no new packages in plan 04. | closed |
| 02-05/T-02-12 | Tampering | `--task` and `--run-id` traversal | mitigate | `fake_run.py` imports the canonical validator and applies it to both CLI args before read/build calls. Evidence: `scripts/fake_run.py:27`, `scripts/fake_run.py:105`. | closed |
| 02-05/T-02-13 | Tampering | `--lab-path` CLI arg | accept | Accepted risk AR-02-13 documents explicit developer-controlled lab root; code normalizes with `expanduser().resolve()`. Evidence: `scripts/fake_run.py:110`. | closed |
| 02-05/T-02-14 | Elevation of Privilege | `--score` subprocess trigger | accept | Accepted risk AR-02-14 documents scoring as opt-in; subprocess only invoked under `if args.score`. Evidence: `scripts/fake_run.py:126`. | closed |
| 02-05/T-02-15 | Information Disclosure | local run directory contents | accept | Accepted risk AR-02-15 documents local-only placeholder deliverables. Evidence: `scripts/fake_run.py:64`, `scripts/fake_run.py:73`. | closed |
| 02-05/T-02-SC | Tampering | installs | accept | Accepted risk AR-02-SC-05 documents no new packages in plan 05. | closed |

## Code Review Finding Classification

| Finding | Classification | Evidence |
|---------|----------------|----------|
| CR-01 run_id path traversal | mitigated | `build_result_dir` validates `run_id`; `score_run` validates `run_id` and `task_id`. Evidence: `lab_harness_runner/result_builder.py:27`, `lab_harness_runner/evaluator.py:25`. |
| CR-02 falsy-zero metrics bug | mitigated | `write_metrics` uses explicit `is not None` checks, preserving legitimate zero values. Evidence: `lab_harness_runner/metrics.py:33`. |
| CR-03 import errors hidden by `__init__.py` | mitigated | Current exports are direct imports; no `try/except ImportError` guards remain. Evidence: `lab_harness_runner/__init__.py:3`. |
| WR-01 unvalidated `end_state` | mitigated | `RunResult.end_state` is a `Literal`; `__post_init__` raises for invalid values. Evidence: `lab_harness_runner/adapter.py:28`, `lab_harness_runner/adapter.py:40`. |
| WR-02 duplicated fake_run validation | mitigated | `fake_run.py` imports `_lab_path` and `_reject_unsafe_relative_path` from package code. Evidence: `scripts/fake_run.py:27`. |
| WR-03 opaque subprocess errors | mitigated | Evaluator calls capture stdout/stderr and re-raise `CalledProcessError` preserving output. Evidence: `lab_harness_runner/evaluator.py:45`, `lab_harness_runner/evaluator.py:64`. |
| WR-04 implicit `run_dir` creation | mitigated | `build_result_dir` explicitly creates `run_dir` before `output_dir`. Evidence: `lab_harness_runner/result_builder.py:30`. |
| IN-01 metrics zero test gap | mitigated by implementation | Explicit `None` checks remove the truthiness gap. Evidence: `lab_harness_runner/metrics.py:33`. |
| IN-02 private validator used across modules | documented accepted internal pattern | The validator remains private but is consistently imported by internal package modules and script code. Evidence: `lab_harness_runner/result_builder.py:5`, `lab_harness_runner/evaluator.py:7`, `scripts/fake_run.py:27`. |
| IN-03 duplicate evaluator tests | accepted non-security test hygiene issue | No security mitigation required; module-level subprocess mocking remains present. Evidence: `tests/test_evaluator.py:18`, `tests/test_evaluator.py:116`. |

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | 02-01/T-02-01 | uv_build, black, and pytest are high-provenance ecosystem packages; phase research records uv_build as Astral's backend and black as PSF-sponsored. | security audit | 2026-06-01 |
| AR-02-03 | 02-01/T-02-03 | Original phase accepted `end_state` as diagnostic-only; current implementation additionally validates it. | security audit | 2026-06-01 |
| AR-02-SC-01 | 02-01/T-02-SC | slopcheck was unavailable; package provenance was reviewed and recorded as assumed/high provenance in phase research. | security audit | 2026-06-01 |
| AR-02-04 | 02-02/T-02-04 | Original phase accepted trusted caller-origin run_id; current implementation additionally validates run_id in package entry points. | security audit | 2026-06-01 |
| AR-02-05 | 02-02/T-02-05 | LAB path is a local development path in a local-only tool context, not a secret. | security audit | 2026-06-01 |
| AR-02-SC-02 | 02-02/T-02-SC | No new packages were installed in plan 02. | security audit | 2026-06-01 |
| AR-02-06 | 02-03/T-02-06 | Deliverables originate from task metadata and current scoring validation constrains them to safe relative paths. | security audit | 2026-06-01 |
| AR-02-07 | 02-03/T-02-07 | CLI arguments are list-form subprocess args, not shell-interpolated; current implementation also validates paths. | security audit | 2026-06-01 |
| AR-02-08 | 02-03/T-02-08 | uv is a trusted local tool; evaluator invocation uses `cwd=lab_path`, `check=True`, captured output, and no shell. | security audit | 2026-06-01 |
| AR-02-09 | 02-03/T-02-09 | Scoring and judge-model cost are explicit user opt-in via `--score`. | security audit | 2026-06-01 |
| AR-02-SC-03 | 02-03/T-02-SC | No new packages were installed in plan 03. | security audit | 2026-06-01 |
| AR-02-10 | 02-04/T-02-10 | Test fixture writes are scoped to pytest temporary paths. | security audit | 2026-06-01 |
| AR-02-SC-04 | 02-04/T-02-SC | No new packages were installed in plan 04. | security audit | 2026-06-01 |
| AR-02-13 | 02-05/T-02-13 | `--lab-path` is an explicit developer-controlled filesystem root for a local tool. | security audit | 2026-06-01 |
| AR-02-14 | 02-05/T-02-14 | Evaluator subprocess and API costs require explicit `--score`. | security audit | 2026-06-01 |
| AR-02-15 | 02-05/T-02-15 | Placeholder deliverables are written to local results only. | security audit | 2026-06-01 |
| AR-02-SC-05 | 02-05/T-02-SC | No new packages were installed in plan 05. | security audit | 2026-06-01 |
| AR-02-IN-02 | Review IN-02 | `_reject_unsafe_relative_path` remains private but is used consistently within package-owned modules; no public API commitment needed in Phase 02. | security audit | 2026-06-01 |
| AR-02-IN-03 | Review IN-03 | Duplicate tests are a maintainability issue, not a security blocker. Required module-level subprocess mocking is present. | security audit | 2026-06-01 |

## Unregistered Flags

None. `02-04-SUMMARY.md` and `02-05-SUMMARY.md` both report no new threat surface
beyond their plan threat models.

## Verification Commands

| Command | Result |
|---------|--------|
| `uv run pytest tests/test_task_reader.py tests/test_result_builder.py tests/test_metrics.py tests/test_evaluator.py -q` | `55 passed in 0.05s` |

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-01 | 21 | 21 | 0 | Codex gsd-secure-phase |

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-01
