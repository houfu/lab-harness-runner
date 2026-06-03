from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lab_harness_runner.adapter import RunResult, TaskSpec


def _task_spec(run_id: str = "run-123") -> TaskSpec:
    return TaskSpec(
        task_id="area/task",
        instructions="Do the task.",
        documents_dir=Path("/tmp/docs"),
        expected_deliverables=["answer.docx"],
        run_id=run_id,
    )


def _args(
    *,
    lab_path: Path,
    run_id: str = "run-123",
    task: str = "area/task",
    score: bool = False,
    report: bool = False,
    compare: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        task=task,
        tasks=None,
        seeds=None,
        batch_id=None,
        adapter="nanoclaw",
        run_id=run_id,
        lab_path=str(lab_path),
        nanoclaw_dir=str(lab_path / "nanoclaw"),
        group_id="lab-runner",
        timeout=12.5,
        score=score,
        report=report,
        compare=compare,
        judge_model="judge-model",
    )


def test_single_run_orchestrates_adapter_status_and_metrics(tmp_path, monkeypatch):
    import scripts.run_benchmark as run_benchmark

    task_spec = _task_spec()
    run_dir = tmp_path / "results" / "run-123"
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True)
    result = RunResult(run_id="run-123", end_state="clean", wall_clock_seconds=1.25)
    adapter = MagicMock()
    adapter.run.return_value = result

    read_task = MagicMock(return_value=task_spec)
    build_result_dir = MagicMock(return_value=(run_dir, output_dir))
    derive_status = MagicMock(
        return_value={
            "benchmark_status": "clean",
            "raw_end_state": "clean",
            "terminal_status_seen": True,
            "expected_deliverables_present": True,
            "missing_deliverables": [],
            "output_dir": str(output_dir),
        }
    )
    write_metrics = MagicMock(return_value=run_dir / "metrics.json")

    monkeypatch.setattr(run_benchmark, "read_task", read_task)
    monkeypatch.setattr(run_benchmark, "build_result_dir", build_result_dir)
    monkeypatch.setattr(
        run_benchmark, "NanoclawAdapter", MagicMock(return_value=adapter)
    )
    monkeypatch.setattr(run_benchmark, "derive_benchmark_status", derive_status)
    monkeypatch.setattr(run_benchmark, "write_metrics", write_metrics)

    summary = run_benchmark.run_single_benchmark(_args(lab_path=tmp_path))

    read_task.assert_called_once_with(
        lab_path=tmp_path, task_id="area/task", run_id="run-123"
    )
    build_result_dir.assert_called_once_with(lab_path=tmp_path, run_id="run-123")
    adapter.run.assert_called_once_with(task_spec=task_spec, output_dir=output_dir)
    derive_status.assert_called_once_with(
        task_spec=task_spec,
        output_dir=output_dir,
        result=result,
        adapter_name="nanoclaw",
    )
    write_metrics.assert_called_once()
    assert write_metrics.call_args.kwargs["extra_fields"]["run_dir"] == str(run_dir)
    assert summary["run_id"] == "run-123"
    assert summary["run_dir"] == str(run_dir)
    assert summary["output_dir"] == str(output_dir)
    assert summary["benchmark_status"] == "clean"
    assert summary["raw_end_state"] == "clean"
    assert summary["metrics_path"] == str(run_dir / "metrics.json")
    assert "scores_path" not in summary


def test_score_and_report_preserve_lab_run_paths(tmp_path, monkeypatch):
    import scripts.run_benchmark as run_benchmark

    run_dir = tmp_path / "results" / "run-123"
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True)
    adapter = MagicMock()
    adapter.run.return_value = RunResult(
        run_id="run-123", end_state="clean", wall_clock_seconds=1.0
    )

    monkeypatch.setattr(
        run_benchmark, "read_task", MagicMock(return_value=_task_spec())
    )
    monkeypatch.setattr(
        run_benchmark, "build_result_dir", MagicMock(return_value=(run_dir, output_dir))
    )
    monkeypatch.setattr(
        run_benchmark, "NanoclawAdapter", MagicMock(return_value=adapter)
    )
    monkeypatch.setattr(
        run_benchmark,
        "derive_benchmark_status",
        MagicMock(return_value={"benchmark_status": "clean", "raw_end_state": "clean"}),
    )
    monkeypatch.setattr(
        run_benchmark, "write_metrics", MagicMock(return_value=run_dir / "metrics.json")
    )
    score_run = MagicMock(return_value=run_dir / "scores.json")
    monkeypatch.setattr(run_benchmark, "score_run", score_run)

    summary = run_benchmark.run_single_benchmark(
        _args(lab_path=tmp_path, score=True, report=True)
    )

    score_run.assert_called_once_with(
        lab_path=tmp_path,
        run_id="run-123",
        task_id="area/task",
        expected_deliverables=["answer.docx"],
        judge_model="judge-model",
    )
    assert summary["scores_path"] == str(run_dir / "scores.json")
    assert summary["report_path"] == str(run_dir / "report.html")
    assert summary["run_dir"] == str(run_dir)
    assert summary["output_dir"] == str(output_dir)


