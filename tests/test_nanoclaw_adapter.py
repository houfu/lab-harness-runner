"""Failing tests for NanoclawAdapter — TDD RED phase for Task 2."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

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
