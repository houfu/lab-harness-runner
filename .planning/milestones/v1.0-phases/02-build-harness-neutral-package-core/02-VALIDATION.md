---
phase: 02
slug: 02-build-harness-neutral-package-core
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-02T00:00:00+08:00
verified: 2026-06-02T00:00:00+08:00
---

# Phase 02 — Validation Strategy

Phase 02 is State B reconstruction: no prior VALIDATION.md existed, but PLAN,
SUMMARY, SECURITY, and VERIFICATION artifacts existed. This file maps the current
automated validation coverage to the Phase 02 plans and records the Nyquist audit
tests added on 2026-06-02.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/test_task_reader.py tests/test_result_builder.py tests/test_metrics.py tests/test_evaluator.py tests/test_adapter_exports.py tests/test_fake_run.py -q` |
| Full suite command | `uv run pytest tests/ -q` |
| Fake-run smoke command | `uv run python scripts/fake_run.py --help` |
| Estimated runtime | < 2 seconds locally |

## Sampling Rate

- After every task commit: run the quick Phase 02 command.
- After every plan wave: run `uv run pytest tests/ -q`.
- Before verification or release: full suite must be green.
- No watch-mode commands are required.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | Package scaffold and flat-layout import | T-02-01 | Build config is present and public package imports resolve | unit | `uv run pytest tests/test_adapter_exports.py -q` | yes | green |
| 02-01-02 | 01 | 1 | TaskSpec, RunResult, Adapter Protocol exports | T-02-03 | Public exports are available; structural adapter can run without inheriting Protocol; invalid end_state is rejected | unit | `uv run pytest tests/test_adapter_exports.py -q` | yes | green |
| 02-02-01 | 02 | 2 | Read LAB task metadata and inline instructions from task.json | T-02-03 | Unsafe task IDs are rejected before filesystem access; missing task.json and instructions fail explicitly | unit | `uv run pytest tests/test_task_reader.py -q` | yes | green |
| 02-02-02 | 02 | 2 | Extract expected deliverables from criteria[].deliverables | T-02-03 | Top-level deliverables dict is ignored; criteria deliverables are de-duplicated and sorted | unit | `uv run pytest tests/test_task_reader.py -q` | yes | green |
| 02-02-03 | 02 | 2 | Create results/<run-id>/output/ and validate run_id | T-02-04 | Unsafe run IDs raise before results paths are created; safe run IDs create run_dir and output_dir idempotently | integration | `uv run pytest tests/test_result_builder.py -q` | yes | green |
| 02-03-01 | 03 | 2 | Write metrics.json with safe defaults and zero preservation | CR-02 | None becomes safe zero/empty defaults; explicit zero values remain zero; no JSON null values are emitted | unit | `uv run pytest tests/test_metrics.py -q` | yes | green |
| 02-03-02 | 03 | 2 | Validate deliverables before evaluator subprocess | T-02-06 | Missing or unsafe deliverables fail before subprocess; validation checks output/ not run_dir | integration | `uv run pytest tests/test_evaluator.py -q` | yes | green |
| 02-03-03 | 03 | 2 | Invoke LAB evaluator safely | T-02-07 / T-02-08 | subprocess.run uses list form, cwd=lab_path, check=True, no shell interpolation | integration | `uv run pytest tests/test_evaluator.py -q` | yes | green |
| 02-04-01 | 04 | 3 | Test fixtures and Phase 02 unit coverage | T-02-10 / T-02-11 | Tests write under tmp_path and patch evaluator subprocess at module level | unit/integration | `uv run pytest tests/test_task_reader.py tests/test_result_builder.py tests/test_metrics.py tests/test_evaluator.py -q` | yes | green |
| 02-05-01 | 05 | 4 | fake_run task -> adapter -> result dir -> metrics wiring | T-02-12 / T-02-14 | fake_run runs against a temp LAB root, creates placeholder deliverables, writes metrics, and skips scoring unless requested | smoke | `uv run pytest tests/test_fake_run.py -q` | yes | green |
| 02-05-02 | 05 | 4 | fake_run CLI is safely invokable without LAB side effects | T-02-12 | Help command exits 0 without reading or writing LAB data | smoke | `uv run python scripts/fake_run.py --help` | yes | green |

## Wave 0 Requirements

Existing pytest infrastructure was present. Nyquist audit added focused coverage:

- tests/test_adapter_exports.py — package exports, structural Protocol behavior, end_state validation.
- tests/test_result_builder.py — unsafe run_id rejection before path creation.
- tests/test_metrics.py — explicit zero metric preservation.
- tests/test_fake_run.py — temp-LAB end-to-end fake_run wiring proof.

## Manual-Only Verifications

All Phase 02 behaviors have automated verification. Real LAB scoring with
`scripts/fake_run.py --score` remains opt-in because it can invoke external model
evaluation; Phase 02 only requires safe evaluator invocation mechanics, which are
covered with mocked subprocess assertions.

## Audit Trail

| Timestamp | Command | Result |
|-----------|---------|--------|
| 2026-06-02 | `uv run pytest tests/test_adapter_exports.py tests/test_result_builder.py tests/test_metrics.py tests/test_fake_run.py -q` | 23 passed in 0.06s |
| 2026-06-02 | `uv run pytest tests/test_task_reader.py tests/test_result_builder.py tests/test_metrics.py tests/test_evaluator.py tests/test_adapter_exports.py tests/test_fake_run.py -q` | 61 passed in 0.08s |
| 2026-06-02 | `uv run python scripts/fake_run.py --help` | exited 0; displayed CLI usage |
| 2026-06-02 | `uv run pytest tests/ -q` | 99 passed in 0.78s |

## Validation Sign-Off

- [x] All Phase 02 tasks have automated verification.
- [x] Sampling continuity verified; no three consecutive tasks depend on manual-only checks.
- [x] Wave 0 audit coverage added for missing behavioral edges.
- [x] No watch-mode flags.
- [x] Feedback latency is under 2 seconds locally.
- [x] `nyquist_compliant: true` set in frontmatter.

Approval: verified 2026-06-02