@pytest.mark.parametrize("mode", ["task", "area", "all"])
def test_score_and_compare_records_dashboard_paths(tmp_path, monkeypatch, mode):
    import scripts.run_benchmark as run_benchmark

    run_dir = tmp_path / "results" / "run-123"
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True)
    adapter = MagicMock()
    adapter.run.return_value = RunResult(
        run_id="run-123", end_state="clean", wall_clock_seconds=1.0
    )
    dashboard_paths = [
        tmp_path / "results" / "comparisons" / "area" / "task" / "comparison.html"
    ]

    monkeypatch.setattr(
        run_benchmark, "read_task", MagicMock(return_value=_task_spec())
    )
    monkeypatch.setattr(
        run_benchmark, "build_result_dir", MagicMock(return_value=(run_dir, output_dir))
    )
    monkeypatch.setattr(
        run_benchmark, "NanoclawAdapter", MagicMock(return_value=adapter)
    )
    monkeypatch.setattr(
        run_benchmark,
        "derive_benchmark_status",
        MagicMock(return_value={"benchmark_status": "clean", "raw_end_state": "clean"}),
    )
    monkeypatch.setattr(
        run_benchmark, "write_metrics", MagicMock(return_value=run_dir / "metrics.json")
    )
    monkeypatch.setattr(
        run_benchmark, "score_run", MagicMock(return_value=run_dir / "scores.json")
    )
    compare = MagicMock(return_value=dashboard_paths)
    monkeypatch.setattr(run_benchmark, "compare_run", compare)

    summary = run_benchmark.run_single_benchmark(
        _args(lab_path=tmp_path, score=True, compare=mode)
    )

    compare.assert_called_once_with(
        lab_path=tmp_path,
        mode=mode,
        task_id="area/task",
    )
    assert summary["compare_mode"] == mode
    assert summary["dashboard_paths"] == [str(path) for path in dashboard_paths]
    assert summary["run_dir"] == str(run_dir)
    assert summary["output_dir"] == str(output_dir)
    assert summary["scores_path"] == str(run_dir / "scores.json")


def test_compare_without_score_rejected_before_adapter_invocation(
    tmp_path, monkeypatch
):
    import scripts.run_benchmark as run_benchmark

    adapter_factory = MagicMock()
    monkeypatch.setattr(run_benchmark, "NanoclawAdapter", adapter_factory)

    with pytest.raises(ValueError, match="--compare requires --score"):
        run_benchmark.run_single_benchmark(
            _args(lab_path=tmp_path, score=False, compare="task")
        )

    adapter_factory.assert_not_called()


def test_report_without_score_rejected_before_adapter_invocation(tmp_path, monkeypatch):
    import scripts.run_benchmark as run_benchmark

    adapter_factory = MagicMock()
    monkeypatch.setattr(run_benchmark, "NanoclawAdapter", adapter_factory)

    with pytest.raises(ValueError, match="--report requires --score"):
        run_benchmark.run_single_benchmark(
            _args(lab_path=tmp_path, score=False, report=True)
        )

    adapter_factory.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task", "../area/task"),
        ("run_id", "../run"),
        ("group_id", "../group"),
    ],
)
def test_unsafe_cli_inputs_fail_before_adapter_invocation(
    tmp_path, monkeypatch, field, value
):
    import scripts.run_benchmark as run_benchmark

    args = _args(lab_path=tmp_path)
    setattr(args, field, value)
    adapter_factory = MagicMock()
    monkeypatch.setattr(run_benchmark, "NanoclawAdapter", adapter_factory)

    with pytest.raises(ValueError):
        run_benchmark.run_single_benchmark(args)

    adapter_factory.assert_not_called()


def test_parser_rejects_compare_without_score():
    import scripts.run_benchmark as run_benchmark

    parser = run_benchmark.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--task",
                "area/task",
                "--adapter",
                "nanoclaw",
                "--nanoclaw-dir",
                "/tmp/nanoclaw",
                "--group-id",
                "lab-runner",
                "--compare",
                "task",
            ]
        )


def test_parser_accepts_repeated_task_tasks_file_seeds_and_batch_id(tmp_path):
    import scripts.run_benchmark as run_benchmark

    tasks_file = tmp_path / "tasks.txt"
    tasks_file.write_text("area/task-c\n", encoding="utf-8")
    parser = run_benchmark.build_parser()

    args = parser.parse_args(
        [
            "--task",
            "area/task-a",
            "--task",
            "area/task-b",
            "--tasks",
            str(tasks_file),
            "--seeds",
            "1,2",
            "--batch-id",
            "batch-123",
            "--adapter",
            "nanoclaw",
            "--nanoclaw-dir",
            "/tmp/nanoclaw",
            "--group-id",
            "lab-runner",
        ]
    )

    assert args.task == ["area/task-a", "area/task-b"]
    assert args.tasks == str(tasks_file)
    assert args.seeds == "1,2"
    assert args.batch_id == "batch-123"


