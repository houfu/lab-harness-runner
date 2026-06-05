"""Unit tests for NanoclawAdapter."""

from __future__ import annotations

import json
import sqlite3
import time
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
        outbound_db, outbound_db.parent, [], timeout_seconds=5.0, poll_interval=0.1
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
        outbound_db, outbound_db.parent, [], timeout_seconds=5.0, poll_interval=0.1
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
        outbound_db, outbound_db.parent, [], timeout_seconds=5.0, poll_interval=0.1
    )
    assert result == "agent_error"


def test_poll_timeout_returns_timeout(outbound_db: Path) -> None:
    """Empty messages_out with tiny timeout -> end_state 'timeout'."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db, outbound_db.parent, [], timeout_seconds=0.3, poll_interval=0.1
    )
    assert result == "timeout"


def test_poll_missing_db_does_not_raise(tmp_path: Path) -> None:
    """Non-existent outbound.db -> returns 'timeout' without raising."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    missing_path = tmp_path / "nonexistent" / "outbound.db"
    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        missing_path, tmp_path, [], timeout_seconds=0.3, poll_interval=0.1
    )
    assert result == "timeout"


def test_poll_deliverables_present_exits_early(
    outbound_db: Path, tmp_path: Path
) -> None:
    """Deliverables present + size-stable, no STATUS: -> 'timeout' returned early.

    Raw end_state is 'timeout' (no terminal signal seen), but the loop exits well
    before the deadline because the deliverable landed. derive_benchmark_status
    maps deliverable presence to benchmark_status='clean' downstream.
    """
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "report.txt").write_text("deliverable contents")

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    start = time.monotonic()
    result = adapter._poll_for_status(
        outbound_db,
        output_dir,
        ["report.txt"],
        timeout_seconds=10.0,
        poll_interval=0.05,
    )
    elapsed = time.monotonic() - start

    assert result == "timeout"
    assert elapsed < 2.0  # exited early on deliverable presence, not after 10s


