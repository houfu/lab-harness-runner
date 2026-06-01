# Adapter Implementation Guide

This guide is for adding harness adapters to `lab-harness-runner`. It is an
implementation contract, not public onboarding material. LAB remains an
unmodified dependency, and every per-run result stays in the LAB checkout under
`/Users/houfu/Projects/harvey-labs/results/<run-id>/`.

## Contract

An adapter is any Python class that satisfies the `Adapter` protocol:

```python
class ExampleAdapter:
    def run(task_spec, output_dir) -> RunResult:
        ...
```

The required callable shape is `run(task_spec, output_dir) -> RunResult`.

`TaskSpec` is the parsed LAB task input:

- `task_id`: LAB task path such as `corporate-ma/example-task`.
- `instructions`: the task instructions read from LAB task metadata.
- `documents_dir`: read-only task documents directory.
- `expected_deliverables`: exact filenames expected in the output directory.
- `run_id`: the LAB run ID for this execution.

`RunResult` is the raw adapter outcome:

- `run_id`: must match the `TaskSpec.run_id` used for the run.
- `end_state`: one of `clean`, `agent_error`, or `timeout`.
- `wall_clock_seconds`: elapsed adapter runtime.
- `input_tokens`, `output_tokens`: optional token counts.
- `documents_read`, `total_vdr_files`, `documents_skipped`: optional document
  coverage counts.
- `documents_read_list`, `documents_skipped_list`: optional document lists.

The core package treats `RunResult.end_state` as adapter/protocol evidence. It is
not the same thing as the benchmark-facing result.

## Implementing run()

`run()` receives a complete task and an already-created LAB output directory.
The adapter should:

1. Dispatch `task_spec.instructions` to the external harness.
2. Expose `task_spec.documents_dir` to the harness as read-only input.
3. Make `output_dir` writable so deliverables are produced directly there.
4. Wait for that harness's terminal signal or stop at the configured timeout.
5. Return a `RunResult` with the raw observed `end_state`.

Adapters must write only to the provided `output_dir` for task deliverables. They
must not move LAB result folders, create alternate score locations, or mutate
LAB's task definitions. Harness-specific setup, polling, mounts, credentials, or
container behavior belong inside the adapter or its script-level configuration,
not in package core.

Nanoclaw is the current reference adapter. Its SQLite, mount, and container
internals are nanoclaw-specific details, not universal adapter requirements.

## Deliverables And Validation

LAB-compatible output layout is fixed:

- Run directory: `/Users/houfu/Projects/harvey-labs/results/<run-id>/`
- Deliverables: `/Users/houfu/Projects/harvey-labs/results/<run-id>/output/`
- Metrics: `/Users/houfu/Projects/harvey-labs/results/<run-id>/metrics.json`
- Scores: `/Users/houfu/Projects/harvey-labs/results/<run-id>/scores.json`
- Report: `/Users/houfu/Projects/harvey-labs/results/<run-id>/report.html`

The runner validates `TaskSpec.expected_deliverables` against files in
`output_dir` before scoring. Exact filenames are expected because LAB may do
fuzzy or LLM-assisted matching, but exact names avoid ambiguous failures. Missing
deliverables prevent scoring through `score_run()`.

Expected deliverable names are treated as relative filenames. Adapter code should
not accept absolute paths or traversal paths for deliverables, run IDs, task IDs,
batch IDs, or harness group IDs.

## Metrics And Status Semantics

`metrics.json` keeps LAB-compatible metric keys and adds diagnostics used for
honest whole-system reporting.

LAB-compatible fields:

- `input_tokens`
- `output_tokens`
- `wall_clock_seconds`
- `documents_read`
- `total_vdr_files`
- `documents_skipped`
- `documents_read_list`
- `documents_skipped_list`
- `end_state`

Diagnostic fields:

- `benchmark_status`
- `raw_end_state`
- `terminal_status_seen`
- `completion_signal`
- `expected_deliverables_present`
- `missing_deliverables`
- `adapter`
- `task_id`
- `run_id`
- `output_dir`

`raw_end_state` is copied from `RunResult.end_state`. `benchmark_status` is
derived after deliverable validation. If all expected deliverables are present,
the benchmark can be `clean` even when the raw adapter state is `timeout`.