def test_batch_execution_runs_each_task_seed_and_writes_metadata_summary(
    tmp_path, monkeypatch
):
    import scripts.run_benchmark as run_benchmark

    calls = []

    def fake_single(args):
        calls.append((args.task, args.seed, args.run_id))
        run_dir = tmp_path / "results" / args.run_id
        return {
            "run_id": args.run_id,
            "task_id": args.task,
            "adapter": args.adapter,
            "run_dir": str(run_dir),
            "output_dir": str(run_dir / "output"),
            "metrics_path": str(run_dir / "metrics.json"),
            "scores_path": str(run_dir / "scores.json"),
            "report_path": str(run_dir / "report.html"),
            "benchmark_status": "clean",
            "raw_end_state": "clean",
            "terminal_status_seen": True,
            "expected_deliverables_present": True,
            "missing_deliverables": [],
            "score": 1.0,
            "all_pass": True,
            "wall_clock_seconds": 1.0,
            "input_tokens": 10,
            "output_tokens": 20,
            "documents_read": 1,
            "total_vdr_files": 2,
        }

    monkeypatch.setattr(run_benchmark, "run_single_benchmark", fake_single)
    args = _args(lab_path=tmp_path, run_id=None)
    args.task = ["area/task-a", "area/task-b"]
    args.seeds = "1,2"
    args.batch_id = "batch-123"

    summary = run_benchmark.run_batch_benchmark(args)

    assert [(task, seed) for task, seed, _ in calls] == [
        ("area/task-a", "1"),
        ("area/task-a", "2"),
        ("area/task-b", "1"),
        ("area/task-b", "2"),
    ]
    assert len({run_id for _, _, run_id in calls}) == 4
    assert summary["batch_id"] == "batch-123"
    assert summary["summary_path"] == str(
        tmp_path / "results" / "batches" / "batch-123" / "summary.json"
    )
    assert all(row["seed"] in {"1", "2"} for row in summary["rows"])
    assert all(row["batch_id"] == "batch-123" for row in summary["rows"])
    assert not (tmp_path / "results" / "batches" / "batch-123" / "scores.json").exists()


def test_batch_execution_rejects_fixed_run_id_for_multiple_runs(tmp_path):
    import scripts.run_benchmark as run_benchmark

    args = _args(lab_path=tmp_path, run_id="fixed-run")
    args.task = ["area/task-a", "area/task-b"]
    args.seeds = "1"
    args.batch_id = "batch-123"

    with pytest.raises(ValueError, match="fixed --run-id"):
        run_benchmark.run_batch_benchmark(args)


def test_nanoclaw_compatibility_wrapper_dispatches_batch(monkeypatch, capsys, tmp_path):
    import scripts.nanoclaw_run as nanoclaw_run

    args = _args(lab_path=tmp_path, run_id=None)
    args.task = ["area/task-a", "area/task-b"]
    args.batch_id = "batch-123"
    parser = MagicMock()
    parser.parse_args.return_value = args
    batch = MagicMock(
        return_value={
            "batch_id": "batch-123",
            "row_count": 2,
            "summary_path": str(
                tmp_path / "results" / "batches" / "batch-123" / "summary.json"
            ),
        }
    )
    single = MagicMock()

    monkeypatch.setattr(nanoclaw_run, "build_parser", MagicMock(return_value=parser))
    monkeypatch.setattr(nanoclaw_run, "run_batch_benchmark", batch)
    monkeypatch.setattr(nanoclaw_run, "run_single_benchmark", single)

    assert nanoclaw_run.main() == 0

    batch.assert_called_once_with(args)
    single.assert_not_called()
    output = capsys.readouterr().out
    assert "batch_id: batch-123" in output
    assert "summary_path:" in output


def test_adapter_from_args_fixed_group_returns_nanoclaw(tmp_path):
    import scripts.run_benchmark as run_benchmark
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    args = _args(lab_path=tmp_path)
    args.group_id = "lab-runner"
    args.keep_failed = False
    adapter = run_benchmark._adapter_from_args(args)
    assert isinstance(adapter, NanoclawAdapter)
    assert adapter.group_id == "lab-runner"


def test_adapter_from_args_no_group_returns_ephemeral(tmp_path):
    import scripts.run_benchmark as run_benchmark
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    args = _args(lab_path=tmp_path)
    args.group_id = None
    args.keep_failed = True
    adapter = run_benchmark._adapter_from_args(args)
    assert isinstance(adapter, EphemeralNanoclawAdapter)
    assert adapter.keep_failed is True
    assert adapter.timeout_seconds == args.timeout
