# Phase 3: Implement Nanoclaw-LQ Adapter - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 5 new/modified files
**Analogs found:** 4 / 5 (Node shim has no analog in this repo)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `lab_harness_runner/nanoclaw_adapter.py` | service/adapter | request-response + polling | `scripts/fake_run.py` (`FakeAdapter`) | role-match (same protocol; polling loop is new) |
| `scripts/nanoclaw_run.py` | utility/script | request-response | `scripts/fake_run.py` (`main()`) | exact |
| `tests/test_nanoclaw_adapter.py` | test | unit | `tests/test_evaluator.py` | role-match |
| `tests/conftest.py` (extend) | test/fixture | unit | `tests/conftest.py` (existing) | exact (extend, do not replace) |
| `scripts/send-lab-message.ts` (nanoclaw-lq repo) | utility/script | event-driven | **NO ANALOG IN THIS REPO** — see "No Analog Found" section | — |

---

## Pattern Assignments

### `lab_harness_runner/nanoclaw_adapter.py` (service/adapter, request-response + polling)

**Analog:** `scripts/fake_run.py` — `FakeAdapter` class (lines 64–81) for the class shape; `lab_harness_runner/evaluator.py` (lines 1–68) for the subprocess dispatch pattern; `lab_harness_runner/task_reader.py` (lines 10–19) for path validation.

**Imports pattern** — copy from `scripts/fake_run.py` lines 9–27 and `lab_harness_runner/evaluator.py` lines 1–6:

```python
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

from lab_harness_runner.adapter import TaskSpec, RunResult
from lab_harness_runner.task_reader import _reject_unsafe_relative_path
```

**Class constructor pattern** — mirrors `FakeAdapter` (fake_run.py line 64) with added `__init__` taking nanoclaw-specific config:

```python
class NanoclawAdapter:
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
```

**Core `run()` pattern** — copy `FakeAdapter.run()` signature from `scripts/fake_run.py` lines 65–81; replace body with the four-step sequence (mounts → dispatch → poll → result):

```python
    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        start = time.monotonic()
        # 1. Configure additional_mounts in nanoclaw container_configs DB
        # 2. Dispatch: subprocess → pnpm exec tsx scripts/send-lab-message.ts
        # 3. Poll outbound.db for STATUS: signal
        # 4. Return RunResult
        return RunResult(
            run_id=task_spec.run_id,
            end_state=end_state,
            wall_clock_seconds=time.monotonic() - start,
        )
```

**Subprocess dispatch pattern** — copy from `lab_harness_runner/evaluator.py` lines 38–66 (explicit list form, `check=True`, `capture_output=True`, `cwd`, re-raise `CalledProcessError` with stdout/stderr preserved):

```python
# evaluator.py lines 38-66 — copy this exact structure for the Node shim dispatch
try:
    subprocess.run(
        [
            "pnpm",
            "exec",
            "tsx",
            "scripts/send-lab-message.ts",
            "--group-id", self.group_id,
            "--message-id", msg_id,
            "--content", content_json,
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
```

**Outbound DB polling pattern** — from RESEARCH.md Pattern 2 (sourced from nanoclaw-lq `schema.ts` + `test-v2-host.ts` open/close-per-op invariant). Critical: open → read → close per iteration; never hold a persistent connection:

```python
def _poll_for_status(
    self,
    outbound_db_path: Path,
    timeout_seconds: float,
    poll_interval: float,
) -> str:
    """Poll outbound.db messages_out for a STATUS: line. Returns end_state."""
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
                    status = text[len("STATUS:"):].strip().upper()
                    return "clean" if status == "DONE" else "agent_error"
        except Exception:
            pass  # DB not yet created; container not yet started — retry
        time.sleep(poll_interval)
    return "timeout"
```

**Path validation pattern** — copy from `lab_harness_runner/task_reader.py` lines 10–19 (apply to `group_id` and any session-relative paths):

