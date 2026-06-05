from __future__ import annotations

import json
from pathlib import Path

from lab_harness_runner.adapter import RunResult


def _without_null_values(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_null_values(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_without_null_values(item) for item in value if item is not None]
    if isinstance(value, Path):
        return str(value)
    return value


def write_metrics(
    run_dir: Path,
    result: RunResult,
    extra_fields: dict[str, object] | None = None,
) -> Path:
    """Write metrics.json to run_dir.

    Returns the path to the written metrics.json file.
    None metric fields are written as JSON null so downstream consumers
    can distinguish "adapter did not measure" from a measured 0 / [].
    Diagnostics passed via extra_fields still strip None values.
    """
    metrics = {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "wall_clock_seconds": result.wall_clock_seconds,
        "documents_read": result.documents_read,
        "total_vdr_files": result.total_vdr_files,
        "documents_skipped": result.documents_skipped,
        "documents_read_list": result.documents_read_list,
        "documents_skipped_list": result.documents_skipped_list,
        "end_state": result.end_state,
    }
    if extra_fields:
        metrics.update(_without_null_values(extra_fields))

    path = run_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path
