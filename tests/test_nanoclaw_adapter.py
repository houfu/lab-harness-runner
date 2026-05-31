"""Unit tests for NanoclawAdapter."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_poll_status_done_returns_clean(outbound_db: Path) -> None:
    """STATUS: DONE in messages_out -> end_state 'clean'."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    conn = sqlite3.connect(str(outbound_db))
    conn.execute(
        "INSERT INTO messages_out (content) VALUES (?)",
        (json.dumps({"text": "STATUS: DONE"}),),
    )
    conn.commit()
    conn.close()

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db, timeout_seconds=5.0, poll_interval=0.1
    )
    assert result == "clean"


def test_poll_status_error_returns_agent_error(outbound_db: Path) -> None:
    """STATUS: ERROR in messages_out -> end_state 'agent_error'."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    conn = sqlite3.connect(str(outbound_db))
    conn.execute(
        "INSERT INTO messages_out (content) VALUES (?)",
        (json.dumps({"text": "STATUS: ERROR"}),),
    )
    conn.commit()
    conn.close()

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db, timeout_seconds=5.0, poll_interval=0.1
    )
    assert result == "agent_error"


def test_poll_non_done_status_returns_agent_error(outbound_db: Path) -> None:
    """Any non-DONE STATUS: value -> end_state 'agent_error'."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    conn = sqlite3.connect(str(outbound_db))
    conn.execute(
        "INSERT INTO messages_out (content) VALUES (?)",
        (json.dumps({"text": "STATUS: FAILED"}),),
    )
    conn.commit()
    conn.close()

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db, timeout_seconds=5.0, poll_interval=0.1
    )
    assert result == "agent_error"


def test_poll_timeout_returns_timeout(outbound_db: Path) -> None:
    """Empty messages_out with tiny timeout -> end_state 'timeout'."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db, timeout_seconds=0.3, poll_interval=0.1
    )
    assert result == "timeout"


def test_poll_missing_db_does_not_raise(tmp_path: Path) -> None:
    """Non-existent outbound.db -> returns 'timeout' without raising."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    missing_path = tmp_path / "nonexistent" / "outbound.db"
    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        missing_path, timeout_seconds=0.3, poll_interval=0.1
    )
    assert result == "timeout"


def test_build_message_content_includes_contract(tmp_path: Path) -> None:
    """_build_message_content includes instructions, output path, deliverables, STATUS signals."""
    from lab_harness_runner.adapter import TaskSpec
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    task_spec = TaskSpec(
        task_id="area/test-task",
        instructions="Analyze this document carefully.",
        documents_dir=tmp_path / "documents",
        expected_deliverables=["report.docx", "summary.txt"],
        run_id="run-001",
    )
    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    content_json = adapter._build_message_content(task_spec)
    parsed = json.loads(content_json)
    text = parsed["text"]

    assert task_spec.instructions in text
    assert "/workspace/extra/lab-output" in text
    assert "report.docx" in text
    assert "summary.txt" in text
    assert "STATUS: DONE" in text
    assert "STATUS: ERROR" in text


def test_unsafe_group_id_rejected() -> None:
    """NanoclawAdapter(path, group_id='../evil') raises ValueError."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    with pytest.raises(ValueError):
        NanoclawAdapter(Path("/tmp"), group_id="../evil")


def test_dispatch_calls_shim_and_returns_clean(
    tmp_path: Path, outbound_db: Path
) -> None:
    """run() calls subprocess with send-lab-message.ts and returns end_state='clean'.

    Patches subprocess.run to return a fake shim JSON stdout pointing at the
    outbound_db fixture, pre-inserts STATUS: DONE so poll terminates fast.
    """
    from lab_harness_runner.adapter import TaskSpec
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    # Pre-insert a STATUS: DONE row so the poll terminates immediately
    conn = sqlite3.connect(str(outbound_db))
    conn.execute(
        "INSERT INTO messages_out (content) VALUES (?)",
        (json.dumps({"text": "STATUS: DONE"}),),
    )
    conn.commit()
    conn.close()

    # Create a minimal nanoclaw_dir with a stub central DB that has a
    # container_configs row for the test group
    nanoclaw_dir = tmp_path / "nanoclaw"
    data_dir = nanoclaw_dir / "data"
    data_dir.mkdir(parents=True)
    central_db = data_dir / "v2.db"
    db_conn = sqlite3.connect(str(central_db))
    db_conn.execute("""CREATE TABLE container_configs (
            agent_group_id TEXT PRIMARY KEY,
            additional_mounts TEXT DEFAULT '[]',
            updated_at TEXT
        )""")
    db_conn.execute(
        "INSERT INTO container_configs (agent_group_id, additional_mounts, updated_at)"
        " VALUES (?, ?, ?)",
        ("lab-test-group", "[]", "2026-01-01T00:00:00Z"),
    )
    db_conn.commit()
    db_conn.close()

    # task_spec with a real documents_dir
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    task_spec = TaskSpec(
        task_id="area/dispatch-test",
        instructions="Write a brief report.",
        documents_dir=documents_dir,
        expected_deliverables=["report.txt"],
        run_id="run-dispatch-test",
    )

    # Shim stdout: JSON line with sessionId + outboundDbPath pointing at fixture
    shim_stdout = json.dumps(
        {"sessionId": "sess-test-001", "outboundDbPath": str(outbound_db)}
    )

    adapter = NanoclawAdapter(
        nanoclaw_dir=nanoclaw_dir,
        group_id="lab-test-group",
        timeout_seconds=5.0,
        poll_interval=0.1,
    )

    with patch("lab_harness_runner.nanoclaw_adapter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=shim_stdout + "\n",
            stderr="",
        )
        result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    # Assert subprocess.run was called once with the shim command
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert any("send-lab-message.ts" in arg for arg in cmd)
    assert "--group-id" in cmd
    assert "lab-test-group" in cmd

    # Assert run() returned the correct end state
    assert result.end_state == "clean"
    assert result.run_id == "run-dispatch-test"
