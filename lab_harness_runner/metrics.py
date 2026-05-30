from __future__ import annotations

import json
from pathlib import Path

from lab_harness_runner.adapter import RunResult


def write_metrics(run_dir: Path, result: RunResult) -> Path:
    """Write metrics.json to run_dir. Always succeeds with safe defaults.

    Returns the path to the written metrics.json file.
    None fields use safe defaults: int fields -> 0, list fields -> [].
    """
    metrics = {
        "input_tokens": result.input_tokens or 0,
        "output_tokens": result.output_tokens or 0,
        "wall_clock_seconds": result.wall_clock_seconds,
        "documents_read": result.documents_read or 0,
        "total_vdr_files": result.total_vdr_files or 0,
        "documents_skipped": result.documents_skipped or 0,
        "documents_read_list": result.documents_read_list or [],
        "documents_skipped_list": result.documents_skipped_list or [],
        "end_state": result.end_state,
    }
    path = run_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path