```python
# task_reader.py lines 10-19 — reuse directly; import from lab_harness_runner.task_reader
_reject_unsafe_relative_path(group_id, "group_id")
```

**Inbound message footer pattern** — from RESEARCH.md Pattern 4 (D-04/D-05). Append to `task_spec.instructions` before serialising to JSON:

```python
FOOTER_TEMPLATE = """\n\n---\nOUTPUT DIRECTORY: Write all deliverable files to /workspace/extra/lab-output/\nREQUIRED FILES: {filenames}\nCOMPLETION SIGNAL: When all files are written, emit exactly: STATUS: DONE\nIf you encounter an unrecoverable error, emit exactly: STATUS: ERROR\nDo not emit STATUS: until all files are fully written.\n"""

def _build_message_content(self, task_spec: TaskSpec) -> str:
    filenames = ", ".join(task_spec.expected_deliverables)
    text = task_spec.instructions + FOOTER_TEMPLATE.format(filenames=filenames)
    return json.dumps({"sender": "system", "senderId": "system", "text": text})
```

**RunResult population** — copy from `scripts/fake_run.py` lines 77–81; `end_state` is one of `"clean"`, `"agent_error"`, `"timeout"` — validated by `RunResult.__post_init__` in `lab_harness_runner/adapter.py` lines 40–45:

```python
return RunResult(
    run_id=task_spec.run_id,
    end_state=end_state,          # from _poll_for_status()
    wall_clock_seconds=time.monotonic() - start,
)
```

---

### `scripts/nanoclaw_run.py` (utility/script, request-response)

**Analog:** `scripts/fake_run.py` — `main()` function (lines 84–142). Copy verbatim, replacing `FakeAdapter` with `NanoclawAdapter` and adding `--nanoclaw-dir` and `--group-id` args.

**Imports pattern** — copy from `scripts/fake_run.py` lines 9–27; replace the `FakeAdapter` import with `NanoclawAdapter`:

```python
from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from lab_harness_runner import (
    build_result_dir,
    read_task,
    score_run,
    write_metrics,
)
from lab_harness_runner.task_reader import _lab_path, _reject_unsafe_relative_path
from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter
```

**CLI arg pattern** — copy from `scripts/fake_run.py` lines 85–103; add two nanoclaw-specific args:

```python
parser.add_argument("--task", required=True, help="area/slug task path")
parser.add_argument("--run-id", default=None, help="explicit run ID (default: uuid4)")
parser.add_argument("--lab-path", default=None, help="explicit LAB root")
parser.add_argument("--score", action="store_true", help="invoke LAB evaluator after run")
parser.add_argument("--judge-model", default="claude-sonnet-4-6", help="judge model name")
# nanoclaw-specific:
parser.add_argument("--nanoclaw-dir", required=True, help="path to nanoclaw-lq repo root")
parser.add_argument("--group-id", required=True, help="nanoclaw agent group ID for LAB runs")
parser.add_argument("--timeout", type=float, default=600.0, help="poll timeout in seconds")
```

**Path validation pattern** — copy from `scripts/fake_run.py` lines 105–107:

```python
_reject_unsafe_relative_path(args.task, "--task")
if args.run_id is not None:
    _reject_unsafe_relative_path(args.run_id, "--run-id")
_reject_unsafe_relative_path(args.group_id, "--group-id")
```

**End-to-end wiring pattern** — copy from `scripts/fake_run.py` lines 109–138 (read_task → build_result_dir → adapter.run → write_metrics → optional score_run); only `adapter =` line changes:

```python
run_id = args.run_id or str(uuid.uuid4())
lab_path = Path(args.lab_path).expanduser().resolve() if args.lab_path else _lab_path()

task_spec = read_task(lab_path=lab_path, task_id=args.task, run_id=run_id)
run_dir, output_dir = build_result_dir(lab_path=lab_path, run_id=run_id)

adapter = NanoclawAdapter(
    nanoclaw_dir=Path(args.nanoclaw_dir),
    group_id=args.group_id,
    timeout_seconds=args.timeout,
)
result = adapter.run(task_spec=task_spec, output_dir=output_dir)

write_metrics(run_dir=run_dir, result=result)
```

