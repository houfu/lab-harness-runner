"""Tests for lab_harness_runner.result_builder."""
from __future__ import annotations

from pathlib import Path

import pytest

from lab_harness_runner.result_builder import build_result_dir


def test_build_result_dir_creates_output_directory(tmp_path: Path) -> None:
    run_dir, output_dir = build_result_dir(tmp_path, "my-run")
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_build_result_dir_run_dir_path(tmp_path: Path) -> None:
    run_dir, output_dir = build_result_dir(tmp_path, "my-run")
    assert run_dir == tmp_path / "results" / "my-run"


def test_build_result_dir_output_dir_path(tmp_path: Path) -> None:
    run_dir, output_dir = build_result_dir(tmp_path, "my-run")
    assert output_dir == tmp_path / "results" / "my-run" / "output"


def test_build_result_dir_returns_tuple(tmp_path: Path) -> None:
    result = build_result_dir(tmp_path, "my-run")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_build_result_dir_idempotent(tmp_path: Path) -> None:
    """Calling twice with same run_id must not raise (exist_ok=True)."""
    build_result_dir(tmp_path, "my-run")
    build_result_dir(tmp_path, "my-run")  # must not raise


def test_build_result_dir_flat_run_id(tmp_path: Path) -> None:
    """A run_id with no slashes creates a single flat directory."""
    run_dir, output_dir = build_result_dir(tmp_path, "abc123")
    assert run_dir == tmp_path / "results" / "abc123"
    assert output_dir == tmp_path / "results" / "abc123" / "output"


def test_build_result_dir_rejects_unsafe_run_id_before_creating_paths(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError):
        build_result_dir(tmp_path, "../evil")

    assert not (tmp_path / "evil").exists()
    assert not (tmp_path / "results").exists()
