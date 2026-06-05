from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path


def test_fake_run_wires_task_adapter_result_dir_and_metrics(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "area" / "task"
    task_dir.mkdir(parents=True)
    (task_dir / "documents").mkdir()
    (task_dir / "task.json").write_text(
        json.dumps(
            {
                "title": "Temporary Task",
                "instructions": "Create the expected deliverables.",
                "criteria": [
                    {"deliverables": ["report.docx", "notes.txt"]},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/fake_run.py",
            "--task",
            "area/task",
            "--run-id",
            "run-001",
            "--lab-path",
            str(tmp_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )

    run_dir = tmp_path / "results" / "run-001"
    output_dir = run_dir / "output"
    metrics_path = run_dir / "metrics.json"

    assert f"Run directory: {run_dir}" in result.stdout
    assert "Scoring skipped" in result.stdout
    assert output_dir.is_dir()
    assert (output_dir / "notes.txt").read_text(encoding="utf-8").startswith(
        "Placeholder for notes.txt"
    )
    assert zipfile.is_zipfile(output_dir / "report.docx")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["end_state"] == "clean"
    # FakeAdapter does not measure token usage, so the contract is honest:
    # unmeasured fields are serialised as JSON null, distinct from 0.
    assert metrics["input_tokens"] is None
    assert metrics["output_tokens"] is None