**`if __name__ == "__main__"` guard** — copy exactly from `scripts/fake_run.py` lines 141–142:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

---

### `tests/test_nanoclaw_adapter.py` (test, unit)

**Analog:** `tests/test_evaluator.py` — structure and `patch`/`MagicMock` pattern (lines 1–30); `tests/conftest.py` — `tmp_lab` fixture pattern (lines 12–51).

**Imports pattern** — copy from `tests/test_evaluator.py` lines 1–7:

```python
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
```

**Synthetic outbound.db fixture pattern** — new fixture needed; modeled on `tests/conftest.py` `tmp_lab` fixture (lines 12–51). Create a real SQLite file in `tmp_path` with the `messages_out` schema from RESEARCH.md Pattern 2:

```python
# Add to tests/conftest.py or tests/test_nanoclaw_adapter.py
@pytest.fixture()
def outbound_db(tmp_path: Path) -> Path:
    """Create a synthetic outbound.db with messages_out table in a temp session dir."""
    session_dir = tmp_path / "sessions" / "ag-test" / "sess-test"
    session_dir.mkdir(parents=True)
    db_path = session_dir / "outbound.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE messages_out (seq INTEGER PRIMARY KEY, content TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    return db_path
```

**Unit test pattern** — copy structure from `tests/test_evaluator.py` test functions (lines 9–44): import inside test, arrange/act/assert, assert specific values:

```python
def test_poll_status_done_returns_clean(outbound_db: Path):
    """STATUS: DONE in messages_out → end_state 'clean'."""
    from lab_harness_runner.nanoclaw_adapter import NanoclawAdapter

    conn = sqlite3.connect(str(outbound_db))
    conn.execute(
        "INSERT INTO messages_out (content) VALUES (?)",
        (json.dumps({"text": "STATUS: DONE"}),),
    )
    conn.commit()
    conn.close()

    adapter = NanoclawAdapter.__new__(NanoclawAdapter)
    result = adapter._poll_for_status(outbound_db, timeout_seconds=5.0, poll_interval=0.1)
    assert result == "clean"


def test_poll_status_error_returns_agent_error(outbound_db: Path): ...
def test_poll_timeout_returns_timeout(outbound_db: Path): ...
def test_poll_missing_db_does_not_raise(tmp_path: Path): ...
```

**subprocess mock pattern** — copy from `tests/test_evaluator.py` lines 17–27 for dispatch subprocess tests:

```python
with patch("lab_harness_runner.nanoclaw_adapter.subprocess.run") as mock_run:
    mock_run.return_value = MagicMock(returncode=0)
    ...
mock_run.assert_called_once()
cmd = mock_run.call_args[0][0]
assert "send-lab-message.ts" in cmd
```

---

### `tests/conftest.py` (extend existing — do not replace)

**Analog:** `tests/conftest.py` (lines 1–68) — existing file. Extend by appending the `outbound_db` fixture shown above. Do not modify existing `tmp_lab` or `sample_run_result` fixtures.

**File path:** `/Users/houfu/Projects/lab-harness-runner/tests/conftest.py`

Read lines 1–68 first (already done in this session). Append after line 68:

```python
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
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every existing module in `lab_harness_runner/` (e.g., `adapter.py` line 1, `evaluator.py` line 1).
**Apply to:** All new `.py` files (`nanoclaw_adapter.py`, `nanoclaw_run.py`, test files).

```python
from __future__ import annotations
```

### Path Validation (`_reject_unsafe_relative_path`)
**Source:** `lab_harness_runner/task_reader.py` lines 10–19; imported in `evaluator.py` line 6, `result_builder.py` line 4, `scripts/fake_run.py` line 27.
**Apply to:** All user-supplied path-like arguments (`group_id`, `session_id`, `--task`, `--run-id`, `--group-id`).

```python
# Import — copy this import line:
from lab_harness_runner.task_reader import _reject_unsafe_relative_path

