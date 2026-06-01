from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab_harness_runner.adapter import RunResult


def test_write_metrics_fully_populated(tmp_path):
    """write_metrics with a fully-populated RunResult writes all fields to metrics.json."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-1",
        end_state="clean",
        wall_clock_seconds=42.5,
        input_tokens=100,
        output_tokens=200,
        documents_read=5,
        total_vdr_files=10,
        documents_skipped=5,
        documents_read_list=["doc1.pdf", "doc2.pdf"],
        documents_skipped_list=["doc3.pdf"],
    )
    path = write_metrics(tmp_path, result)

    assert path == tmp_path / "metrics.json"
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 200
    assert data["wall_clock_seconds"] == 42.5
    assert data["documents_read"] == 5
    assert data["total_vdr_files"] == 10
    assert data["documents_skipped"] == 5
    assert data["documents_read_list"] == ["doc1.pdf", "doc2.pdf"]
    assert data["documents_skipped_list"] == ["doc3.pdf"]
    assert data["end_state"] == "clean"


def test_write_metrics_returns_path(tmp_path):
    """write_metrics returns the Path of the written file."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-2",
        end_state="clean",
        wall_clock_seconds=1.0,
    )
    path = write_metrics(tmp_path, result)
    assert isinstance(path, Path)
    assert path == tmp_path / "metrics.json"


def test_write_metrics_none_int_fields_default_to_zero(tmp_path):
    """write_metrics with RunResult where input_tokens=None writes 'input_tokens': 0."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-3",
        end_state="agent_error",
        wall_clock_seconds=5.0,
        input_tokens=None,
        output_tokens=None,
        documents_read=None,
        total_vdr_files=None,
        documents_skipped=None,
    )
    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["input_tokens"] == 0
    assert data["output_tokens"] == 0
    assert data["documents_read"] == 0
    assert data["total_vdr_files"] == 0
    assert data["documents_skipped"] == 0


def test_write_metrics_preserves_explicit_zero_values(tmp_path):
    """Explicit zero metrics are written as zero, not null or omitted."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-zero",
        end_state="clean",
        wall_clock_seconds=0.0,
        input_tokens=0,
        output_tokens=0,
        documents_read=0,
        total_vdr_files=0,
        documents_skipped=0,
    )

    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["wall_clock_seconds"] == 0.0
    assert data["input_tokens"] == 0
    assert data["output_tokens"] == 0
    assert data["documents_read"] == 0
    assert data["total_vdr_files"] == 0
    assert data["documents_skipped"] == 0


def test_write_metrics_empty_list_fields(tmp_path):
    """write_metrics with RunResult where documents_read_list is [] writes empty list."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-4",
        end_state="clean",
        wall_clock_seconds=3.0,
        documents_read_list=[],
        documents_skipped_list=[],
    )
    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["documents_read_list"] == []
    assert data["documents_skipped_list"] == []


def test_write_metrics_no_null_values(tmp_path):
    """Written JSON does NOT contain null values — all None fields become 0 or []."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-5",
        end_state="timeout",
        wall_clock_seconds=120.0,
    )
    path = write_metrics(tmp_path, result)
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    # Check no null values in the JSON
    assert "null" not in raw_text
    for value in data.values():
        assert value is not None


def test_write_metrics_contains_end_state(tmp_path):
    """Written JSON contains end_state from result.end_state."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-6",
        end_state="timeout",
        wall_clock_seconds=300.0,
    )
    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["end_state"] == "timeout"


def test_write_metrics_safe_defaults(tmp_path):
    """write_metrics with input_tokens=None writes input_tokens: 0 (not null)."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-safe",
        end_state="clean",
        wall_clock_seconds=1.0,
        input_tokens=None,
        output_tokens=None,
    )
    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["input_tokens"] == 0
    assert data["output_tokens"] == 0


def test_write_metrics_with_sample_run_result(tmp_path, sample_run_result):
    """write_metrics with sample_run_result fixture preserves all values."""
    from lab_harness_runner.metrics import write_metrics

    path = write_metrics(tmp_path, sample_run_result)
    assert path == tmp_path / "metrics.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50
    assert data["end_state"] == "clean"


def test_write_metrics_no_task_title(tmp_path):
    """Written JSON does NOT contain task_title key."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-7",
        end_state="clean",
        wall_clock_seconds=1.0,
    )
    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert "task_title" not in data


def test_write_metrics_accepts_old_two_argument_call(tmp_path):
    """write_metrics remains backwards-compatible without diagnostic fields."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-8",
        end_state="clean",
        wall_clock_seconds=1.0,
    )
    path = write_metrics(tmp_path, result)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["end_state"] == "clean"
    assert "benchmark_status" not in data


def test_write_metrics_writes_diagnostic_fields_without_null_values(tmp_path):
    """Diagnostic fields are merged after LAB keys and do not write JSON null."""
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-9",
        end_state="timeout",
        wall_clock_seconds=30.0,
    )
    diagnostics = {
        "task_id": "corporate-ma/example-task",
        "run_id": "test-run-9",
        "adapter": "nanoclaw",
        "raw_end_state": "timeout",
        "benchmark_status": "clean",
        "terminal_status_seen": False,
        "completion_signal": "",
        "expected_deliverables_present": True,
        "missing_deliverables": [],
        "run_dir": tmp_path,
        "output_dir": str(tmp_path / "output"),
        "omit_me": None,
    }

    path = write_metrics(tmp_path, result, extra_fields=diagnostics)
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    assert "null" not in raw_text
    assert data["end_state"] == "timeout"
    assert data["benchmark_status"] == "clean"
    assert data["raw_end_state"] == "timeout"
    assert data["terminal_status_seen"] is False
    assert data["completion_signal"] == ""
    assert data["expected_deliverables_present"] is True
    assert data["missing_deliverables"] == []
    assert data["run_dir"] == str(tmp_path)
    assert data["output_dir"] == str(tmp_path / "output")
    assert "omit_me" not in data