def test_poll_status_done_wins_over_deliverables(
    outbound_db: Path, tmp_path: Path
) -> None:
    """A terminal STATUS: DONE short-circuits to 'clean' even with deliverables present."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    conn = sqlite3.connect(str(outbound_db))
    conn.execute(
        "INSERT INTO messages_out (content) VALUES (?)",
        (json.dumps({"text": "STATUS: DONE"}),),
    )
    conn.commit()
    conn.close()

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "report.txt").write_text("x")

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db,
        output_dir,
        ["report.txt"],
        timeout_seconds=5.0,
        poll_interval=0.05,
    )
    assert result == "clean"


def test_poll_empty_deliverable_does_not_latch(
    outbound_db: Path, tmp_path: Path
) -> None:
    """A zero-byte deliverable is not treated as complete -> falls through to timeout."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "report.txt").touch()  # 0 bytes — not yet written

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(
        outbound_db,
        output_dir,
        ["report.txt"],
        timeout_seconds=0.3,
        poll_interval=0.05,
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

    # Shim stdout can include runtime noise before the JSON line.
    shim_stdout = "\n".join(
        [
            "wakeContainer: container already running",
            json.dumps(
                {"sessionId": "sess-test-001", "outboundDbPath": str(outbound_db)}
            ),
        ]
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


# ---------------------------------------------------------------------------
# EphemeralNanoclawAdapter — per-run group create/destroy orchestration
# ---------------------------------------------------------------------------


def _eph_task_spec(tmp_path: Path) -> "object":
    from lab_harness_runner.adapter import TaskSpec

    docs = tmp_path / "documents"
    docs.mkdir(exist_ok=True)
    return TaskSpec(
        task_id="area/eph-task",
        instructions="Do it.",
        documents_dir=docs,
        expected_deliverables=["answer.docx"],
        run_id="run-eph-1",
    )


def test_create_group_parses_noisy_stdout(tmp_path: Path) -> None:
    """_create_group scans past INFO log noise for the JSON result line."""
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(
        nanoclaw_dir=tmp_path, model="custom-model:cloud"
    )
    noisy = "\n".join(
        [
            "[12:00:00.000] INFO Central DB initialized",
            "[12:00:00.001] INFO Initialized group filesystem",
            json.dumps(
                {
                    "groupId": "ag-123-abc",
                    "folder": "lab-eph-xyz",
                    "model": "custom-model:cloud",
                }
            ),
        ]
    )
    with patch("lab_harness_runner.nanoclaw_adapter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=noisy + "\n", stderr="")
        group_id = adapter._create_group("lab-eph-xyz")

    assert group_id == "ag-123-abc"
    cmd = mock_run.call_args[0][0]
    assert any("create-lab-group.ts" in arg for arg in cmd)
    # The chosen model is forwarded to the create shim.
    assert "--model" in cmd
    assert "custom-model:cloud" in cmd


def test_ephemeral_model_neutral_by_default(tmp_path: Path) -> None:
    """No model arg -> model is None and --model is NOT passed to the create shim."""
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(nanoclaw_dir=tmp_path)
    assert adapter.model is None

    result_line = json.dumps({"groupId": "ag-x", "folder": "f", "model": None})
    with patch("lab_harness_runner.nanoclaw_adapter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=result_line + "\n", stderr=""
        )
        adapter._create_group("lab-eph-x")

    cmd = mock_run.call_args[0][0]
    assert "--model" not in cmd


def test_ephemeral_creates_and_destroys_on_success(tmp_path: Path) -> None:
    """Successful run -> group created once, inner adapter runs, group destroyed.

    The outer adapter merges the inner's end_state / wall_clock_seconds with
    the extractor's None fields (NoOp for model=None default). The merged
    RunResult is a NEW instance, not the inner's — the wiring in Plan 02
    builds a new RunResult so the extractor's metric fields can replace the
    base's (all-None) ones.
    """
    from lab_harness_runner.adapter import RunResult
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(nanoclaw_dir=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    task_spec = _eph_task_spec(tmp_path)
    inner_result = RunResult(
        run_id="run-eph-1", end_state="timeout", wall_clock_seconds=1.0
    )

    inner = MagicMock()
    inner.run.return_value = inner_result

    with (
        patch.object(adapter, "_create_group", return_value="ag-eph-99") as create,
        patch.object(adapter, "_destroy_group") as destroy,
        patch(
            "lab_harness_runner.nanoclaw_adapter.NanoclawAdapter",
            return_value=inner,
        ) as ctor,
    ):
        result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    create.assert_called_once()
    # Inner adapter was bound to the freshly created group id.
    assert ctor.call_args.kwargs["group_id"] == "ag-eph-99"
    destroy.assert_called_once_with("ag-eph-99")
    # The merge preserves the inner's run_id, end_state, wall_clock_seconds
    # (the adapter's invariants) and uses the extractor's None fields
    # (NoOp path for model=None default).
    assert result.end_state == inner_result.end_state  # "timeout" (preserved by the merge)
    assert result.run_id == inner_result.run_id  # "run-eph-1" (preserved by the merge)
    assert result.wall_clock_seconds == inner_result.wall_clock_seconds  # 1.0 (preserved)
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.documents_read is None
    assert result.documents_read_list is None


def test_ephemeral_destroys_on_failure_by_default(tmp_path: Path) -> None:
    """Inner run raising -> group still destroyed (keep_failed defaults False)."""
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(nanoclaw_dir=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    task_spec = _eph_task_spec(tmp_path)

    inner = MagicMock()
    inner.run.side_effect = RuntimeError("dispatch blew up")

    with (
        patch.object(adapter, "_create_group", return_value="ag-eph-fail"),
        patch.object(adapter, "_destroy_group") as destroy,
        patch(
            "lab_harness_runner.nanoclaw_adapter.NanoclawAdapter", return_value=inner
        ),
        pytest.raises(RuntimeError, match="dispatch blew up"),
    ):
        adapter.run(task_spec=task_spec, output_dir=output_dir)

    destroy.assert_called_once_with("ag-eph-fail")


def test_ephemeral_keeps_failed_group_when_flag_set(tmp_path: Path) -> None:
    """keep_failed=True -> a failed run's group is retained (not destroyed)."""
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(nanoclaw_dir=tmp_path, keep_failed=True)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    task_spec = _eph_task_spec(tmp_path)

    inner = MagicMock()
    inner.run.side_effect = RuntimeError("boom")

    with (
        patch.object(adapter, "_create_group", return_value="ag-keep"),
        patch.object(adapter, "_destroy_group") as destroy,
        patch(
            "lab_harness_runner.nanoclaw_adapter.NanoclawAdapter", return_value=inner
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        adapter.run(task_spec=task_spec, output_dir=output_dir)

    destroy.assert_not_called()


# ---------------------------------------------------------------------------
# EphemeralNanoclawAdapter + MetricsExtractor integration (Plan 02, D-13..D-17)
# ---------------------------------------------------------------------------


def test_ephemeral_extracts_metrics_for_claude_model(
    tmp_path: Path, transcript_dir_with_claude_session: tuple[Path, str, str]
) -> None:
    """EphemeralNanoclawAdapter(model='claude-*') -> Anthropic extractor fires.

    Phase 6 D-16 / D-17 integration test: the wiring in
    EphemeralNanoclawAdapter.run() binds the deferred Anthropic extractor to
    the per-group transcript_dir + the shim's sessionId, runs the inner
    NanoclawAdapter (mocked), then merges the extractor's metric fields
    into the returned RunResult.

    The fixture provides a jsonl with two assistant messages
    (input=100+200=300, output=50+80=130) and one Read tool_use block
    (file_path=/tmp/foo.txt).
    """
    from lab_harness_runner.adapter import RunResult
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    _transcript_dir, group_id, session_id = transcript_dir_with_claude_session

    adapter = EphemeralNanoclawAdapter(
        nanoclaw_dir=tmp_path, model="claude-opus-4-8"
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    task_spec = _eph_task_spec(tmp_path)

    # The inner NanoclawAdapter's run() is mocked to return a stub
    # RunResult; shim_session_id is stashed on the mock instance by
    # the wiring (we set it explicitly so the merge's adapter.shim_session_id
    # read returns the fixture's sessionId).
    inner = MagicMock()
    inner.run.return_value = RunResult(
        run_id=task_spec.run_id, end_state="clean", wall_clock_seconds=42.0
    )
    inner.shim_session_id = session_id

    with (
        patch.object(adapter, "_create_group", return_value=group_id),
        patch.object(adapter, "_destroy_group"),
        patch(
            "lab_harness_runner.nanoclaw_adapter.NanoclawAdapter",
            return_value=inner,
        ),
    ):
        result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    # The merge preserves the inner's end_state / wall_clock_seconds /
    # run_id (adapter's invariants) and replaces the token / coverage
    # fields with the extractor's output.
    assert result.end_state == "clean"
    assert result.wall_clock_seconds == 42.0
    assert result.run_id == task_spec.run_id
    # D-05 / D-09 / D-13: extracted metrics come from the jsonl.
    assert result.input_tokens == 300
    assert result.output_tokens == 130
    # D-07 / D-08: documents_read is the count, documents_read_list is
    # the verbatim file_path strings (no basename remapping).
    assert result.documents_read == 1
    assert result.documents_read_list == ["/tmp/foo.txt"]


def test_ephemeral_noop_for_non_claude_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """EphemeralNanoclawAdapter(model='ollama') -> NoOp path; all fields None.

    Phase 6 D-10 / EXT-04 Ollama clause: a non-claude model routes to the
    no-op extractor. The no-op returns a RunResult with all token /
    coverage fields as None and emits no stderr breadcrumb (the breadcrumb
    is gated on the deferred-Anthropic branch).
    """
    from lab_harness_runner.adapter import RunResult
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(nanoclaw_dir=tmp_path, model="ollama")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    task_spec = _eph_task_spec(tmp_path)

    inner = MagicMock()
    inner.run.return_value = RunResult(
        run_id=task_spec.run_id, end_state="clean", wall_clock_seconds=7.5
    )
    inner.shim_session_id = "sess-noop-001"

    with (
        patch.object(adapter, "_create_group", return_value="ag-noop-1"),
        patch.object(adapter, "_destroy_group"),
        patch(
            "lab_harness_runner.nanoclaw_adapter.NanoclawAdapter",
            return_value=inner,
        ),
    ):
        result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    # Adapter invariants preserved.
    assert result.end_state == "clean"
    assert result.wall_clock_seconds == 7.5
    assert result.run_id == task_spec.run_id
    # All metric fields are None — the NoOp path.
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.documents_read is None
    assert result.total_vdr_files is None
    assert result.documents_skipped is None
    assert result.documents_read_list is None
    assert result.documents_skipped_list is None

    # Defensive: the no-op path must not log the missing-transcript
    # breadcrumb (the breadcrumb is gated on _DeferredAnthropicExtractor).
    captured = capsys.readouterr()
    assert "transcript not found" not in captured.err
    assert "transcript not found" not in captured.out


def test_ephemeral_logs_breadcrumb_on_missing_transcript(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """model='claude-opus-4-8' with no jsonl on disk -> D-14 breadcrumb + base result.

    Phase 6 D-14: when the deferred Anthropic extractor cannot find a
    matching sessionId jsonl, the adapter logs a one-line stderr breadcrumb
    and returns the base RunResult with all token / coverage fields None
    (the base result is preserved, not replaced with a partial extract).
    """
    from lab_harness_runner.adapter import RunResult
    from lab_harness_runner.nanoclaw_adapter import EphemeralNanoclawAdapter

    adapter = EphemeralNanoclawAdapter(
        nanoclaw_dir=tmp_path, model="claude-opus-4-8"
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    task_spec = _eph_task_spec(tmp_path)

    inner = MagicMock()
    inner.run.return_value = RunResult(
        run_id=task_spec.run_id, end_state="clean", wall_clock_seconds=15.0
    )
    # A sessionId the resolver will not find — the jsonl does not exist
    # in tmp_path/v2-sessions/<group>/.claude-shared/projects/-workspace-agent/
    # because tmp_path has no v2-sessions layout.
    inner.shim_session_id = "sess-missing-001"

    with (
        patch.object(adapter, "_create_group", return_value="ag-missing-1"),
        patch.object(adapter, "_destroy_group"),
        patch(
            "lab_harness_runner.nanoclaw_adapter.NanoclawAdapter",
            return_value=inner,
        ),
    ):
        result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    # Adapter invariants preserved (end_state + wall_clock_seconds from
    # the inner adapter's poll loop).
    assert result.end_state == "clean"
    assert result.wall_clock_seconds == 15.0
    assert result.run_id == task_spec.run_id
    # The base result is kept: all metric fields stay None.
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.documents_read is None
    assert result.documents_read_list is None

    # D-14: stderr breadcrumb is logged with the exact format.
    captured = capsys.readouterr()
    assert (
        "[ephemeral] metrics: transcript not found for session "
        "sess-missing-001; skipping extraction"
    ) in captured.err
