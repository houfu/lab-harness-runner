"""Nanoclaw-LQ adapter — poll loop, end-state mapping, and message footer.

Implements the STATUS: poll loop against nanoclaw's outbound.db, the D-04/D-05
inbound-message footer builder, mount configuration, and dispatch via the Node shim.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
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
        # The nanoclaw container runtime (OneCLI SDK / docker spawn invoked by
        # wakeContainer) can emit unstructured lines on stdout. The shim's JSON
        # result is one line among that noise, so scan for the line that parses
        # as our result object instead of assuming stdout is JSON-only.
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(parsed, dict)
                and "sessionId" in parsed
                and "outboundDbPath" in parsed
            ):
                return parsed
        raise ValueError(
            "nanoclaw shim produced no parseable JSON result line on stdout; "
            f"stdout was:\n{result.stdout}"
        )

    def _read_terminal_status(self, outbound_db_path: Path) -> str | None:
        """Return "clean"/"agent_error" if a terminal STATUS: line exists, else None.

        Opens, reads, and closes the DB per call — never holds a connection across
        a sleep (one-writer invariant for virtiofs cross-mounts). Swallows errors
        (DB not yet created or locked) and returns None so the caller retries.
        """
        try:
            conn = sqlite3.connect(str(outbound_db_path))
            rows = conn.execute(
                "SELECT content FROM messages_out ORDER BY seq"
            ).fetchall()
            conn.close()
        except Exception:
            return None  # DB not yet created or locked — caller retries
        for (content_json,) in rows:
            try:
                text = json.loads(content_json).get("text", "")
            except Exception:
                text = content_json
            if text.startswith("STATUS:"):
                status = text[len("STATUS:") :].strip().upper()
                return "clean" if status == "DONE" else "agent_error"
        return None

    def _deliverable_sizes(
        self, output_dir: Path, expected_deliverables: list[str]
    ) -> dict[str, int] | None:
        """Return {name: byte_size} for the expected deliverables, or None.

        None means at least one expected deliverable is missing or empty (size 0)
        — the caller treats that as "not yet complete" and keeps polling. Empty
        files are excluded to avoid latching onto a just-created, not-yet-written
        file. Names are validated as safe relative paths (no absolute/.. paths).
        """
        sizes: dict[str, int] = {}
        for name in expected_deliverables:
            rel = _reject_unsafe_relative_path(name, "expected_deliverable")
            path = output_dir / rel
            if not path.exists():
                return None
            size = path.stat().st_size
            if size <= 0:
                return None
            sizes[name] = size
        return sizes

    def _poll_for_status(
        self,
        outbound_db_path: Path,
        output_dir: Path,
        expected_deliverables: list[str],
        timeout_seconds: float,
        poll_interval: float,
    ) -> str:
        """Poll for completion, gated on deliverables — not the agent's self-report.

        The loop exits as soon as every expected deliverable is present in
        output_dir and byte-size-stable across one poll interval (the stability
        check guards against latching onto a half-written file). A terminal
        STATUS: line still short-circuits when present, but its absence no longer
        forces a full-timeout wait.

        Returns one of "clean", "agent_error", "timeout":
          - "clean"/"agent_error": a terminal STATUS: line was observed.
          - "timeout": deliverables landed but no STATUS: was seen. This is the
            honest raw state (no terminal signal); derive_benchmark_status maps
            deliverable presence to benchmark_status="clean" downstream.
          - "timeout": deadline passed with no deliverables and no STATUS:.

        Opens/reads/closes the DB per iteration — never holds a connection across a
        sleep (one-writer invariant for virtiofs cross-mounts).
        """
        deadline = time.monotonic() + timeout_seconds
        prev_sizes: dict[str, int] | None = None
        while time.monotonic() < deadline:
            # Terminal STATUS: short-circuits with the agent's reported outcome.
            status = self._read_terminal_status(outbound_db_path)
            if status is not None:
                return status
            # Deliverable gate: present and size-stable across two observations.
            if expected_deliverables:
                sizes = self._deliverable_sizes(output_dir, expected_deliverables)
                if sizes is not None and sizes == prev_sizes:
                    return "timeout"
                prev_sizes = sizes
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

        # Step 3 — poll for completion (deliverables landing, or a STATUS: signal)
        end_state = self._poll_for_status(
            outbound_db_path,
            output_dir,
            task_spec.expected_deliverables,
            self.timeout_seconds,
            self.poll_interval,
        )

        # Step 4 — return RunResult
        return RunResult(
            run_id=task_spec.run_id,
            end_state=end_state,
            wall_clock_seconds=time.monotonic() - start,
        )


def _scan_json_result(stdout: str, *required_keys: str) -> dict:
    """Return the first stdout line that parses as a dict with all required_keys.

    The nanoclaw shims emit INFO log lines on stdout alongside their single JSON
    result line, so callers must scan for the result rather than assuming
    stdout is JSON-only (same pattern as NanoclawAdapter._dispatch).
    """
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and all(k in parsed for k in required_keys):
            return parsed
    raise ValueError(
        "nanoclaw shim produced no parseable JSON result line on stdout; "
        f"stdout was:\n{stdout}"
    )


class EphemeralNanoclawAdapter:
    """Adapter that provisions a fresh nanoclaw group per run, then tears it down.

    Each run() creates a throwaway agent group (via the create-lab-group.ts
    shim), delegates execution to a NanoclawAdapter bound to that group, and
    destroys the group afterwards (destroy-lab-group.ts). This gives every run a
    clean session, container filesystem, and memory — no carryover contamination
    from prior tasks, which a reused group would accumulate (nanoclaw uses one
    "agent-shared" session per group).

    Teardown policy:
      - success: always destroy.
      - failure: destroy unless keep_failed=True, which retains the group and its
        session dir for debugging (the orphaned group id is reported on stderr).
    """

    def __init__(
        self,
        nanoclaw_dir: Path,
        timeout_seconds: float = 600.0,
        poll_interval: float = 5.0,
        keep_failed: bool = False,
        name_prefix: str = "lab-eph",
        model: str | None = None,
    ) -> None:
        self.nanoclaw_dir = nanoclaw_dir.expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self.poll_interval = poll_interval
        self.keep_failed = keep_failed
        self.name_prefix = name_prefix
        # None -> the group keeps nanoclaw's default model (model-neutral). A
        # non-claude model is routed to the host Ollama by the create shim.
        self.model = model

    def _create_group(self, name: str) -> str:
        """Create a fresh group via the shim and return its agent group id.

        Passes --model only when a model is configured, so the committed default
        is model-neutral; the operator selects a model (e.g. an Ollama-routed
        one) per run or via env.
        """
        cmd = ["pnpm", "exec", "tsx", "scripts/create-lab-group.ts", "--name", name]
        if self.model:
            cmd += ["--model", self.model]
        result = subprocess.run(
            cmd,
            cwd=self.nanoclaw_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        parsed = _scan_json_result(result.stdout, "groupId")
        return str(parsed["groupId"])

    def _destroy_group(self, group_id: str) -> None:
        """Destroy a group via the shim. Raises CalledProcessError on shim failure."""
        subprocess.run(
            [
                "pnpm",
                "exec",
                "tsx",
                "scripts/destroy-lab-group.ts",
                "--group-id",
                group_id,
            ],
            cwd=self.nanoclaw_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        """Provision a fresh group, run the task on it, then tear it down."""
        name = f"{self.name_prefix}-{uuid.uuid4().hex[:8]}"
        group_id = self._create_group(name)

        failed = False
        try:
            adapter = NanoclawAdapter(
                nanoclaw_dir=self.nanoclaw_dir,
                group_id=group_id,
                timeout_seconds=self.timeout_seconds,
                poll_interval=self.poll_interval,
            )
            return adapter.run(task_spec=task_spec, output_dir=output_dir)
        except Exception:
            failed = True
            raise
        finally:
            if failed and self.keep_failed:
                print(
                    f"[ephemeral] keeping failed group for debugging: {group_id}",
                    file=sys.stderr,
                )
            else:
                try:
                    self._destroy_group(group_id)
                except Exception as exc:  # don't mask a run error; surface orphan
                    # Include the shim's stderr — the exit code alone is not
                    # actionable for diagnosing teardown failures under load.
                    shim_stderr = getattr(exc, "stderr", None)
                    detail = f": {shim_stderr.strip()}" if shim_stderr else ""
                    print(
                        f"[ephemeral] WARNING: failed to destroy group {group_id}; "
                        f"manual cleanup may be needed: {exc}{detail}",
                        file=sys.stderr,
                    )
