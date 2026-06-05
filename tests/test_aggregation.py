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


def _annotate_expected_rows(rows):
    """Mirror build_summary's metrics_provided annotation so the test can
    compare against the on-disk shape rather than the raw input rows."""
    expected_rows = []
    for row in rows:
        annotated = dict(row)
        # Per Plan 05-03 / D-18: metrics_provided is True when every LAB metric
        # field is non-null. The fixture rows in this test set every LAB metric
        # field, so the annotation is True for both rows.
        annotated["metrics_provided"] = True
        expected_rows.append(annotated)
    return expected_rows


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
            # Every LAB metric field set non-null so metrics_provided is True.
            "documents_skipped": 0,
            "documents_read_list": ["a.pdf"],
            "documents_skipped_list": [],
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
            # Every LAB metric field set non-null so metrics_provided is True.
            "documents_skipped": 0,
            "documents_read_list": ["a.pdf", "b.pdf"],
            "documents_skipped_list": [],
        },
    ]

    summary = build_summary(rows)

    assert summary["batch_id"] == "batch-1"
    assert summary["row_count"] == 2
    expected_rows = _annotate_expected_rows(rows)
    assert summary["rows"] == expected_rows
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
    # Per D-05: top-level unmeasured_counts is present and is the expected
    # dict of zeros (the two fixture rows set every LAB metric field, so
    # no field is null on either row).
    assert summary["unmeasured_counts"] == {
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_clock_seconds": 0,
        "documents_read": 0,
        "total_vdr_files": 0,
        "documents_skipped": 0,
        "documents_read_list": 0,
        "documents_skipped_list": 0,
    }
    # Variance key set is the original six numeric fields plus the two
    # list-field `lengths` blocks added in Plan 02 (D-11).
    assert set(summary["variance"].keys()) == {
        "score",
        "wall_clock_seconds",
        "input_tokens",
        "output_tokens",
        "documents_read",
        "total_vdr_files",
        "documents_read_list",
        "documents_skipped_list",
    }


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
        "total_vdr_files": 4,
        # Every LAB metric field is set to a non-null value so the
        # per-row `metrics_provided` boolean is True (D-04, D-18).
        "documents_skipped": 0,
        "documents_read_list": ["doc.txt"],
        "documents_skipped_list": [],
    }

    summary_path = write_batch_summary(tmp_path, "batch-1", [row])

    assert summary_path == tmp_path / "results" / "batches" / "batch-1" / "summary.json"
    assert summary_path.exists()
    assert not (summary_path.parent / "scores.json").exists()

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["batch_id"] == "batch-1"
    # Per Plan 02 / D-04, build_summary annotates each row with
    # `metrics_provided`. The row's missing_deliverables is [] and every
    # LAB metric field is set, so the annotation is True.
    expected_row = dict(row)
    expected_row["metrics_provided"] = True
    assert payload["rows"] == [expected_row]
    assert "variance" in payload
    assert all(path.name != "scores.json" for path in summary_path.parent.iterdir())


def _base_row_kwargs() -> dict[str, object]:
    """The non-metric fields shared by every fixture row in the new tests
    (mixed-measured-and-unmeasured, list-field lengths, metrics_provided
    boolean). Keeping the helper here keeps the new tests focused on the
    per-row metric nullability they exercise."""
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


def _all_measured_metric_kwargs() -> dict[str, object]:
    """The eight LAB metric fields, all set to a non-null value. Used to
    construct a "fully measured" row whose `metrics_provided` boolean is
    True."""
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


def _merge(base: dict[str, object], overrides: dict[str, object] | None = None) -> dict[str, object]:
    """Build a fixture row by overlaying ``overrides`` onto ``base``. The
    override dict is applied via ``dict.update`` so callers may list keys
    that already exist in ``base`` (e.g. setting ``input_tokens=None`` to
    exercise the null path)."""
    merged = dict(base)
    if overrides:
        merged.update(overrides)
    return merged


