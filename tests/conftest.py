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


@pytest.fixture()
def transcript_dir_with_claude_session(tmp_path: Path) -> tuple[Path, str, str]:
    """Build a tmp_path-rooted nanoclaw transcript jsonl with a Claude session.

    The layout mirrors the D-04 path the adapter wires:
        <tmp_path>/data/v2-sessions/<group_id>/.claude-shared/projects/-workspace-agent/<session_id>.jsonl

    Test usage: pass ``nanoclaw_dir=tmp_path`` to the adapter; the wiring
    resolves the jsonl at ``nanoclaw_dir / "data" / "v2-sessions" / ...``
    and finds this fixture's file.

    Returns ``(transcript_dir, group_id, session_id)``. The jsonl contains:
      * Line 1: a system line that sets the sessionId for the resolver
        (D-04 reads ``sessionId`` at the top of each line).
      * Line 2: an assistant message with input_tokens=100, output_tokens=50
        (text-only content).
      * Line 3: an assistant message with input_tokens=200, output_tokens=80
        AND a ``Read`` tool_use block whose ``input.file_path`` is
        ``/tmp/foo.txt``.

    Expected sums (D-16 / D-17 integration test):
      input_tokens = 300, output_tokens = 130,
      documents_read = 1, documents_read_list = ["/tmp/foo.txt"].
    """
    group_id = "ag-test-eph"
    session_id = "sess-test-001"
    transcript_dir = (
        tmp_path
        / "data"
        / "v2-sessions"
        / group_id
        / ".claude-shared"
        / "projects"
        / "-workspace-agent"
    )
    transcript_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = transcript_dir / f"{session_id}.jsonl"
    lines = [
        json.dumps(
            {"sessionId": session_id, "type": "system", "content": "session boot"}
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "reading..."}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/foo.txt"},
                        }
                    ],
                    "usage": {"input_tokens": 200, "output_tokens": 80},
                },
            }
        ),
    ]
    jsonl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return transcript_dir, group_id, session_id
