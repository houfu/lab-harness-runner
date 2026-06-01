from __future__ import annotations

from pathlib import Path

import pytest

from lab_harness_runner.adapter import RunResult, TaskSpec
from lab_harness_runner.status import derive_benchmark_status


def _task_spec(
    tmp_path: Path,
    expected_deliverables: list[str] | None = None,
) -> TaskSpec:
    return TaskSpec(
        task_id="corporate-ma/example-task",
        instructions="Review the source documents.",
        documents_dir=tmp_path / "documents",
        expected_deliverables=expected_deliverables or ["memo.docx"],
        run_id="run-123",
    )


def _run_result(end_state: str) -> RunResult:
    return RunResult(
        run_id="run-123",
        end_state=end_state,  # type: ignore[arg-type]
        wall_clock_seconds=12.5,
    )


def test_timeout_with_valid_deliverables_is_benchmark_clean(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "memo.docx").write_text("done", encoding="utf-8")

    diagnostics = derive_benchmark_status(
        _task_spec(tmp_path),
        output_dir,
        _run_result("timeout"),
        adapter_name="nanoclaw",
    )

    assert diagnostics["benchmark_status"] == "clean"
    assert diagnostics["raw_end_state"] == "timeout"
    assert diagnostics["terminal_status_seen"] is False
    assert diagnostics["completion_signal"] == ""
    assert diagnostics["expected_deliverables_present"] is True
    assert diagnostics["missing_deliverables"] == []


def test_clean_with_valid_deliverables_records_done_signal(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "memo.docx").write_text("done", encoding="utf-8")

    diagnostics = derive_benchmark_status(
        _task_spec(tmp_path),
        output_dir,
        _run_result("clean"),
        adapter_name="nanoclaw",
    )

    assert diagnostics["benchmark_status"] == "clean"
    assert diagnostics["raw_end_state"] == "clean"
    assert diagnostics["terminal_status_seen"] is True
    assert diagnostics["completion_signal"] == "STATUS:DONE"


def test_agent_error_with_missing_deliverable_is_benchmark_error(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    diagnostics = derive_benchmark_status(
        _task_spec(tmp_path),
        output_dir,
        _run_result("agent_error"),
        adapter_name="nanoclaw",
    )

    assert diagnostics["benchmark_status"] == "error"
    assert diagnostics["raw_end_state"] == "agent_error"
    assert diagnostics["terminal_status_seen"] is True
    assert diagnostics["completion_signal"] == "STATUS:ERROR"
    assert diagnostics["expected_deliverables_present"] is False
    assert diagnostics["missing_deliverables"] == ["memo.docx"]


def test_timeout_with_missing_deliverable_preserves_timeout_status(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    diagnostics = derive_benchmark_status(
        _task_spec(tmp_path),
        output_dir,
        _run_result("timeout"),
        adapter_name="nanoclaw",
    )

    assert diagnostics["benchmark_status"] == "timeout"
    assert diagnostics["raw_end_state"] == "timeout"
    assert diagnostics["expected_deliverables_present"] is False
    assert diagnostics["missing_deliverables"] == ["memo.docx"]


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "/tmp/outside.docx",
        "../outside.docx",
        "nested/../../outside.docx",
    ],
)
def test_unsafe_expected_deliverable_names_raise_value_error(tmp_path, unsafe_name):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with pytest.raises(ValueError):
        derive_benchmark_status(
            _task_spec(tmp_path, expected_deliverables=[unsafe_name]),
            output_dir,
            _run_result("clean"),
            adapter_name="nanoclaw",
        )
