"""Nanoclaw-LQ adapter — poll loop, end-state mapping, and message footer.

Implements the STATUS: poll loop against nanoclaw's outbound.db, the D-04/D-05
inbound-message footer builder, mount configuration, and dispatch via the Node shim.
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

# Filename of the nanoclaw central database (relative to nanoclaw_dir/data/)
_CENTRAL_DB_NAME = "v2.db"


class NanoclawAdapter:
    """Adapter that dispatches LAB tasks to nanoclaw-lq and polls for completion.

    Sequence in run():
      1. Configure additional_mounts in the nanoclaw container_configs DB
         (documents dir RO at lab-documents, output dir RW at lab-output).
      2. Dispatch: shell out to the Node shim send-lab-message.ts via subprocess.
      3. Poll the resolved session's outbound.db for a STATUS: signal.
      4. Return a RunResult.
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _central_db_path(self) -> Path:
        """Return the path to nanoclaw's central SQLite database."""
        return self.nanoclaw_dir / "data" / _CENTRAL_DB_NAME

    def _configure_additional_mounts(
        self, task_spec: TaskSpec, output_dir: Path
    ) -> None:
        """Write the two known lab mount entries to container_configs.additional_mounts.

        Only task_spec.documents_dir and output_dir are ever written as
        hostPaths — no caller-controlled arbitrary path reaches additional_mounts
        (T-03-04 mitigation).  containerPath values are relative bare names
        (T-03-06 mitigation — nanoclaw rejects absolute/.. containerPaths).

        Uses open/UPDATE/close per op (T-03-07 / one-writer invariant).
        """
        mounts = [
            {
                "hostPath": str(task_spec.documents_dir.resolve()),
                "containerPath": "lab-documents",
                "readonly": True,
            },
            {
                "hostPath": str(output_dir.resolve()),
                "containerPath": "lab-output",
                "readonly": False,
            },
        ]
        mounts_json = json.dumps(mounts)
        db_path = self._central_db_path()
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE container_configs"
            " SET additional_mounts = ?, updated_at = ?"
            " WHERE agent_group_id = ?",
            (
                mounts_json,
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                self.group_id,
            ),
        )
        conn.commit()
        conn.close()

    def _dispatch(self, task_spec: TaskSpec) -> dict:
        """Shell out to the Node shim and return its parsed JSON output.

        Raises subprocess.CalledProcessError on nonzero exit, preserving
        stdout/stderr (evaluator.py pattern).

        T-03-05 mitigation: explicit list form, never shell=True; group_id
        pre-validated by _reject_unsafe_relative_path; msg_id is uuid4.
        """
        msg_id = str(uuid.uuid4())
        content = self._build_message_content(task_spec)
        try:
            result = subprocess.run(
                [
                    "pnpm",
                    "exec",
                    "tsx",
                    "scripts/send-lab-message.ts",
                    "--group-id",
                    self.group_id,
                    "--message-id",
                    msg_id,
                    "--content",
                    content,
                ],
                cwd=self.nanoclaw_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise subprocess.CalledProcessError(
                exc.returncode,
                exc.cmd,
                output=exc.output,
                stderr=exc.stderr,
            ) from exc
        return json.loads(result.stdout.strip())

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        """Execute a LAB task via nanoclaw-lq and return a RunResult.

        Sequence:
          1. Configure additional_mounts BEFORE dispatch (Pitfall 4 — mounts
             only take effect on next container spawn).
          2. Dispatch via the Node shim subprocess.
          3. Poll the resolved session's outbound.db for a STATUS: signal.
          4. Return RunResult.
        """
        start = time.monotonic()

        # Step 1 — configure mounts before wake (Pitfall 4)
        # output_dir is created by build_result_dir before run() is called;
        # assert it exists so Docker does not create a root-owned directory.
        assert output_dir.exists(), f"output_dir must exist before run(): {output_dir}"
        self._configure_additional_mounts(task_spec, output_dir)

        # Step 2 — dispatch: shell out to send-lab-message.ts
        shim_result = self._dispatch(task_spec)
        outbound_db_path = Path(shim_result["outboundDbPath"])

        # Step 3 — poll for STATUS: signal
        end_state = self._poll_for_status(
            outbound_db_path, self.timeout_seconds, self.poll_interval
        )

        # Step 4 — return RunResult
        return RunResult(
            run_id=task_spec.run_id,
            end_state=end_state,
            wall_clock_seconds=time.monotonic() - start,
        )
