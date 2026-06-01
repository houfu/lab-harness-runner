from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Iterable

from lab_harness_runner.task_reader import _reject_unsafe_relative_path

VARIANCE_FIELDS = (
    "score",
    "wall_clock_seconds",
    "input_tokens",
    "output_tokens",
    "documents_read",
    "total_vdr_files",
)

REQUIRED_ROW_FIELDS = (
    "batch_id",
    "task_id",
    "seed",
    "adapter",
    "run_id",
    "run_dir",
    "output_dir",
    "metrics_path",
    "scores_path",
    "report_path",
    "benchmark_status",
    "raw_end_state",
    "terminal_status_seen",
    "expected_deliverables_present",
    "missing_deliverables",
    "score",
    "all_pass",
    "wall_clock_seconds",
    "input_tokens",
    "output_tokens",
    "documents_read",
    "total_vdr_files",
)


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _numeric_values(values: Iterable[object]) -> list[float]:
    numeric: list[float] = []
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            numeric.append(float(value))
    return numeric


def summarize_variance(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0}
    if len(values) == 1:
        return {
            "count": 1,
            "mean": values[0],
            "min": values[0],
            "max": values[0],
            "stdev": 0.0,
        }
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "stdev": statistics.stdev(values),
    }


def build_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    batch_id = str(rows[0]["batch_id"]) if rows else ""
    json_rows = [_jsonable(row) for row in rows]
    variance = {
        field: summarize_variance(_numeric_values(row.get(field) for row in rows))
        for field in VARIANCE_FIELDS
    }
    return {
        "batch_id": batch_id,
        "row_count": len(rows),
        "rows": json_rows,
        "variance": variance,
    }


def write_batch_summary(
    lab_path: Path,
    batch_id: str,
    rows: list[dict[str, object]],
) -> Path:
    _reject_unsafe_relative_path(batch_id, "batch_id")
    summary_dir = lab_path / "results" / "batches" / batch_id
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "summary.json"
    if summary_path.name == "scores.json":
        raise ValueError("batch summary must not be named scores.json")

    normalized_rows = []
    for row in rows:
        normalized = {field: row.get(field, "") for field in REQUIRED_ROW_FIELDS}
        normalized.update(row)
        normalized_rows.append(normalized)

    payload = build_summary(normalized_rows)
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary_path
