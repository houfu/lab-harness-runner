"""Nanoclaw-LQ adapter — poll loop, end-state mapping, and message footer.

Implements the STATUS: poll loop against nanoclaw's outbound.db, the D-04/D-05
inbound-message footer builder, and the Adapter protocol signature.

Dispatch/mount wiring is stubbed for Plan 02.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

from lab_harness_runner.adapter import RunResult, TaskSpec
from lab_harness_runner.task_reader import _reject_unsafe_relative_path

_FOOTER_TEMPLATE = (
    "\n\n---\n"
    "OUTPUT DIRECTORY: Write all deliverable files to /workspace/extra/lab-output/\n"
    "REQUIRED FILES: {filenames}\n"
    "COMPLETION SIGNAL: When all files are written, emit exactly: STATUS: DONE\n"
    "If you encounter an unrecoverable error, emit exactly: STATUS: ERROR\n"
    "Do not emit STATUS: until all files are fully written.\n"
)


class NanoclawAdapter:
    """Adapter that dispatches LAB tasks to nanoclaw-lq and polls for completion.

    Poll loop and footer logic are fully implemented.
    Dispatch/mount wiring is stubbed pending Plan 02.
    """

    def __init__(
        self,
        nanoclaw_dir: Path,
        group_id: str,
        timeout_seconds: float = 600.0,
        poll_interval: float = 5.0,
    ) -> None:
        _reject_unsafe_relative_path(group_id, "group_id")
        self.nanoclaw_dir = nanoclaw_dir.expanduser().resolve()
        self.group_id = group_id
        self.timeout_seconds = timeout_seconds
        self.poll_interval = poll_interval

    def _poll_for_status(
        self,
        outbound_db_path: Path,
        timeout_seconds: float,
        poll_interval: float,
    ) -> str:
        """Poll outbound.db messages_out for a STATUS: line.

        Opens, reads, and closes the DB per iteration — never holds a connection
        across a sleep (one-writer invariant for virtiofs cross-mounts).

        Returns one of: "clean", "agent_error", "timeout".
        """
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                conn = sqlite3.connect(str(outbound_db_path))
                rows = conn.execute(
                    "SELECT content FROM messages_out ORDER BY seq"
                ).fetchall()
                conn.close()
                for (content_json,) in rows:
                    try:
                        text = json.loads(content_json).get("text", "")
                    except Exception:
                        text = content_json
                    if text.startswith("STATUS:"):
                        status = text[len("STATUS:") :].strip().upper()
                        return "clean" if status == "DONE" else "agent_error"
            except Exception:
                pass  # DB not yet created or locked — retry
            time.sleep(poll_interval)
        return "timeout"

    def _build_message_content(self, task_spec: TaskSpec) -> str:
        """Build the JSON message content for the inbound nanoclaw message.

        Appends a D-04/D-05 footer to task_spec.instructions specifying the
        output directory, required deliverable filenames, and STATUS: signals.
        """
        filenames = ", ".join(task_spec.expected_deliverables)
        text = task_spec.instructions + _FOOTER_TEMPLATE.format(filenames=filenames)
        return json.dumps({"sender": "system", "senderId": "system", "text": text})

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        """Execute a LAB task via nanoclaw-lq and return a RunResult.

        Plan 01 stub: dispatch and mount wiring are not yet implemented.
        Full implementation lands in Plan 02.
        """
        start = time.monotonic()
        raise NotImplementedError("dispatch wired in Plan 02")
