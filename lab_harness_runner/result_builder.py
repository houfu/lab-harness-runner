from __future__ import annotations

from pathlib import Path


def build_result_dir(lab_path: Path, run_id: str) -> tuple[Path, Path]:
    """Create the run directory and output subdirectory.

    Args:
        lab_path: Root directory of the Harvey LAB installation.
        run_id: Unique identifier for this run. May be a plain string
            (e.g., "abc123") or a slash-separated path; Python's Path
            operator handles nested directories automatically.

    Returns:
        (run_dir, output_dir) where:
            run_dir = lab_path / "results" / run_id
            output_dir = run_dir / "output"

    The output_dir is created on disk (parents=True, exist_ok=True).
    """
    run_dir = lab_path / "results" / run_id
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, output_dir
