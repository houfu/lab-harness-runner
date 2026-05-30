"""Tests for lab_harness_runner.task_reader."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lab_harness_runner.task_reader import _lab_path, read_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_task_json(
    tmp_path: Path,
    task_id: str = "area/slug",
    *,
    instructions: str = "Do the task.",
    criteria: list[dict] | None = None,
    extra: dict | None = None,
) -> Path:
    """Write a minimal task.json under tmp_path/tasks/<task_id>/task.json."""
    if criteria is None:
        criteria = [{"deliverables": ["report.docx", "analysis.txt"]}]
    task_dir = tmp_path / "tasks" / Path(*task_id.split("/"))
    task_dir.mkdir(parents=True, exist_ok=True)
    data: dict = {
        "title": "Test Task",
        "instructions": instructions,
        "criteria": criteria,
    }
    if extra:
        data.update(extra)
    task_json = task_dir / "task.json"
    task_json.write_text(json.dumps(data), encoding="utf-8")
    return task_json


# ---------------------------------------------------------------------------
# Tests for read_task
# ---------------------------------------------------------------------------


def test_read_task_returns_taskspec_with_correct_fields(tmp_path: Path) -> None:
    make_task_json(tmp_path, "area/slug")
    spec = read_task(tmp_path, "area/slug", "run-001")
    assert spec.task_id == "area/slug"
    assert spec.run_id == "run-001"
    assert spec.instructions == "Do the task."
    assert spec.documents_dir == tmp_path / "tasks" / "area" / "slug" / "documents"


def test_read_task_extracts_deliverables_from_criteria(tmp_path: Path) -> None:
    make_task_json(
        tmp_path,
        "area/slug",
        criteria=[
            {"deliverables": ["report.docx"]},
            {"deliverables": ["summary.txt", "report.docx"]},
        ],
    )
    spec = read_task(tmp_path, "area/slug", "run-001")
    # Unique deliverables, sorted
    assert spec.expected_deliverables == ["report.docx", "summary.txt"]


def test_read_task_ignores_top_level_deliverables_key(tmp_path: Path) -> None:
    """Top-level 'deliverables' dict in task.json must NOT be used."""
    make_task_json(
        tmp_path,
        "area/slug",
        criteria=[{"deliverables": ["report.docx"]}],
        extra={"deliverables": {"should_not_appear.txt": "should_not_appear.txt"}},
    )
    spec = read_task(tmp_path, "area/slug", "run-001")
    assert "should_not_appear.txt" not in spec.expected_deliverables


def test_read_task_raises_file_not_found_when_task_json_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_task(tmp_path, "area/missing", "run-001")


def test_read_task_raises_key_error_when_instructions_missing(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "area" / "noinstr"
    task_dir.mkdir(parents=True)
    (task_dir / "task.json").write_text(
        json.dumps({"title": "t", "criteria": []}), encoding="utf-8"
    )
    with pytest.raises(KeyError):
        read_task(tmp_path, "area/noinstr", "run-001")


def test_read_task_raises_value_error_for_double_dot_task_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        read_task(tmp_path, "area/../etc/passwd", "run-001")


def test_read_task_raises_value_error_for_absolute_task_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        read_task(tmp_path, "/etc/passwd", "run-001")


def test_read_task_raises_value_error_before_filesystem_access(tmp_path: Path) -> None:
    """ValueError must be raised before any filesystem access (no task.json needed)."""
    # No task directory created — if ValueError is raised first, no FileNotFoundError
    with pytest.raises(ValueError):
        read_task(tmp_path, "../traversal", "run-001")


def test_read_task_empty_criteria_returns_empty_deliverables(tmp_path: Path) -> None:
    make_task_json(tmp_path, "area/empty", criteria=[])
    spec = read_task(tmp_path, "area/empty", "run-001")
    assert spec.expected_deliverables == []


# ---------------------------------------------------------------------------
# Tests for _lab_path
# ---------------------------------------------------------------------------


def test_lab_path_returns_override_when_provided(tmp_path: Path) -> None:
    result = _lab_path(override=tmp_path)
    assert result == tmp_path


def test_lab_path_returns_env_var_when_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HARVEY_LAB_PATH", str(tmp_path))
    result = _lab_path()
    assert result == Path(str(tmp_path))


def test_lab_path_returns_fallback_when_no_env_or_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HARVEY_LAB_PATH", raising=False)
    result = _lab_path()
    assert result == Path.home() / "Projects" / "harvey-labs"
