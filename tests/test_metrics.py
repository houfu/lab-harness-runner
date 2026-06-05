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


def test_write_metrics_unmeasured_fields_written_as_null(tmp_path):
    """Unmeasured fields (None) are serialised as JSON null on disk so
    downstream consumers can distinguish "not measured" from "measured zero".
    """
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
        documents_read_list=None,
        documents_skipped_list=None,
    )
    path = write_metrics(tmp_path, result)
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    # Python None round-trips from JSON null
    assert data["input_tokens"] is None
    assert data["output_tokens"] is None
    assert data["documents_read"] is None
    assert data["total_vdr_files"] is None
    assert data["documents_skipped"] is None
    assert data["documents_read_list"] is None
    assert data["documents_skipped_list"] is None

    # The raw on-disk text contains JSON null for each unmeasured field
    assert '"input_tokens": null' in raw_text
    assert '"output_tokens": null' in raw_text
    assert '"documents_read": null' in raw_text
    assert '"total_vdr_files": null' in raw_text
    assert '"documents_skipped": null' in raw_text
    assert '"documents_read_list": null' in raw_text
    assert '"documents_skipped_list": null' in raw_text


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


def test_write_metrics_unmeasured_list_field_written_as_null(tmp_path):
    """documents_read_list=None and documents_skipped_list=None write as null,
    not as the measured-empty []. This is the D-08 contract.
    """
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-list-null",
        end_state="clean",
        wall_clock_seconds=1.0,
        documents_read_list=None,
        documents_skipped_list=None,
    )
    path = write_metrics(tmp_path, result)
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    assert data["documents_read_list"] is None
    assert data["documents_skipped_list"] is None
    assert '"documents_read_list": null' in raw_text
    assert '"documents_skipped_list": null' in raw_text


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


def test_write_metrics_explicit_zero_preserved(tmp_path):
    """Explicit zero values (int fields and empty list fields) are preserved
    on disk; only None is written as null. This is the D-01 explicit-zero
    preservation contract.
    """
    from lab_harness_runner.metrics import write_metrics

    result = RunResult(
        run_id="test-run-explicit-zero",
        end_state="clean",
        wall_clock_seconds=0.0,
        input_tokens=0,
        output_tokens=0,
        documents_read=0,
        total_vdr_files=0,
        documents_skipped=0,
        documents_read_list=[],
        documents_skipped_list=[],
    )
    path = write_metrics(tmp_path, result)
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    assert data["wall_clock_seconds"] == 0.0
    assert data["input_tokens"] == 0
    assert data["output_tokens"] == 0
    assert data["documents_read"] == 0
    assert data["total_vdr_files"] == 0
    assert data["documents_skipped"] == 0
    assert data["documents_read_list"] == []
    assert data["documents_skipped_list"] == []

    # Raw text preserves the explicit values (0 / []) rather than null
    assert '"input_tokens": 0' in raw_text
    assert '"documents_read_list": []' in raw_text
    assert '"documents_skipped_list": []' in raw_text


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
    """Diagnostic fields are merged after LAB keys. A None diagnostic value
    is stripped by _without_null_values; the LAB-metric null contract is
    a separate, expected behaviour covered by
    test_write_metrics_unmeasured_fields_written_as_null — this test's
    scope is diagnostics filtering only.
    """
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
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["end_state"] == "timeout"
    assert data["benchmark_status"] == "clean"
    assert data["raw_end_state"] == "timeout"
    assert data["terminal_status_seen"] is False
    assert data["completion_signal"] == ""
    assert data["expected_deliverables_present"] is True
    assert data["missing_deliverables"] == []
    assert data["run_dir"] == str(tmp_path)
    assert data["output_dir"] == str(tmp_path / "output")
    # The omit_me=None diagnostic is still stripped by _without_null_values
    # even though the LAB-metric fields may carry JSON null on disk.
    assert "omit_me" not in data


# ---------------------------------------------------------------------------
# Phase 6 D-17: metrics_provided boolean end-to-end for the measured
# (Anthropic) and unmeasured (no-op) paths.
# ---------------------------------------------------------------------------


def _all_measured_metric_kwargs() -> dict[str, object]:
    """The eight LAB metric fields, all set to a non-null value. Used to
    construct a "fully measured" row whose `metrics_provided` boolean is
    True. Mirrors the helper in tests/test_aggregation.py so the D-17
    round-trip test does not depend on the aggregation test module's
    internal helpers (which may evolve)."""
    return {
        "wall_clock_seconds": 12.0,
        "input_tokens": 100,
        "output_tokens": 50,
        "documents_read": 3,
        "total_vdr_files": 4,
        "documents_skipped": 0,
        "documents_read_list": ["a.pdf"],
        "documents_skipped_list": [],
    }


