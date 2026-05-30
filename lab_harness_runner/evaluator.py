from __future__ import annotations

import subprocess
from pathlib import Path


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
    """
    output_dir = lab_path / "results" / run_id / "output"

    # D-11: pre-score validation — check output_dir, not run_dir (Pitfall 4)
    missing = [
        name for name in expected_deliverables if not (output_dir / name).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing deliverables in {output_dir}: {', '.join(missing)}"
        )

    # D-10: subprocess invocation — list form, cwd=lab_path, check=True
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
    )

    return lab_path / "results" / run_id / "scores.json"
