from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

from lab_harness_runner.task_reader import _reject_unsafe_relative_path


def score_run(
    lab_path: Path,
    run_id: str,
    task_id: str,
    expected_deliverables: list[str],
    judge_model: str = "claude-sonnet-4-6",
) -> Path:
    """Validate deliverables then invoke the LAB evaluator.

    Returns path to scores.json.
    Raises FileNotFoundError if any expected deliverable is missing from
    lab_path/results/run_id/output/.
    Raises subprocess.CalledProcessError if run_eval exits non-zero.
    Raises ValueError if run_id or task_id is absolute or contains traversal.
    """
    _reject_unsafe_relative_path(run_id, "run_id")
    _reject_unsafe_relative_path(task_id, "task_id")

    output_dir = lab_path / "results" / run_id / "output"

    # D-11: pre-score validation — check output_dir, not run_dir (Pitfall 4)
    missing = []
    for name in expected_deliverables:
        deliverable_path = _reject_unsafe_relative_path(
            name, "expected_deliverable"
        )
        if not (output_dir / deliverable_path).exists():
            missing.append(name)
    if missing:
        raise FileNotFoundError(
            f"Missing deliverables in {output_dir}: {', '.join(missing)}"
        )

    # D-10: subprocess invocation — list form, cwd=lab_path, check=True
    try:
        subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "evaluation.run_eval",
                "--run-id",
                run_id,
                "--task",
                task_id,
                "--judge-model",
                judge_model,
            ],
            cwd=lab_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        # Re-raise preserving captured stdout/stderr so failures are diagnosable.
        raise subprocess.CalledProcessError(
            exc.returncode,
            exc.cmd,
            output=exc.output,
            stderr=exc.stderr,
        ) from exc

    return lab_path / "results" / run_id / "scores.json"


def report_path_for_run(lab_path: Path, run_id: str) -> Path:
    """Return the LAB report path for a scored run."""
    _reject_unsafe_relative_path(run_id, "run_id")
    return lab_path / "results" / run_id / "report.html"


def compare_run(
    lab_path: Path,
    mode: Literal["task", "area", "all"],
    task_id: str,
) -> list[Path]:
    """Invoke LAB comparison dashboards and return their expected artifact paths."""
    _reject_unsafe_relative_path(task_id, "task_id")

    cmd = ["uv", "run", "python", "-m", "evaluation.compare"]
    results_dir = lab_path / "results" / "comparisons"
    if mode == "task":
        cmd.extend(["--task", task_id])
        dashboard_path = results_dir / task_id / "comparison.html"
    elif mode == "area":
        area = task_id.split("/", maxsplit=1)[0]
        _reject_unsafe_relative_path(area, "task_area")
        cmd.extend(["--area", area])
        dashboard_path = results_dir / area / "comparison.html"
    elif mode == "all":
        cmd.append("--all")
        dashboard_path = results_dir / "_global" / "comparison.html"
    else:
        raise ValueError(f"compare mode must be one of task, area, all: {mode!r}")

    before_mtime = dashboard_path.stat().st_mtime_ns if dashboard_path.exists() else None

    try:
        subprocess.run(
            cmd,
            cwd=lab_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise subprocess.CalledProcessError(
            exc.returncode,
            exc.cmd,
            output=exc.output,
            stderr=exc.stderr,
        ) from exc

    if not dashboard_path.exists():
        raise FileNotFoundError(f"LAB comparison did not create {dashboard_path}")
    after_mtime = dashboard_path.stat().st_mtime_ns
    if before_mtime is not None and after_mtime <= before_mtime:
        raise FileNotFoundError(f"LAB comparison did not update {dashboard_path}")

    return [dashboard_path]