Example mixed state:

```text
raw_end_state: "timeout"
terminal_status_seen: false
completion_signal: ""
expected_deliverables_present: true
missing_deliverables: []
benchmark_status: "clean"
```

This means valid deliverables exist and LAB can evaluate the run, but the adapter
did not observe `STATUS:DONE`. The timeout remains diagnostic evidence and must
not be rewritten to `clean` inside `RunResult`.

Raw adapter status and benchmark-facing status answer different questions:

- `raw_end_state`: what the harness protocol observed.
- `terminal_status_seen`: whether a terminal `STATUS:DONE` or `STATUS:ERROR`
  signal was observed.
- `completion_signal`: the raw terminal marker when available.
- `benchmark_status`: whether the run is usable for benchmark reporting after
  deliverable validation.

## Scoring And Report Preservation

The primary command is:

```bash
uv run python scripts/run_benchmark.py --task <area>/<task> --adapter nanoclaw --nanoclaw-dir <path> --group-id <id> --score --report
```

`--score` invokes LAB's evaluator and writes `scores.json` in the normal LAB run
folder. `--report` records the `report.html` path generated by LAB scoring.
`--compare task|area|all` may be used only with `--score`; it preserves LAB's
comparison dashboard paths and does not move per-run results.

Results are whole agent-system outcomes. Do not describe them as model-only
scores: the adapter, harness, container/runtime, prompt delivery, document
access, and LAB scoring path all contribute to the result.

## Batch Summaries And Variance

Batch runs execute a task x seed matrix around the same per-run contract. Each
individual run still writes its normal LAB folder at `results/<run-id>/`. Batch
metadata is written separately at:

`results/batches/<batch-id>/summary.json`

`summary.json` is metadata only. It must not contain an aggregate `scores.json`
and must not replace any per-run LAB artifact.

Batch summary rows include:

- `batch_id`
- `task_id`
- `seed`
- `adapter`
- `run_id`
- `run_dir`
- `output_dir`
- `metrics_path`
- `scores_path`
- `report_path`
- `benchmark_status`
- `raw_end_state`
- `terminal_status_seen`
- `expected_deliverables_present`
- `missing_deliverables`
- `score`
- `all_pass`
- `wall_clock_seconds`
- `input_tokens`
- `output_tokens`
- `documents_read`
- `total_vdr_files`

Variance is reported for score, wall-clock time, token counts, and document
coverage where values are available. `seed` is metadata unless an adapter
explicitly implements deterministic seeding; the current nanoclaw path does not
claim deterministic seed control.

## Adding Another Adapter Later

Additional adapters are deferred until a real second harness needs one. To add a
second adapter later, do not implement it in advance. Use this checklist when the
need exists:

1. Add a new adapter class that implements `run(task_spec, output_dir) -> RunResult`.
2. Keep all harness-specific dispatch, auth, mounts, polling, and status parsing
   in that adapter or its CLI wiring.
3. Return raw `RunResult.end_state` without converting deliverable presence into
   adapter success.
4. Register the adapter choice in `scripts/run_benchmark.py`.
5. Add tests that mock the harness boundary and prove deliverables, metrics, and
   status diagnostics are preserved.
6. Confirm batch rows and `summary.json` work without creating aggregate
   `scores.json` files.

The future adapter should reuse `TaskSpec`, `RunResult`,
`derive_benchmark_status()`, `write_metrics()`, `score_run()`, and
`write_batch_summary()` rather than duplicating those contracts.

## Checklist

- Implement `run(task_spec, output_dir) -> RunResult`.
- Write deliverables directly into the provided `output_dir`.
- Keep LAB result folders under `/Users/houfu/Projects/harvey-labs/results/<run-id>/`.
- Preserve raw/protocol state in `RunResult.end_state`.
- Let the runner derive `benchmark_status` after deliverable validation.
- Write `metrics.json` with LAB fields plus diagnostics.
- Preserve LAB `scores.json`, `report.html`, and comparison dashboards at LAB
  paths.
- For batch runs, write only metadata to `results/batches/<batch-id>/summary.json`.
- Treat seed as metadata unless deterministic seeding is implemented and tested.
- Document any adapter-specific operational requirements without exposing
  secrets, credentials, or private API keys.
