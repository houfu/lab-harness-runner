"""Primary LAB-compatible benchmark command for nanoclaw single runs."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from lab_harness_runner import (
    build_result_dir,
    compare_run,
    derive_benchmark_status,
    read_task,
    report_path_for_run,
    score_run,
    write_metrics,
)
from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter
from lab_harness_runner.task_reader import _lab_path, _reject_unsafe_relative_path


class BenchmarkArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args: list[str] | None = None, namespace: Any = None) -> Any:
        parsed = super().parse_args(args, namespace)
        if parsed.compare and not parsed.score:
            self.error("--compare requires --score")
        if parsed.report and not parsed.score:
            self.error("--report requires --score")
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = BenchmarkArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="area/slug task path")
    parser.add_argument(
        "--adapter",
        choices=["nanoclaw"],
        default="nanoclaw",
        help="adapter to run (default: nanoclaw)",
    )
    parser.add_argument("--run-id", default=None, help="explicit run ID")
    parser.add_argument(
        "--lab-path",
        default=None,
        help="explicit LAB root (default: HARVEY_LAB_PATH or ~/Projects/harvey-labs)",
    )
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
    parser.add_argument(
        "--score",
        action="store_true",
        help="invoke LAB evaluator after adapter execution",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="publish the LAB report.html path generated during scoring",
    )
    parser.add_argument(
        "--compare",
        choices=["task", "area", "all"],
        default=None,
        help="run LAB comparison/dashboard generation after scoring",
    )
    parser.add_argument(
        "--judge-model",
        default="claude-sonnet-4-6",
        help="judge model name",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    _reject_unsafe_relative_path(args.task, "--task")
    if args.run_id is not None:
        _reject_unsafe_relative_path(args.run_id, "--run-id")
    _reject_unsafe_relative_path(args.group_id, "--group-id")
    if args.report and not args.score:
        raise ValueError("--report requires --score")
    if args.compare and not args.score:
        raise ValueError("--compare requires --score")
    if args.adapter != "nanoclaw":
        raise ValueError(f"unsupported adapter: {args.adapter}")


def _adapter_from_args(args: argparse.Namespace) -> NanoclawAdapter:
    return NanoclawAdapter(
        nanoclaw_dir=Path(args.nanoclaw_dir),
        group_id=args.group_id,
        timeout_seconds=args.timeout,
    )


def run_single_benchmark(args: argparse.Namespace) -> dict[str, object]:
    """Run one LAB task through the selected adapter and return artifact metadata."""
    _validate_args(args)

    run_id = args.run_id or str(uuid.uuid4())
    _reject_unsafe_relative_path(run_id, "run_id")
    lab_path = (
        Path(args.lab_path).expanduser().resolve() if args.lab_path else _lab_path()
    )

    task_spec = read_task(lab_path=lab_path, task_id=args.task, run_id=run_id)
    run_dir, output_dir = build_result_dir(lab_path=lab_path, run_id=run_id)

    adapter = _adapter_from_args(args)
    result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    diagnostics = derive_benchmark_status(
        task_spec=task_spec,
        output_dir=output_dir,
        result=result,
        adapter_name=args.adapter,
    )
    diagnostics["run_dir"] = str(run_dir)
    diagnostics["output_dir"] = str(output_dir)
    metrics_path = write_metrics(
        run_dir=run_dir,
        result=result,
        extra_fields=diagnostics,
    )

    summary: dict[str, object] = {
        "run_id": run_id,
        "task_id": task_spec.task_id,
        "adapter": args.adapter,
        "run_dir": str(run_dir),
        "output_dir": str(output_dir),
        "benchmark_status": diagnostics["benchmark_status"],
        "raw_end_state": diagnostics["raw_end_state"],
        "metrics_path": str(metrics_path),
    }
    for key in (
        "terminal_status_seen",
        "completion_signal",
        "expected_deliverables_present",
        "missing_deliverables",
    ):
        if key in diagnostics:
            summary[key] = diagnostics[key]

    if args.score:
        scores_path = score_run(
            lab_path=lab_path,
            run_id=run_id,
            task_id=args.task,
            expected_deliverables=task_spec.expected_deliverables,
            judge_model=args.judge_model,
        )
        summary["scores_path"] = str(scores_path)
        if args.report:
            summary["report_path"] = str(report_path_for_run(lab_path, run_id))

    if args.compare:
        dashboard_paths = compare_run(
            lab_path=lab_path,
            mode=args.compare,
            task_id=args.task,
        )
        summary["compare_mode"] = args.compare
        summary["dashboard_paths"] = [str(path) for path in dashboard_paths]

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run_single_benchmark(args)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
