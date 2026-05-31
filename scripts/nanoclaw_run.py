"""Nanoclaw-LQ adapter run — dispatches a LAB task through nanoclaw-lq end to end.

Wires read_task -> build_result_dir -> NanoclawAdapter.run -> write_metrics, with
optional LAB evaluator scoring.  Mirrors scripts/fake_run.py but uses the real
nanoclaw-lq adapter instead of a local fake.

Usage:
    uv run python scripts/nanoclaw_run.py \\
        --task corporate-ma/compare-matter-plan-against-engagement-letter \\
        --nanoclaw-dir /path/to/nanoclaw-lq \\
        --group-id lab-runner
    uv run python scripts/nanoclaw_run.py \\
        --task antitrust-competition/analyze-antitrust-hsr-strategy \\
        --nanoclaw-dir /path/to/nanoclaw-lq \\
        --group-id lab-runner \\
        --score
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from lab_harness_runner import (
    build_result_dir,
    read_task,
    score_run,
    write_metrics,
)
from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter
from lab_harness_runner.task_reader import _lab_path, _reject_unsafe_relative_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="area/slug task path")
    parser.add_argument(
        "--run-id", default=None, help="explicit run ID (default: uuid4)"
    )
    parser.add_argument(
        "--lab-path",
        default=None,
        help="explicit LAB root (default: env var / home fallback)",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="invoke LAB evaluator after the run",
    )
    parser.add_argument(
        "--judge-model", default="claude-sonnet-4-6", help="judge model name"
    )
    # nanoclaw-specific args
    parser.add_argument(
        "--nanoclaw-dir",
        required=True,
        help="path to nanoclaw-lq repo root",
    )
    parser.add_argument(
        "--group-id",
        required=True,
        help="nanoclaw agent group ID for LAB runs",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="poll timeout in seconds (default: 600)",
    )
    args = parser.parse_args()

    _reject_unsafe_relative_path(args.task, "--task")
    if args.run_id is not None:
        _reject_unsafe_relative_path(args.run_id, "--run-id")
    _reject_unsafe_relative_path(args.group_id, "--group-id")

    run_id = args.run_id or str(uuid.uuid4())
    lab_path = (
        Path(args.lab_path).expanduser().resolve() if args.lab_path else _lab_path()
    )

    task_spec = read_task(lab_path=lab_path, task_id=args.task, run_id=run_id)
    run_dir, output_dir = build_result_dir(lab_path=lab_path, run_id=run_id)

    adapter = NanoclawAdapter(
        nanoclaw_dir=Path(args.nanoclaw_dir),
        group_id=args.group_id,
        timeout_seconds=args.timeout,
    )
    result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    write_metrics(run_dir=run_dir, result=result)

    print(f"Run directory: {run_dir}")
    print(f"Run ID: {run_id}")
    print(f"Deliverables: {', '.join(task_spec.expected_deliverables)}")
    print(f"End state: {result.end_state}")

    if args.score:
        scores_path = score_run(
            lab_path=lab_path,
            run_id=run_id,
            task_id=args.task,
            expected_deliverables=task_spec.expected_deliverables,
            judge_model=args.judge_model,
        )
        print(f"Scores: {scores_path}")
    else:
        print("Scoring skipped (pass --score to invoke evaluator)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
