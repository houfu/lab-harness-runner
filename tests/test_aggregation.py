from __future__ import annotations

import json
from pathlib import Path

from lab_harness_runner.aggregation import (
    build_summary,
    summarize_variance,
    write_batch_summary,
)


def test_variance_empty_values_has_count_only():
    assert summarize_variance([]) == {"count": 0}


def test_variance_singleton_uses_zero_stdev():
    assert summarize_variance([1.0]) == {
        "count": 1,
        "mean": 1.0,
        "min": 1.0,
        "max": 1.0,
        "stdev": 0.0,
    }


def test_variance_multiple_values_uses_sample_stdev():
    summary = summarize_variance([1.0, 3.0])

    assert summary["count"] == 2
    assert summary["mean"] == 2.0
    assert summary["min"] == 1.0
    assert summary["max"] == 3.0
    assert summary["stdev"] > 0


def test_build_summary_includes_rows_and_variance_fields():
    rows = [
        {
            "batch_id": "batch-1",
            "task_id": "area/task",
            "seed": "1",
            "adapter": "nanoclaw",
            "run_id": "run-1",
            "run_dir": "/lab/results/run-1",
            "output_dir": "/lab/results/run-1/output",
            "metrics_path": "/lab/results/run-1/metrics.json",
            "scores_path": "/lab/results/run-1/scores.json",
            "report_path": "/lab/results/run-1/report.html",
            "benchmark_status": "clean",
            "raw_end_state": "timeout",
            "terminal_status_seen": False,
            "expected_deliverables_present": True,
            "missing_deliverables": [],
            "score": 0.5,
            "all_pass": False,
            "wall_clock_seconds": 12.0,
            "input_tokens": 100,
            "output_tokens": 50,
            "documents_read": 3,
            "total_vdr_files": 4,
        },
        {
            "batch_id": "batch-1",
            "task_id": "area/task",
            "seed": "2",
            "adapter": "nanoclaw",
            "run_id": "run-2",
            "run_dir": "/lab/results/run-2",
            "output_dir": "/lab/results/run-2/output",
            "metrics_path": "/lab/results/run-2/metrics.json",
            "scores_path": "/lab/results/run-2/scores.json",
            "report_path": "/lab/results/run-2/report.html",
            "benchmark_status": "clean",
            "raw_end_state": "clean",
            "terminal_status_seen": True,
            "expected_deliverables_present": True,
            "missing_deliverables": [],
            "score": 1.0,
            "all_pass": True,
            "wall_clock_seconds": 8.0,
            "input_tokens": 120,
            "output_tokens": 70,
            "documents_read": 4,
            "total_vdr_files": 4,
        },
    ]

    summary = build_summary(rows)

    assert summary["batch_id"] == "batch-1"
    assert summary["row_count"] == 2
    assert summary["rows"] == rows
    assert summary["variance"]["score"] == {
        "count": 2,
        "mean": 0.75,
        "min": 0.5,
        "max": 1.0,
        "stdev": 0.3535533905932738,
    }
    assert summary["variance"]["wall_clock_seconds"]["mean"] == 10.0
    assert summary["variance"]["input_tokens"]["count"] == 2
    assert summary["variance"]["output_tokens"]["count"] == 2
    assert summary["variance"]["documents_read"]["count"] == 2
    assert summary["variance"]["total_vdr_files"]["count"] == 2


def test_write_batch_summary_is_metadata_only_under_results_batches(tmp_path):
    row = {
        "batch_id": "batch-1",
        "task_id": "area/task",
        "seed": "1",
        "adapter": "nanoclaw",
        "run_id": "run-1",
        "run_dir": str(tmp_path / "results" / "run-1"),
        "output_dir": str(tmp_path / "results" / "run-1" / "output"),
        "metrics_path": str(tmp_path / "results" / "run-1" / "metrics.json"),
        "scores_path": str(tmp_path / "results" / "run-1" / "scores.json"),
        "report_path": str(tmp_path / "results" / "run-1" / "report.html"),
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

    summary_path = write_batch_summary(tmp_path, "batch-1", [row])

    assert summary_path == tmp_path / "results" / "batches" / "batch-1" / "summary.json"
    assert summary_path.exists()
    assert not (summary_path.parent / "scores.json").exists()

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["batch_id"] == "batch-1"
    assert payload["rows"] == [row]
    assert "variance" in payload
    assert all(path.name != "scores.json" for path in summary_path.parent.iterdir())
