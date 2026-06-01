from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import lab_harness_runner
from lab_harness_runner import Adapter, RunResult, TaskSpec


class StructuralAdapter:
    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        return RunResult(
            run_id=task_spec.run_id,
            end_state="clean",
            wall_clock_seconds=0.0,
        )


def test_package_exports_phase_2_public_api() -> None:
    assert lab_harness_runner.Adapter is Adapter
    assert lab_harness_runner.TaskSpec is TaskSpec
    assert lab_harness_runner.RunResult is RunResult
    assert "Adapter" in lab_harness_runner.__all__
    assert "TaskSpec" in lab_harness_runner.__all__
    assert "RunResult" in lab_harness_runner.__all__
    assert "read_task" in lab_harness_runner.__all__
    assert "build_result_dir" in lab_harness_runner.__all__
    assert "write_metrics" in lab_harness_runner.__all__
    assert "score_run" in lab_harness_runner.__all__


def test_structural_adapter_can_run_without_inheriting_protocol(tmp_path: Path) -> None:
    task_spec = TaskSpec(
        task_id="area/task",
        instructions="Do the task.",
        documents_dir=tmp_path / "documents",
        expected_deliverables=[],
        run_id="run-001",
    )
    adapter = cast(Adapter, StructuralAdapter())

    result = adapter.run(task_spec, tmp_path / "output")

    assert isinstance(result, RunResult)
    assert result.run_id == "run-001"
    assert result.end_state == "clean"


def test_run_result_rejects_unknown_end_state() -> None:
    with pytest.raises(ValueError):
        RunResult(
            run_id="run-001",
            end_state="unknown",  # type: ignore[arg-type]
            wall_clock_seconds=0.0,
        )
