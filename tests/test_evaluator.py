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


def test_score_run_rejects_unsafe_expected_deliverable_before_subprocess(tmp_path):
    """score_run rejects traversal deliverable names before checking the filesystem."""
    from lab_harness_runner.evaluator import score_run

    run_dir = tmp_path / "results" / "run-id"
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True)
    (run_dir / "outside.docx").write_text("wrong location", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        with pytest.raises(ValueError):
            score_run(
                lab_path=tmp_path,
                run_id="run-id",
                task_id="area/task",
                expected_deliverables=["../outside.docx"],
            )

    mock_run.assert_not_called()


def test_score_run_raises_before_subprocess_when_missing(tmp_path):
    """score_run raises FileNotFoundError BEFORE subprocess when deliverable missing."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "my-run" / "output"
    output_dir.mkdir(parents=True)
    # Do NOT create "output.docx"

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        with pytest.raises(FileNotFoundError):
            score_run(tmp_path, "my-run", "test-area/test-task", ["output.docx"])
        # subprocess must NOT have been called
        mock_run.assert_not_called()


def test_score_run_calls_subprocess_when_files_present(tmp_path):
    """score_run calls subprocess when all deliverables are present."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "my-run" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "output.docx").write_bytes(b"")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        score_run(tmp_path, "my-run", "test-area/test-task", ["output.docx"])
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "--run-id" in cmd
    assert "my-run" in cmd


def test_score_run_uses_cwd_lab_path_fixture(tmp_path):
    """score_run passes cwd=lab_path to subprocess."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "my-run" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "output.docx").write_bytes(b"")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        score_run(tmp_path, "my-run", "test-area/test-task", ["output.docx"])
    assert mock_run.call_args[1]["cwd"] == tmp_path


def test_score_run_returns_scores_path_fixture(tmp_path):
    """score_run returns lab_path / 'results' / run_id / 'scores.json'."""
    from lab_harness_runner.evaluator import score_run

    output_dir = tmp_path / "results" / "my-run" / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "output.docx").write_bytes(b"")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = score_run(tmp_path, "my-run", "test-area/test-task", ["output.docx"])
    assert result == tmp_path / "results" / "my-run" / "scores.json"


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


def test_report_path_for_run_returns_lab_report_html_path(tmp_path):
    from lab_harness_runner.evaluator import report_path_for_run

    assert report_path_for_run(tmp_path, "run-id") == (
        tmp_path / "results" / "run-id" / "report.html"
    )


def test_compare_run_task_invokes_lab_compare_and_returns_artifact_paths(tmp_path):
    from lab_harness_runner.evaluator import compare_run

    dashboard_path = (
        tmp_path / "results" / "comparisons" / "area" / "task" / "comparison.html"
    )

    def create_dashboard(*args, **kwargs):
        dashboard_path.parent.mkdir(parents=True)
        dashboard_path.write_text("dashboard", encoding="utf-8")
        return MagicMock(returncode=0)

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.side_effect = create_dashboard
        paths = compare_run(tmp_path, mode="task", task_id="area/task")

    mock_run.assert_called_once_with(
        [
            "uv",
            "run",
            "python",
            "-m",
            "evaluation.compare",
            "--task",
            "area/task",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert paths == [dashboard_path]


def test_compare_run_area_invokes_lab_compare_for_task_area(tmp_path):
    from lab_harness_runner.evaluator import compare_run

    dashboard_path = tmp_path / "results" / "comparisons" / "area" / "comparison.html"

    def create_dashboard(*args, **kwargs):
        dashboard_path.parent.mkdir(parents=True)
        dashboard_path.write_text("dashboard", encoding="utf-8")
        return MagicMock(returncode=0)

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.side_effect = create_dashboard
        paths = compare_run(tmp_path, mode="area", task_id="area/task")

    cmd = mock_run.call_args.args[0]
    assert cmd[-2:] == ["--area", "area"]
    assert paths == [tmp_path / "results" / "comparisons" / "area" / "comparison.html"]


def test_compare_run_all_invokes_lab_compare_global(tmp_path):
    from lab_harness_runner.evaluator import compare_run

    dashboard_path = (
        tmp_path / "results" / "comparisons" / "_global" / "comparison.html"
    )

    def create_dashboard(*args, **kwargs):
        dashboard_path.parent.mkdir(parents=True)
        dashboard_path.write_text("dashboard", encoding="utf-8")
        return MagicMock(returncode=0)

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.side_effect = create_dashboard
        paths = compare_run(tmp_path, mode="all", task_id="area/task")

    cmd = mock_run.call_args.args[0]
    assert cmd[-1] == "--all"
    assert paths == [
        tmp_path / "results" / "comparisons" / "_global" / "comparison.html"
    ]


def test_compare_run_validates_inputs_before_subprocess(tmp_path):
    from lab_harness_runner.evaluator import compare_run

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        with pytest.raises(ValueError):
            compare_run(tmp_path, mode="task", task_id="../area/task")

    mock_run.assert_not_called()


def test_compare_run_raises_when_lab_does_not_create_dashboard(tmp_path):
    from lab_harness_runner.evaluator import compare_run

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        with pytest.raises(FileNotFoundError, match="LAB comparison did not create"):
            compare_run(tmp_path, mode="task", task_id="area/task")


def test_compare_run_raises_when_lab_only_leaves_stale_dashboard(tmp_path):
    from lab_harness_runner.evaluator import compare_run

    dashboard_path = (
        tmp_path / "results" / "comparisons" / "area" / "task" / "comparison.html"
    )
    dashboard_path.parent.mkdir(parents=True)
    dashboard_path.write_text("stale dashboard", encoding="utf-8")

    with patch("lab_harness_runner.evaluator.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        with pytest.raises(FileNotFoundError, match="LAB comparison did not update"):
            compare_run(tmp_path, mode="task", task_id="area/task")