def test_build_summary_mixed_measured_and_unmeasured_rows():
    """Per D-18: when rows mix measured and unmeasured LAB metric fields,
    variance counts and means reflect only the measured rows, the
    unmeasured_counts dict records the per-field unmeasured tally, and
    the per-row `metrics_provided` boolean is True / False accordingly."""
    base = _base_row_kwargs()
    measured_row = _merge(
        base,
        {"run_id": "run-1", **_all_measured_metric_kwargs()},
    )
    unmeasured_row = _merge(
        base,
        {
            "run_id": "run-2",
            "wall_clock_seconds": None,
            "input_tokens": None,
            "output_tokens": None,
            "documents_read": None,
            "total_vdr_files": None,
        },
    )

    summary = build_summary([measured_row, unmeasured_row])

    # Per D-05: top-level unmeasured_counts records the per-field null tally.
    assert summary["unmeasured_counts"]["input_tokens"] == 1
    assert summary["unmeasured_counts"]["output_tokens"] == 1
    assert summary["unmeasured_counts"]["wall_clock_seconds"] == 1
    assert summary["unmeasured_counts"]["documents_read"] == 1
    assert summary["unmeasured_counts"]["total_vdr_files"] == 1
    # The list / skipped fields are present and non-null on the measured
    # row, and absent (default None) on the unmeasured row, so each is
    # unmeasured on exactly one row.
    assert summary["unmeasured_counts"]["documents_skipped"] == 1
    assert summary["unmeasured_counts"]["documents_read_list"] == 1
    assert summary["unmeasured_counts"]["documents_skipped_list"] == 1

    # Per D-10: variance count reflects the measured row only.
    assert summary["variance"]["input_tokens"]["count"] == 1
    assert summary["variance"]["input_tokens"]["mean"] == 100
    assert summary["variance"]["input_tokens"]["min"] == 100
    assert summary["variance"]["input_tokens"]["max"] == 100
    assert summary["variance"]["input_tokens"]["stdev"] == 0.0

    # Per D-04: per-row metrics_provided boolean reflects whether any LAB
    # metric field on that row is null.
    assert summary["rows"][0]["metrics_provided"] is True
    assert summary["rows"][1]["metrics_provided"] is False


def test_build_summary_unmeasured_counts_zero_for_all_measured_rows():
    """Per D-18: when every LAB metric field is set on every row, the
    unmeasured_counts dict is present and every value is 0; both rows
    have metrics_provided is True."""
    base = _base_row_kwargs()
    row_1 = _merge(base, {"run_id": "run-1", **_all_measured_metric_kwargs()})
    row_2 = _merge(base, {"run_id": "run-2", **_all_measured_metric_kwargs()})

    summary = build_summary([row_1, row_2])

    assert set(summary["unmeasured_counts"].keys()) == {
        "input_tokens",
        "output_tokens",
        "wall_clock_seconds",
        "documents_read",
        "total_vdr_files",
        "documents_skipped",
        "documents_read_list",
        "documents_skipped_list",
    }
    assert all(value == 0 for value in summary["unmeasured_counts"].values())
    assert summary["rows"][0]["metrics_provided"] is True
    assert summary["rows"][1]["metrics_provided"] is True


def test_build_summary_list_field_lengths_skip_null_rows():
    """Per D-11 / D-18: list-field `lengths` variance is computed over
    measured rows only (rows where the list field is a list, not None).
    A null row is excluded from the length statistics."""
    base = _base_row_kwargs()
    # Row 1: list fields are populated, count fields are set so they do
    # not interfere with the boolean test.
    measured_row = _merge(
        base,
        {
            "run_id": "run-1",
            **_all_measured_metric_kwargs(),
            "documents_read_list": ["a.pdf", "b.pdf", "c.pdf"],
            "documents_skipped_list": ["d.pdf"],
        },
    )
    # Row 2: list fields are None; count fields are set so metrics_provided
    # is False for a different reason (the list fields are null).
    unmeasured_row = _merge(
        base,
        {
            "run_id": "run-2",
            **_all_measured_metric_kwargs(),
            "documents_read_list": None,
            "documents_skipped_list": None,
        },
    )

    summary = build_summary([measured_row, unmeasured_row])

    # Length statistics are computed over the single measured row only.
    assert summary["variance"]["documents_read_list"]["lengths"]["count"] == 1
    assert summary["variance"]["documents_read_list"]["lengths"]["mean"] == 3.0
    assert summary["variance"]["documents_read_list"]["lengths"]["min"] == 3.0
    assert summary["variance"]["documents_read_list"]["lengths"]["max"] == 3.0
    assert summary["variance"]["documents_read_list"]["lengths"]["stdev"] == 0.0
    assert summary["variance"]["documents_skipped_list"]["lengths"]["count"] == 1
    assert summary["variance"]["documents_skipped_list"]["lengths"]["mean"] == 1.0

    # The first row is measured for the list field; the second is not
    # (None counts as unmeasured for the per-row boolean).
    assert summary["rows"][0]["metrics_provided"] is True
    assert summary["rows"][1]["metrics_provided"] is False


def test_build_summary_metrics_provided_false_when_any_field_null():
    """Per D-06 / D-18: the per-row metrics_provided boolean is False
    when any LAB metric field is None and True when all are non-null."""
    base = _base_row_kwargs()

    # Row with a single null token field — boolean must be False.
    row_with_null_input = _merge(
        base,
        {"run_id": "run-1", **_all_measured_metric_kwargs(), "input_tokens": None},
    )
    # Row with every LAB metric field set — boolean must be True.
    row_all_measured = _merge(
        base,
        {"run_id": "run-2", **_all_measured_metric_kwargs()},
    )

    summary_single_null = build_summary([row_with_null_input])
    assert summary_single_null["rows"][0]["metrics_provided"] is False

    summary_all_measured = build_summary([row_all_measured])
    assert summary_all_measured["rows"][0]["metrics_provided"] is True
