"""Shared pytest fixtures for lab_harness_runner tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab_harness_runner.adapter import RunResult


@pytest.fixture()
def tmp_lab(tmp_path: Path) -> Path:
    """Create a minimal LAB directory tree for testing.

    Structure::

        tmp_path/
          tasks/
            test-area/
              test-task/
                task.json  (with criteria[].deliverables: ["output.docx"])
                documents/ (empty directory)
          results/

    Returns:
        tmp_path — the mock lab_path root.

    The canonical task_id for this fixture is "test-area/test-task".
    """
    task_dir = tmp_path / "tasks" / "test-area" / "test-task"
    task_dir.mkdir(parents=True)

    task_data = {
        "title": "Test Task",
        "instructions": "Do the test.",
        "criteria": [
            {
                "id": "c1",
                "title": "Criterion 1",
                "match_criteria": "...",
                "deliverables": ["output.docx"],
            }
        ],
    }
    (task_dir / "task.json").write_text(json.dumps(task_data), encoding="utf-8")
    (task_dir / "documents").mkdir()

    (tmp_path / "results").mkdir()

    return tmp_path


@pytest.fixture()
def sample_run_result() -> RunResult:
    """Return a populated RunResult for metrics tests.

    Provides a deterministic result with:
        run_id="test-run-001", end_state="clean",
        wall_clock_seconds=1.5, input_tokens=100, output_tokens=50
    """
    return RunResult(
        run_id="test-run-001",
        end_state="clean",
        wall_clock_seconds=1.5,
        input_tokens=100,
        output_tokens=50,
    )


@pytest.fixture()
def outbound_db(tmp_path: Path) -> Path:
    """Create a synthetic outbound.db with messages_out table.

    Returns the path to the DB file. The session directory structure mirrors
    nanoclaw's data/v2-sessions/<agentGroupId>/<sessionId>/outbound.db layout.
    """
    import sqlite3

    session_dir = tmp_path / "v2-sessions" / "ag-test" / "sess-test"
    session_dir.mkdir(parents=True)
    db_path = session_dir / "outbound.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE messages_out (seq INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    return db_path
