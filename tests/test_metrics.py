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
