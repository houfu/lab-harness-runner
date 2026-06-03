"""Primary LAB-compatible benchmark command for nanoclaw single runs."""

from __future__ import annotations

import argparse
import copy
import json
import uuid
from pathlib import Path
from typing import Any

from lab_harness_runner import (
    build_result_dir,
    build_summary,
    compare_run,
    derive_benchmark_status,
    read_task,
    report_path_for_run,
    score_run,
    write_batch_summary,
    write_metrics,
)
from lab_harness_runner.nanoclaw_adapter import (
    EphemeralNanoclawAdapter,
    NanoclawAdapter,
)
from lab_harness_runner.task_reader import _lab_path, _reject_unsafe_relative_path


class BenchmarkArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args: list[str] | None = None, namespace: Any = None) -> Any:
        parsed = super().parse_args(args, namespace)
        if parsed.compare and not parsed.score:
            self.error("--compare requires --score")
        if parsed.report and not parsed.score:
            self.error("--report requires --score")
        if not parsed.task and not parsed.tasks:
            self.error("at least one --task or --tasks entry is required")
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = BenchmarkArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="area/slug task path; may be repeated for batch runs",
    )
    parser.add_argument(
        "--tasks",
        default=None,
        help="text file with one area/slug task path per non-empty non-comment line",
    )
    parser.add_argument(
        "--seeds",
        default=None,
        help="comma-separated seed labels recorded as metadata for batch rows",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="batch summary ID under LAB results/batches/<batch-id>/summary.json",
    )
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
        default=None,
        help=(
            "reuse a fixed nanoclaw agent group ID. Omit for ephemeral mode "
            "(default): a fresh throwaway group is created per run and destroyed "
            "afterwards, so runs cannot contaminate each other"
        ),
    )
    parser.add_argument(
        "--keep-failed",
        action="store_true",
        help=(
            "in ephemeral mode, retain the group of a failed run for debugging "
            "instead of destroying it (successful runs are always destroyed)"
        ),
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
    if isinstance(args.task, list):
        if len(args.task) != 1:
            raise ValueError("single-run benchmark requires exactly one --task")
        args.task = args.task[0]
    _reject_unsafe_relative_path(args.task, "--task")
    if args.run_id is not None:
        _reject_unsafe_relative_path(args.run_id, "--run-id")
    if args.group_id is not None:
        _reject_unsafe_relative_path(args.group_id, "--group-id")
    if args.report and not args.score:
        raise ValueError("--report requires --score")
    if args.compare and not args.score:
        raise ValueError("--compare requires --score")
    if args.adapter != "nanoclaw":
        raise ValueError(f"unsupported adapter: {args.adapter}")


def _read_tasks_file(path: str) -> list[str]:
    task_path = Path(path).expanduser()
    tasks = []
    for line in task_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        _reject_unsafe_relative_path(stripped, "--tasks entry")
        tasks.append(stripped)
    return tasks


def _expand_tasks(args: argparse.Namespace) -> list[str]:
    tasks = list(args.task if isinstance(args.task, list) else [args.task])
    if args.tasks:
        tasks.extend(_read_tasks_file(args.tasks))
    tasks = [task for task in tasks if task]
    if not tasks:
        raise ValueError("at least one --task or --tasks entry is required")
    for task in tasks:
        _reject_unsafe_relative_path(task, "--task")
    return tasks


def _expand_seeds(seed_arg: str | None) -> list[str]:
    if seed_arg is None:
        return ["default"]
    seeds = [seed.strip() for seed in seed_arg.split(",") if seed.strip()]
    if not seeds:
        raise ValueError("--seeds must contain at least one non-empty seed")
    return seeds


def _read_json_object(path: str | None) -> dict[str, object]:
    if not path:
        return {}
    json_path = Path(path)
    if not json_path.exists():
        return {}
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _score_from_scores(payload: dict[str, object]) -> float | str:
    for key in ("score", "overall_score", "mean_score"):
        value = payload.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return ""


def _all_pass_from_scores(payload: dict[str, object]) -> bool | str:
    value = payload.get("all_pass")
    if isinstance(value, bool):
        return value
    value = payload.get("passed")
    if isinstance(value, bool):
        return value
    return ""


def _batch_row(
    *,
    batch_id: str,
    seed: str,
    run_summary: dict[str, object],
) -> dict[str, object]:
    metrics = _read_json_object(run_summary.get("metrics_path"))
    scores = _read_json_object(run_summary.get("scores_path"))
    return {
        "batch_id": batch_id,
        "task_id": run_summary.get("task_id", ""),
        "seed": seed,
        "adapter": run_summary.get("adapter", ""),
        "run_id": run_summary.get("run_id", ""),
        "run_dir": run_summary.get("run_dir", ""),
        "output_dir": run_summary.get("output_dir", ""),
        "metrics_path": run_summary.get("metrics_path", ""),
        "scores_path": run_summary.get("scores_path", ""),
        "report_path": run_summary.get("report_path", ""),
        "benchmark_status": run_summary.get("benchmark_status", ""),
        "raw_end_state": run_summary.get("raw_end_state", ""),
        "terminal_status_seen": run_summary.get("terminal_status_seen", ""),
        "expected_deliverables_present": run_summary.get(
            "expected_deliverables_present", ""
        ),
        "missing_deliverables": run_summary.get("missing_deliverables", []),
        "score": run_summary.get("score", _score_from_scores(scores)),
        "all_pass": run_summary.get("all_pass", _all_pass_from_scores(scores)),
        "wall_clock_seconds": run_summary.get(
            "wall_clock_seconds", metrics.get("wall_clock_seconds", "")
        ),
        "input_tokens": run_summary.get(
            "input_tokens", metrics.get("input_tokens", "")
        ),
        "output_tokens": run_summary.get(
            "output_tokens", metrics.get("output_tokens", "")
        ),
        "documents_read": run_summary.get(
            "documents_read", metrics.get("documents_read", "")
        ),
        "total_vdr_files": run_summary.get(
            "total_vdr_files", metrics.get("total_vdr_files", "")
        ),
    }


def run_batch_benchmark(args: argparse.Namespace) -> dict[str, object]:
    lab_path = (
        Path(args.lab_path).expanduser().resolve() if args.lab_path else _lab_path()
    )
    tasks = _expand_tasks(args)
    seeds = _expand_seeds(args.seeds)
    run_count = len(tasks) * len(seeds)
    if args.run_id and run_count > 1:
        raise ValueError("fixed --run-id is only allowed for one batch run")

    batch_id = args.batch_id or str(uuid.uuid4())
    _reject_unsafe_relative_path(batch_id, "--batch-id")
    rows: list[dict[str, object]] = []
    for task in tasks:
        for seed in seeds:
            run_args = copy.copy(args)
            run_args.task = task
            run_args.seed = seed
            run_args.run_id = args.run_id or str(uuid.uuid4())
            summary = run_single_benchmark(run_args)
            rows.append(_batch_row(batch_id=batch_id, seed=seed, run_summary=summary))

    summary_path = write_batch_summary(lab_path=lab_path, batch_id=batch_id, rows=rows)
    payload = build_summary(rows)
    payload["summary_path"] = str(summary_path)
    return payload


def _should_run_batch(args: argparse.Namespace) -> bool:
    task_count = len(args.task if isinstance(args.task, list) else [args.task])
    return bool(args.tasks or args.seeds or args.batch_id or task_count > 1)


def _adapter_from_args(
    args: argparse.Namespace,
) -> NanoclawAdapter | EphemeralNanoclawAdapter:
    """Build the adapter: ephemeral per-run group by default, fixed if --group-id."""
    if args.group_id is not None:
        return NanoclawAdapter(
            nanoclaw_dir=Path(args.nanoclaw_dir),
            group_id=args.group_id,
            timeout_seconds=args.timeout,
        )
    return EphemeralNanoclawAdapter(
        nanoclaw_dir=Path(args.nanoclaw_dir),
        timeout_seconds=args.timeout,
        keep_failed=args.keep_failed,
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
        if _should_run_batch(args):
            summary = run_batch_benchmark(args)
        else:
            if isinstance(args.task, list) and len(args.task) == 1:
                args.task = args.task[0]
            summary = run_single_benchmark(args)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
