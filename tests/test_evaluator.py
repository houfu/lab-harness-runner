from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_score_run_calls_subprocess_with_correct_command(tmp_path):
    """score_run calls subprocess with the correct list-form command."""
    from lab_harness_runner.evaluator import score_run

    # Set up: create the expected deliverable files in output_dir
    output_dir = tmp_path / "results" / "my-run-id" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "report.docx").write_text("dummy", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        score_run(
            lab_path=tmp_path,
            run_id="my-run-id",
            task_id="area/my-task",
            expected_deliverables=["report.docx"],
        )

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    cmd = call_args[0][0]  # first positional arg is the command list

    assert cmd == [
        "uv",
        "run",
        "python",
        "-m",
        "evaluation.run_eval",
        "--run-id",
        "my-run-id",
        "--task",
        "area/my-task",
        "--judge-model",
        "claude-sonnet-4-6",
    ]


def test_score_run_uses_cwd_lab_path(tmp_path):
    """score_run passes cwd=lab_path to subprocess.run."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "run-id" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "file.txt").write_text("dummy", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        score_run(
            lab_path=tmp_path,
            run_id="run-id",
            task_id="area/task",
            expected_deliverables=["file.txt"],
        )

    call_kwargs = mock_run.call_args[1]
    assert call_kwargs["cwd"] == tmp_path


def test_score_run_uses_check_true(tmp_path):
    """score_run passes check=True to subprocess.run."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "run-id" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "file.txt").write_text("dummy", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        score_run(
            lab_path=tmp_path,
            run_id="run-id",
            task_id="area/task",
            expected_deliverables=["file.txt"],
        )

    call_kwargs = mock_run.call_args[1]
    assert call_kwargs["check"] is True


def test_score_run_returns_scores_json_path(tmp_path):
    """score_run returns lab_path / 'results' / run_id / 'scores.json'."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "run-id" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "file.txt").write_text("dummy", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = score_run(
            lab_path=tmp_path,
            run_id="run-id",
            task_id="area/task",
            expected_deliverables=["file.txt"],
        )

    assert result == tmp_path / "results" / "run-id" / "scores.json"


def test_score_run_raises_before_subprocess_when_deliverables_missing(tmp_path):
    """score_run raises FileNotFoundError BEFORE calling subprocess if deliverables missing."""
    from lab_harness_runner.evaluator import score_run

    # Create output_dir but don't create expected deliverables
    output_dir = tmp_path / "results" / "run-id" / "output"
    output_dir.mkdir(parents=True)

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        with pytest.raises(FileNotFoundError):
            score_run(
                lab_path=tmp_path,
                run_id="run-id",
                task_id="area/task",
                expected_deliverables=["missing-file.docx"],
            )
        # subprocess must NOT have been called
        mock_run.assert_not_called()


def test_score_run_error_message_lists_all_missing(tmp_path):
    """FileNotFoundError message lists all missing filenames."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "run-id" / "output"
    output_dir.mkdir(parents=True)
    # Create only one of the two expected deliverables
    (output_dir / "present.docx").write_text("exists", encoding="utf-8")

    with pytest.raises(FileNotFoundError) as exc_info:
        score_run(
            lab_path=tmp_path,
            run_id="run-id",
            task_id="area/task",
            expected_deliverables=["present.docx", "missing.docx"],
        )

    assert "missing.docx" in str(exc_info.value)
    assert "present.docx" not in str(exc_info.value)


def test_score_run_validates_in_output_dir_not_run_dir(tmp_path):
    """score_run validates in output_dir (lab_path/results/run_id/output/), not run_dir."""
    from lab_harness_runner.evaluator import score_run

    # Put the deliverable in run_dir (not output_dir) — should still raise
    run_dir = tmp_path / "results" / "run-id"
    run_dir.mkdir(parents=True)
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True)
    # File in run_dir, NOT in output_dir
    (run_dir / "report.docx").write_text("in wrong dir", encoding="utf-8")

    with pytest.raises(FileNotFoundError) as exc_info:
        score_run(
            lab_path=tmp_path,
            run_id="run-id",
            task_id="area/task",
            expected_deliverables=["report.docx"],
        )

    assert "report.docx" in str(exc_info.value)


def test_score_run_custom_judge_model(tmp_path):
    """score_run passes judge_model to the subprocess command."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "run-id" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "file.txt").write_text("dummy", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        score_run(
            lab_path=tmp_path,
            run_id="run-id",
            task_id="area/task",
            expected_deliverables=["file.txt"],
            judge_model="claude-opus-4",
        )

    cmd = mock_run.call_args[0][0]
    assert "--judge-model" in cmd
    idx = cmd.index("--judge-model")
    assert cmd[idx + 1] == "claude-opus-4"
