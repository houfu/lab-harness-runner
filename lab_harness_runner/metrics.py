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
    """Write metrics.json to run_dir. Always succeeds with safe defaults.

    Returns the path to the written metrics.json file.
    None fields use safe defaults: int fields -> 0, list fields -> [].
    """
    metrics = {
        "input_tokens": (result.input_tokens if result.input_tokens is not None else 0),
        "output_tokens": (
            result.output_tokens if result.output_tokens is not None else 0
        ),
        "wall_clock_seconds": result.wall_clock_seconds,
        "documents_read": (
            result.documents_read if result.documents_read is not None else 0
        ),
        "total_vdr_files": (
            result.total_vdr_files if result.total_vdr_files is not None else 0
        ),
        "documents_skipped": (
            result.documents_skipped if result.documents_skipped is not None else 0
        ),
        "documents_read_list": (
            result.documents_read_list if result.documents_read_list is not None else []
        ),
        "documents_skipped_list": (
            result.documents_skipped_list
            if result.documents_skipped_list is not None
            else []
        ),
        "end_state": result.end_state,
    }
    if extra_fields:
        metrics.update(_without_null_values(extra_fields))

    path = run_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path
