# lab-harness-runner

Harness-neutral runner experiments for Harvey LAB.

This package provides a small Python layer for running external harnesses
against LAB tasks while preserving LAB's normal result layout and scoring
artifacts. The current reference adapter is `nanoclaw`.

## What It Does

- Reads LAB task metadata into a `TaskSpec`.
- Creates normal LAB result folders at `results/<run-id>/`.
- Runs an adapter that writes deliverables into `results/<run-id>/output/`.
- Writes LAB-compatible `metrics.json` with extra diagnostic fields.
- Optionally invokes LAB scoring, report generation, and comparison dashboards.
- Supports task x seed batch runs with metadata-only summaries.
- Keeps raw adapter state separate from benchmark-facing status.

## Install

This project uses `uv` and Python 3.11 or newer.

```bash
uv sync
```

Run tests:

```bash
uv run pytest tests/ -q
```

## Primary Command

Single task:

```bash
uv run python scripts/run_benchmark.py \
  --task <area>/<task> \
  --adapter nanoclaw \
  --nanoclaw-dir <path-to-nanoclaw-lq> \
  --group-id <group-id> \
  --score \
  --report
```

Batch run:

```bash
uv run python scripts/run_benchmark.py \
  --task <area>/<task-a> \
  --task <area>/<task-b> \
  --seeds 1,2,3 \
  --batch-id <batch-id> \
  --adapter nanoclaw \
  --nanoclaw-dir <path-to-nanoclaw-lq> \
  --group-id <group-id> \
  --score \
  --report
```

Comparison dashboards are opt-in and require scoring:

```bash
uv run python scripts/run_benchmark.py \
  --task <area>/<task> \
  --adapter nanoclaw \
  --nanoclaw-dir <path-to-nanoclaw-lq> \
  --group-id <group-id> \
  --score \
  --compare task
```

By default, the runner resolves the LAB checkout from `HARVEY_LAB_PATH` or a
standard sibling checkout location. You can pass `--lab-path <path-to-lab>` to
override that explicitly.

## Result Layout

Per-run artifacts stay in LAB's standard result tree:

```text
results/<run-id>/
  output/
  metrics.json
  scores.json
  report.html
```

Batch metadata is separate and must not replace or move per-run LAB artifacts:

```text
results/batches/<batch-id>/summary.json
```

Batch summaries are metadata only. They do not create aggregate `scores.json`
files.

## Status Semantics

Adapters return raw protocol state through `RunResult.end_state`:

- `clean`
- `agent_error`
- `timeout`

The benchmark-facing status is derived later from deliverable validation. A run
can have:

```text
raw_end_state: "timeout"
benchmark_status: "clean"
```

That means the adapter did not observe the terminal success signal, but the
expected deliverables exist and LAB can evaluate the output. The raw timeout is
preserved as diagnostic evidence.

## Adapter Contract

Adapters implement:

```python
def run(task_spec, output_dir) -> RunResult:
    ...
```

Adapters should write deliverables only to the provided `output_dir`, return the
raw observed `RunResult`, and leave scoring/reporting to the runner.

See [docs/adapter-guide.md](docs/adapter-guide.md) for the full adapter contract.

## Useful Commands

```bash
uv run pytest tests/test_status.py tests/test_metrics.py -q
uv run pytest tests/test_evaluator.py tests/test_run_benchmark.py -q
uv run pytest tests/test_aggregation.py tests/test_docs.py -q
uv run python scripts/run_benchmark.py --help
uv run python scripts/nanoclaw_run.py --help
```

## Notes

- LAB is treated as an unmodified dependency.
- `nanoclaw` is the only implemented adapter today.
- Additional adapters should reuse the shared `TaskSpec`, `RunResult`, metrics,
  status, evaluator, and aggregation helpers rather than duplicating the runner
  contract.