# Usage — call before any path construction:
_reject_unsafe_relative_path(value, "argument-name")
```

### Subprocess Invocation (explicit list, `check=True`, `cwd`, `capture_output`)
**Source:** `lab_harness_runner/evaluator.py` lines 38–66.
**Apply to:** The Node shim dispatch call in `NanoclawAdapter.run()`.

```python
subprocess.run(
    [...],            # explicit list — never shell=True
    cwd=self.nanoclaw_dir,
    check=True,
    capture_output=True,
    text=True,
)
```

### SQLite Open/Close Per Operation (one-writer invariant)
**Source:** RESEARCH.md Pattern 2 and nanoclaw-lq `session-manager.ts` lines 1–12 (cross-mount invariants).
**Apply to:** All SQLite access in `nanoclaw_adapter.py` (both mount-config writes and outbound.db polling).

```python
# CORRECT — open, operate, close
conn = sqlite3.connect(str(db_path))
rows = conn.execute("SELECT ...").fetchall()
conn.close()

# WRONG — do not do this
conn = sqlite3.connect(str(db_path))
# ... use conn across multiple calls or across a sleep ...
```

### `RunResult` Population
**Source:** `scripts/fake_run.py` lines 77–81; `lab_harness_runner/adapter.py` lines 28–45 (`__post_init__` validates `end_state`).
**Apply to:** The return statement in `NanoclawAdapter.run()`.

```python
return RunResult(
    run_id=task_spec.run_id,
    end_state=end_state,   # must be "clean", "agent_error", or "timeout"
    wall_clock_seconds=time.monotonic() - start,
)
```

### `main()` + `if __name__ == "__main__": raise SystemExit(main())` guard
**Source:** `scripts/fake_run.py` lines 84, 141–142.
**Apply to:** `scripts/nanoclaw_run.py`.

```python
def main() -> int:
    ...
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/send-lab-message.ts` (in nanoclaw-lq repo) | utility/script | event-driven (Node/TypeScript) | No TypeScript files exist in this repo. The closest reference is `nanoclaw-lq/scripts/test-v2-host.ts` (lines 1–139) which shows the full pattern: import `resolveSession` + `writeSessionMessage` from `../src/session-manager.js`, call them in sequence, then call `wakeContainer` from `../src/container-runner.js`. Planner should use RESEARCH.md Pattern 1 (adapter class shape) and the `test-v2-host.ts` reference at `/Users/houfu/Projects/nanoclaw-lq/scripts/test-v2-host.ts` lines 72–96 as the implementation template. |

**Node shim implementation guide for planner** (from `test-v2-host.ts` lines 72–96 and session-manager.ts lines 92–133, 193–238):

```typescript
// scripts/send-lab-message.ts (nanoclaw-lq repo)
// Key imports mirrored from test-v2-host.ts lines 23-27:
import { resolveSession, writeSessionMessage } from '../src/session-manager.js';
import { wakeContainer } from '../src/container-runner.js';
// Sequence:
// 1. resolveSession(groupId, null, null, 'agent-shared') → { session }
// 2. writeSessionMessage(groupId, session.id, { id, kind: 'chat', timestamp, content })
// 3. wakeContainer(session)
// Print session.id to stdout so Python adapter can capture it
```

CLI args consumed by the shim (Python adapter passes via `subprocess.run` arg list):
- `--group-id` (required)
- `--message-id` (required; Python generates with `str(uuid.uuid4())`)
- `--content` (required; JSON string matching shape `{"sender":"system","senderId":"system","text":"..."}`)

---

## Metadata

**Analog search scope:** `lab_harness_runner/`, `scripts/`, `tests/`
**Files scanned:** 9 source files, 5 test files
**Pattern extraction date:** 2026-05-31