def _base_row_kwargs() -> dict[str, object]:
    """The non-metric fields required by ``build_summary``'s row schema.

    The harness calls ``build_summary`` with batch / task / run / score
    metadata alongside the LAB metric fields. Mirrors the helper in
    tests/test_aggregation.py."""
    return {
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
        "raw_end_state": "clean",
        "terminal_status_seen": True,
        "expected_deliverables_present": True,
        "missing_deliverables": [],
        "score": 1.0,
        "all_pass": True,
    }


def test_metrics_provided_true_for_measured_run(tmp_path: Path) -> None:
    """Phase 6 D-17: a measured Anthropic run -> metrics_provided: True.

    Round-trips a fully-populated RunResult (the kind an
    AnthropicTranscriptExtractor would produce) through ``write_metrics``,
    builds a batch row from the on-disk JSON, and asserts
    ``build_summary`` annotates the row with ``metrics_provided: True``.
    This is the consumer-facing signal that the run was measured.
    """
    from lab_harness_runner.aggregation import (
        LAB_METRIC_FIELDS,
        build_summary,
    )
    from lab_harness_runner.metrics import write_metrics

    # The kind of RunResult the AnthropicTranscriptExtractor would return
    # for a successful run (D-09: usage + docs fields both populated).
    result = RunResult(
        run_id="run-measured-1",
        end_state="clean",
        wall_clock_seconds=42.0,
        input_tokens=300,
        output_tokens=130,
        documents_read=1,
        total_vdr_files=4,
        documents_skipped=3,
        documents_read_list=["/tmp/foo.txt"],
        documents_skipped_list=[],
    )

    metrics_path = write_metrics(tmp_path, result)
    on_disk = json.loads(metrics_path.read_text(encoding="utf-8"))

    # Build the batch row by overlaying the on-disk metric fields onto
    # the base row. LAB_METRIC_FIELDS is the canonical eight-field set
    # that build_summary's per-row metrics_provided check uses.
    row = dict(_base_row_kwargs())
    for field in LAB_METRIC_FIELDS:
        row[field] = on_disk[field]

    summary = build_summary([row])

    # D-17: per-row metrics_provided boolean is True when every LAB
    # metric field is non-null (the measured case).
    assert summary["rows"][0]["metrics_provided"] is True
    # The four null-counted fields on the measured row are all zero.
    assert summary["unmeasured_counts"] == {f: 0 for f in LAB_METRIC_FIELDS}


def test_metrics_provided_false_for_no_op_run(tmp_path: Path) -> None:
    """Phase 6 D-17: an unmeasured no-op run -> metrics_provided: False.

    Round-trips a no-op-extractor-shaped RunResult (all token / coverage
    fields None) through ``write_metrics``, builds a batch row, and
    asserts ``build_summary`` annotates the row with
    ``metrics_provided: False``. This is the consumer-facing signal that
    the run was NOT measured (Ollama / unknown model path per D-10).
    """
    from lab_harness_runner.aggregation import (
        LAB_METRIC_FIELDS,
        build_summary,
    )
    from lab_harness_runner.metrics import write_metrics

    # The kind of RunResult a NoOpExtractor would return — every
    # token / coverage field None, end_state="clean".
    result = RunResult(
        run_id="run-unmeasured-1",
        end_state="clean",
        wall_clock_seconds=15.0,
    )

    metrics_path = write_metrics(tmp_path, result)
    on_disk = json.loads(metrics_path.read_text(encoding="utf-8"))

    row = dict(_base_row_kwargs())
    for field in LAB_METRIC_FIELDS:
        row[field] = on_disk[field]

    summary = build_summary([row])

    # D-17: per-row metrics_provided boolean is False when any LAB
    # metric field is None (the unmeasured / no-op case).
    assert summary["rows"][0]["metrics_provided"] is False
    # The four LAB metric fields that carry token / coverage data are
    # all unmeasured on the no-op row. (wall_clock_seconds is also None
    # on the no-op row because NoOpExtractor's RunResult has it at 0.0
    # while the RunResult dataclass default is 0.0 from write_metrics
    # — see the call: the input RunResult does carry wall_clock_seconds,
    # so it is NOT counted as unmeasured here.)
    # The unmeasured counts for the four fields populated by the
    # extractor (input_tokens, output_tokens, documents_read, etc.)
    # must all be 1.
    assert summary["unmeasured_counts"]["input_tokens"] == 1
    assert summary["unmeasured_counts"]["output_tokens"] == 1
    assert summary["unmeasured_counts"]["documents_read"] == 1
    assert summary["unmeasured_counts"]["total_vdr_files"] == 1
    assert summary["unmeasured_counts"]["documents_skipped"] == 1
    assert summary["unmeasured_counts"]["documents_read_list"] == 1
    assert summary["unmeasured_counts"]["documents_skipped_list"] == 1
