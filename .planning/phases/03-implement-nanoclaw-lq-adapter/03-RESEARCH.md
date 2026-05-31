# Phase 3: Implement Nanoclaw-LQ Adapter - Research

**Researched:** 2026-05-31
**Domain:** nanoclaw-lq dispatch surface, session/container lifecycle, mount wiring, completion signaling
**Confidence:** HIGH (all findings verified by direct source inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Primary dispatch path is to **shell out to a nanoclaw CLI** that uses nanoclaw's own session-manager API to enqueue the inbound task message. The adapter does not write `inbound.db` directly on the happy path.
- **D-02:** **Research must verify** that nanoclaw exposes a suitable CLI/command for enqueuing an inbound `messages_in` message.
- **D-03:** **Fallback policy — block and report.** If research finds no suitable CLI, STOP and surface the finding to the user. Do NOT auto-select direct SQLite writes or a Node shim.
- **D-04:** Inbound message content = instructions + explicit output contract (exact output path + expected deliverable filenames from `TaskSpec.expected_deliverables`).
- **D-05:** Footer also states the completion-signal protocol — the same message footer instructs the agent to emit `STATUS: DONE` when finished.

### Claude's Discretion
- Exact CLI command name/flags to call once research confirms the surface.
- Footer wording/format for the output contract and `STATUS:` instruction.
- Which specific LAB task to use as the single-task proof for the exit criterion.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Direct SQLite write and a Node `send-message` shim are not deferred *ideas* but deferred *fallback decisions* gated on research per D-03.)
</user_constraints>

---

## Summary

This phase builds the first real adapter for lab-harness-runner: a Python class satisfying
`Adapter.run(task_spec, output_dir) -> RunResult` that dispatches a Harvey LAB task into
nanoclaw-lq's Docker container, wires document/output mounts, waits for a terminal STATUS:
signal with a wall-clock timeout, and returns a `RunResult`.

**The single most important finding from research is the dispatch CLI verdict below.** The
`ncl` CLI exists and is well-structured, but it communicates with a running nanoclaw *daemon*
via a Unix socket (`data/ncl.sock`). There is NO nanoclaw CLI command that can (a) create a
session and (b) enqueue an inbound message as a standalone one-shot operation without the
daemon running. The closest operations (session create, message enqueue) are not exposed in
the `ncl` CLI at all — sessions are created automatically by the router when a message
arrives, and message delivery goes through the running router, not through a standalone CLI
write. D-03 is therefore triggered: the user must decide the dispatch path before planning
proceeds. Three concrete options are documented in "Open Questions" below.

Despite this blocker, all other research questions (mounts, completion, briefing, proof task)
are fully resolved at HIGH confidence and are documented here so planning can proceed
immediately once the user makes the dispatch decision.

**Primary recommendation:** Present the dispatch gap to the user with three options (thin
Node shim, direct SQLite write, or use the existing `_ping-test` / `main` group's socket).
Do not auto-select. The rest of the plan is fully ready to execute on whichever option is
chosen.

---

## DISPATCH CLI VERDICT (CRITICAL — READ FIRST)

**Status: NO SUITABLE CLI EXISTS. D-03 BLOCK APPLIES.**

[VERIFIED: direct source inspection of `/Users/houfu/Projects/nanoclaw-lq`]

### What was confirmed

The `ncl` binary (`bin/ncl` → `src/cli/client.ts`) exists and is a real CLI that sends
JSON frames over a Unix socket (`data/ncl.sock`) to the running nanoclaw daemon. It supports:

- `ncl groups list/get` — inspect groups
- `ncl groups create` — create a group (requires `approval` access — only works while daemon
  is running, and the operation gates behind approval in the socket dispatch)
- `ncl groups config get/update` — read/write container config (incl. `additional_mounts`)
- `ncl sessions list/get` — read sessions (no `create` operation)
- **No `sessions create` command exists.** Sessions are created automatically by
  `src/router.ts → resolveSession()` when a message arrives and is routed.
- **No `messages send` or `sessions enqueue` command exists.** There is no CLI command
  that writes a row into `messages_in`.

### How messages actually flow (verified)

```
Channel message arrives
  → src/router.ts routeInbound()
      → resolveSession()        # creates session if needed, init inbound.db/outbound.db
      → writeSessionMessage()   # inserts row into messages_in
      → wakeContainer()         # spawns docker container for this session
          → container polls inbound.db
          → agent processes message
          → agent writes to outbound.db messages_out
```

The `ncl` CLI, when used by a human host, sends a frame to the daemon over `data/ncl.sock`;
the daemon then calls `dispatch()` which executes the registered command handler. For session
commands, only `list` and `get` are registered (source: `src/cli/resources/sessions.ts`).
For groups, `create` requires `approval` access which gates behind the daemon's approval
system even from the host socket.

### Three dispatch paths available (for user decision)

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A — Thin Node shim** | Write `scripts/send-lab-message.ts` that imports `session-manager.ts` directly, calls `resolveSession()` + `writeSessionMessage()` + `wakeContainer()`, then exits. The Python adapter shells out to it via `subprocess`. | Uses nanoclaw's own API surface; honors one-writer invariant; clean | Requires adding one script to nanoclaw-lq repo (contradicts "unmodified dep" goal) |
| **B — Direct SQLite write** | Python adapter writes to `inbound.db` directly using Python's built-in `sqlite3` module, respecting the one-writer invariant (open, write, close per op; DELETE journal mode). Session row and folder must be pre-created or the adapter must also call `resolveSession()` somehow. | No Node dep from Python adapter | Bypasses nanoclaw's API; must manually reproduce schema; fragile against nanoclaw schema changes |
| **C — Re-use existing group + CLI socket** | Use an existing wired group (e.g. `_ping-test` or `main`) and send a message via `data/cli.sock` (the chat-style socket that `scripts/chat.ts` uses). The daemon routes the message, creates a session, wakes container. Python adapter writes JSON to the socket. | No new files; daemon handles session/wake | The cli.sock is the interactive chat channel; would mix LAB tasks into normal conversation history; no clean session isolation per task |

**D-03 blocks the plan. User must select Option A, B, or C (or a new option) before
planning proceeds.**

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Task dispatch (enqueue inbound message) | Adapter (Python) | nanoclaw daemon (Node) | Adapter drives the dispatch; nanoclaw receives and queues it |
| Session/container lifecycle | nanoclaw daemon | — | Sessions created by router; containers spawned by container-runner |
| Mount configuration | nanoclaw container config DB | Adapter (writes config before spawn) | `additional_mounts` stored in `container_configs` table; adapter must pre-configure |
| Agent execution | nanoclaw Docker container | — | Agent runs inside container, polls inbound.db |
| Completion signaling | Agent (writes to outbound.db) | Adapter (polls outbound.db) | Agent writes messages_out; adapter reads them looking for STATUS: |
| Deliverable output | Agent (writes to lab-output mount) | — | Agent writes files to `/workspace/extra/lab-output` inside container |
| Result validation | Adapter → evaluator.py | — | Adapter confirms files exist, then calls LAB evaluator |
| Metrics capture | Adapter | metrics.py | Adapter populates RunResult; metrics.py serializes to metrics.json |

---

## Standard Stack

### Core (No New Python Dependencies Required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib | Read nanoclaw's `outbound.db` to detect STATUS: signal | Built-in; nanoclaw uses SQLite; no dep install needed |
| `subprocess` | stdlib | Shell out to dispatch mechanism (Node shim or ncl) | Established pattern in Phase 2 evaluator.py |
| `threading` / `time` | stdlib | Wall-clock timeout + polling loop | No external dep needed for simple polling |
| `pathlib` | stdlib | Path manipulation for mounts and session dirs | Already used throughout the codebase |

### Supporting (Only if Option A is chosen)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pnpm exec tsx` | (nanoclaw's pnpm) | Execute Node shim from Python via subprocess | Option A only |

**Installation:** No new Python packages needed. The adapter uses only stdlib.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib sqlite3 polling | asyncio + aiosqlite | No benefit for simple polling; sqlite3 is simpler and avoids new dep |
| polling outbound.db | watching heartbeat file | Heartbeat is liveness only; outbound.db content carries STATUS: string |

---

## Package Legitimacy Audit

No new packages are being installed in this phase. The adapter uses Python stdlib only.
If Option A is chosen, the nanoclaw-lq repo's existing pnpm/tsx/better-sqlite3 stack is used
with no additions.

**Packages removed due to slopcheck:** none (no packages to install)

---

## Architecture Patterns

### System Architecture Diagram

```
Python Adapter (NanoclawAdapter.run)
    │
    ├─[pre-flight]──► Update container_configs.additional_mounts in nanoclaw's DB
    │                   (documents dir → /workspace/extra/lab-documents, RO)
    │                   (output dir → /workspace/extra/lab-output, RW)
    │                   Requires mount-allowlist.json to include harvey-labs paths
    │
    ├─[dispatch]────► Choice depends on D-03 user decision:
    │                 A: subprocess → pnpm exec tsx scripts/send-lab-message.ts
    │                 B: direct sqlite3 write → inbound.db messages_in
    │                 C: write to cli.sock (chat socket)
    │                     ↓
    │                 nanoclaw daemon receives message
    │                     ↓
    │                 resolveSession() → creates session folder + inbound.db + outbound.db
    │                 writeSessionMessage() → inserts row in messages_in
    │                 wakeContainer() → docker run ... with mounts
    │
    ├─[poll loop]───► Read outbound.db messages_out every N seconds
    │                   (open readonly, scan content JSON for "STATUS:" prefix, close)
    │                   Wall-clock timeout: raise timeout if exceeded
    │                   On STATUS: DONE → end_state = "clean"
    │                   On STATUS: ERROR → end_state = "agent_error"
    │                   On timeout → end_state = "timeout"
    │
    └─[result]──────► Return RunResult(run_id, end_state, wall_clock_seconds)
                      Files in output_dir are ready for evaluator.py
```

### Recommended Project Structure

```
lab_harness_runner/
├── adapter.py           # existing: TaskSpec, RunResult, Adapter protocol
├── evaluator.py         # existing: score_run()
├── metrics.py           # existing: write_metrics()
├── result_builder.py    # existing: build_result_dir()
├── task_reader.py       # existing: read_task(), _lab_path()
└── nanoclaw_adapter.py  # NEW: NanoclawAdapter class (this phase)

scripts/
├── fake_run.py          # existing: FakeAdapter end-to-end wiring
├── nanoclaw_run.py      # NEW: real nanoclaw run script (mirrors fake_run.py)
└── send-lab-message.ts  # NEW (Option A only, in nanoclaw-lq repo): thin Node shim
```

### Pattern 1: Adapter Class Shape

The adapter follows the same structural pattern as `FakeAdapter` in `fake_run.py`:

```python
# Source: scripts/fake_run.py — FakeAdapter class pattern
import time
import sqlite3
from pathlib import Path

from lab_harness_runner.adapter import TaskSpec, RunResult

class NanoclawAdapter:
    def __init__(self, nanoclaw_dir: Path, group_id: str, session_id: str | None = None):
        self.nanoclaw_dir = nanoclaw_dir
        self.group_id = group_id
        self._session_id = session_id  # resolved at dispatch time

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        start = time.monotonic()
        # 1. Configure mounts (additional_mounts in container_configs)
        # 2. Dispatch task message
        # 3. Poll outbound.db for STATUS: signal
        # 4. Return RunResult
        ...
```

### Pattern 2: Outbound DB Polling

[VERIFIED: direct inspection of `/Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts` lines 222-235]

```python
# Source: schema.ts OUTBOUND_SCHEMA — messages_out table shape
# content column is JSON: {"text": "...", ...}
import sqlite3
import json
import time

def poll_for_status(outbound_db_path: Path, timeout_seconds: float, poll_interval: float = 2.0) -> str:
    """Poll outbound.db for a STATUS: line. Returns end_state string."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            conn = sqlite3.connect(str(outbound_db_path), uri=True)  # open, read, close
            rows = conn.execute("SELECT content FROM messages_out ORDER BY seq").fetchall()
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
            pass  # DB not yet created; container not yet started
        time.sleep(poll_interval)
    return "timeout"
```

**Critical SQLite constraint:** Open, read, close per poll. Do NOT hold a persistent
connection. [VERIFIED: `session-manager.ts` comment: "Host opens-writes-CLOSES per op —
close invalidates the container's page cache; a long-lived connection freezes its view."]
While the container is the writer of `outbound.db`, the host must still close quickly to
avoid any contention on macOS virtiofs mounts.

### Pattern 3: Mount Configuration

[VERIFIED: `src/container-config.ts` lines 26-29, `src/modules/mount-security/index.ts`]

`additional_mounts` is a JSON array stored in the `container_configs` table. It is
materialized into `groups/<folder>/container.json` at every container spawn. The mount
security module validates each entry against `~/.config/nanoclaw/mount-allowlist.json`
before passing them to Docker.

**The mount-allowlist.json currently has empty `allowedRoots`.** This means the Harvey LAB
paths must be added to the allowlist before any additional mounts will work.

The adapter needs to:
1. Add Harvey LAB paths to `mount-allowlist.json` (one-time setup, human task)
2. Update `container_configs.additional_mounts` for the target group before spawning

The validated container path for an additional mount is assembled as:
`/workspace/extra/<containerPath>` where `containerPath` is the `basename(hostPath)` if not
specified, or the explicit `containerPath` field.

Example `additional_mounts` entry for the adapter to configure:

```json
[
  {
    "hostPath": "/Users/houfu/Projects/harvey-labs/tasks/corporate-ma/compare-matter-plan-against-engagement-letter/documents",
    "containerPath": "lab-documents",
    "readonly": true
  },
  {
    "hostPath": "/Users/houfu/Projects/harvey-labs/results/<run-id>/output",
    "containerPath": "lab-output",
    "readonly": false
  }
]
```

This makes the agent see:
- `/workspace/extra/lab-documents/` — task documents (RO)
- `/workspace/extra/lab-output/` — deliverable output (RW)

[VERIFIED: `container/agent-runner/src/index.ts` lines 56-68 — agent runner discovers these
at `/workspace/extra/*` and passes them to the provider as `additionalDirectories`]

### Pattern 4: Inbound Message Content (D-04/D-05)

The inbound message `content` column is JSON. Based on `formatMessages()` in
`container/agent-runner/src/formatter.ts`, the agent reads messages via the poll-loop
which formats them as XML prompt input. The content JSON shape observed in existing tests is:

```json
{
  "sender": "system",
  "senderId": "system",
  "text": "<task instructions and footer>"
}
```

The footer (D-04/D-05) appended to `TaskSpec.instructions` should be:

```
---
OUTPUT DIRECTORY: Write all deliverable files to /workspace/extra/lab-output/
REQUIRED FILES: <filename1>, <filename2>
COMPLETION SIGNAL: When all files are written, emit exactly: STATUS: DONE
If you encounter an unrecoverable error, emit exactly: STATUS: ERROR
Do not emit STATUS: until all files are fully written.
```

### Pattern 5: Agent Message Output Structure

[VERIFIED: `container/agent-runner/src/poll-loop.ts` lines 494-533]

The agent's text output must be wrapped in `<message to="name">...</message>` blocks for
delivery. For a CLI-channel session, the destination name will be whatever is in the
`destinations` table of `inbound.db`. For a freshly-created session with no wiring, there
may be no registered destination, in which case the agent's output goes to scratchpad.

**Implication for D-04/D-05:** The STATUS: signal in the message footer should instruct the
agent to emit `STATUS: DONE` as plain text (which nanoclaw will write to outbound.db
regardless of message wrapping). The adapter polls outbound.db for any `messages_out` row
whose `content.text` starts with `STATUS:`.

### Anti-Patterns to Avoid

- **Long-lived sqlite3 connections:** Do not hold a connection to `inbound.db` or
  `outbound.db` open. Open, operate, close per call — the one-writer invariant requires this
  and the Docker virtiofs page cache depends on it.
- **Writing to inbound.db from Python without resolveSession:** The session folder and both
  DBs must already exist. If Option B (direct SQLite) is chosen, the adapter must ensure
  `initSessionFolder()` semantics are reproduced (create folder, `ensureSchema()` both DBs).
- **Assuming additional mounts appear without allowlist entry:** The mount security module
  silently drops any mount whose hostPath is not under an `allowedRoot`. Without updating
  `~/.config/nanoclaw/mount-allowlist.json`, no mounts appear in the container.
- **Relying on group briefing for task contract:** The CLAUDE.md is composed from fragments
  at spawn time. It does not carry per-task instructions. The D-04/D-05 footer in the inbound
  message must be fully self-contained.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQLite journal safety | Custom SQLite wrapper | Python stdlib `sqlite3` with open/close per op | nanoclaw's invariant is open/write/close; no extra abstraction needed |
| Docker mount argument construction | String-building mount args | nanoclaw's `validateAdditionalMounts()` | Mount security module does path validation + `/workspace/extra/` prefixing |
| Session ID generation | Custom UUID logic | nanoclaw generates session ID in `generateId()` | Session creation is nanoclaw's job; adapter only needs to know the session ID |
| Wall-clock timeout | Thread + exception | `time.monotonic()` deadline loop | Simple and matches how `scripts/test-v2-host.ts` does it |

---

## Completion Signaling

[VERIFIED: `src/db/schema.ts` lines 222-235; `container/agent-runner/src/poll-loop.ts` lines 443-453]

### How the agent emits a STATUS: signal

The agent writes to `outbound.db → messages_out` via `writeMessageOut()`. Each row has a
`content` column (JSON, shape: `{"text": "...", ...}`). The poll-loop dispatches the agent's
result text to `writeMessageOut()` after the provider's `result` event fires.

The adapter should scan all `messages_out` rows (ordered by `seq`) looking for a row where
`JSON.parse(content).text.startsWith("STATUS:")`.

### End-state mapping

| `messages_out` content text | `RunResult.end_state` |
|----------------------------|-----------------------|
| starts with `STATUS: DONE` | `"clean"` |
| starts with `STATUS: ERROR` | `"agent_error"` |
| Poll times out | `"timeout"` |
| Container exits before STATUS: | `"agent_error"` |

### Timeout value

Left to Claude's discretion per CONTEXT.md. Recommendation: **600 seconds (10 minutes)**
for LAB tasks, configurable via constructor arg or environment variable. Rationale: LAB tasks
involve legal document drafting which can take several minutes; the existing test in
`scripts/test-v2-host.ts` uses 120 seconds for a trivial "say three words" task.

### Poll interval

Recommendation: **5 seconds**. The agent runner polls `inbound.db` at 1-second intervals;
a 5-second host poll is low overhead and catches completion within 5 seconds of it being
written.

---

## Briefing and Group Strategy

[VERIFIED: `src/claude-md-compose.ts` lines 1, 48, 119; `docs/verified-contracts.md`]

### Verdict: Self-contained inbound message footer (D-04/D-05) is the lowest-friction path

Three options existed; the D-04/D-05 decision already locked the footer approach.

**Dedicated LAB group (Option 1):**
- Create `groups/lab-runner/` with `CLAUDE.local.md` containing LAB-specific instructions
- Register via `scripts/init-first-agent.ts` or direct DB + `initGroupFilesystem()` call
- Pro: persistent LAB context; Con: requires agent group in nanoclaw DB + folder
- Status: valid but requires group creation (which needs daemon running + approval)

**Footer-only approach (D-04/D-05 — recommended):**
- Put all task context in the inbound message itself
- The existing group (`_ping-test` / `main`) is used as the container runtime
- CLAUDE.md from the group provides base capabilities; footer provides task contract
- Pro: no new group needed; Con: base CLAUDE.md affects agent behavior (e.g. existing
  groups may have unexpected tools/restrictions)

**Finding:** The `_ping-test` group's `container.json` shows it uses Ollama locally (not
Anthropic API) and has `blockedHosts: ["api.anthropic.com"]`. Using this group for LAB
tasks requires the LAB task to be doable with the configured model. The `main` group may
be better if it uses Anthropic Claude. The planner should recommend using the `main` group
or a dedicated new group with the Anthropic provider.

---

## Single-Task Proof

[VERIFIED: direct inspection of `/Users/houfu/Projects/harvey-labs/tasks/`]

**Recommended proof task:** `corporate-ma/compare-matter-plan-against-engagement-letter`

| Property | Value |
|----------|-------|
| Task ID | `corporate-ma/compare-matter-plan-against-engagement-letter` |
| Title | Compare Matter Plan against Engagement Letter — Discrepancy Analysis Memorandum |
| Instructions | Inline in `task.json` (not in separate `instructions.md`) |
| Documents | 2 files: `engagement-letter.docx`, `matter-plan.docx` |
| Expected deliverable | `discrepancy-analysis-memo.docx` (single file) |
| Number of criteria | 33 |
| Documents directory | `/Users/houfu/Projects/harvey-labs/tasks/corporate-ma/compare-matter-plan-against-engagement-letter/documents/` |

**Why this task:**
- Single deliverable (.docx) — minimal surface for the exit criterion
- Has real documents to mount (validates the mount wiring)
- 33 criteria — substantial enough to be a real LAB task; not trivially short
- Self-contained instructions in `task.json` (no `instructions.md` fallback needed)

**Exit criterion validation:** After the adapter runs, confirm
`results/<run-id>/output/discrepancy-analysis-memo.docx` exists and is non-zero bytes.

---

## Common Pitfalls

### Pitfall 1: Empty mount-allowlist blocks all additional mounts silently

**What goes wrong:** The adapter configures `additional_mounts` in the DB correctly, but no
mounts appear in the container. The agent cannot find documents or write output.

**Why it happens:** `~/.config/nanoclaw/mount-allowlist.json` has `allowedRoots: []` (confirmed
on this machine). `validateAdditionalMounts()` blocks all mounts when no allowedRoot matches.
The blockage is logged at WARN level by the nanoclaw daemon but not surfaced to the adapter.

**How to avoid:** Wave 0 setup task must add Harvey LAB paths to `mount-allowlist.json`:
```json
{
  "allowedRoots": [
    {
      "path": "/Users/houfu/Projects/harvey-labs",
      "allowReadWrite": true,
      "description": "Harvey LAB tasks and results"
    }
  ],
  "blockedPatterns": []
}
```

**Warning signs:** Container starts, polls, agent reports no documents found.

### Pitfall 2: Session has no destination — agent output goes to scratchpad

**What goes wrong:** Agent generates the correct output but the STATUS: message never
appears in `outbound.db` because it was treated as scratchpad (bare text outside
`<message to="name">` blocks).

**Why it happens:** The poll-loop's `dispatchResultText()` requires `<message to="name">`
wrapping. The `destinations` table in `inbound.db` maps destination names to channels.
A freshly-created session with no registered messaging group has no named destination, so
the agent cannot route its output.

**How to avoid:** The D-05 footer must instruct the agent explicitly:
- Emit `STATUS: DONE` as plain text (not inside a message block)
- Or: ensure the session has a wired destination so the agent can route output

**Deeper issue:** For Option A/B (programmatic session creation without the router), there
is no messaging group wired, so `session_routing` and `destinations` tables will be empty.
The adapter needs to write a dummy destination into `inbound.db` after session creation
so the agent knows where to send its output.

### Pitfall 3: `additional_mounts` containerPath must be relative (not absolute)

**What goes wrong:** Adapter writes `containerPath: "/workspace/extra/lab-output"` (absolute)
into the DB; `validateMount()` rejects it.

**Why it happens:** `isValidContainerPath()` rejects paths starting with `/`. The validated
path is assembled as `/workspace/extra/<containerPath>` by the security module.

**How to avoid:** Always use bare names: `"containerPath": "lab-documents"` not
`"/workspace/extra/lab-documents"`.

### Pitfall 4: Mount config takes effect only on next container spawn

**What goes wrong:** Adapter updates `additional_mounts` in the DB but the running container
doesn't see the new mounts.

**Why it happens:** `materializeContainerJson()` is called at spawn time. A running container
has already been given its mounts at docker run. Mount changes require a container restart
(kill + respawn).

**How to avoid:** The adapter must configure `additional_mounts` BEFORE the session is
created/container is woken. The sequence is: (1) set mounts, (2) create session + message,
(3) wake container — not the other way around.

### Pitfall 5: outbound.db doesn't exist until the container starts

**What goes wrong:** Adapter immediately polls `outbound.db` after dispatch and gets
`FileNotFoundError`.

**Why it happens:** `initSessionFolder()` creates both `inbound.db` and `outbound.db`, but
if the session is created by the router-based path, the container runner initializes them
at spawn time. There is a window between message dispatch and container start.

**How to avoid:** The polling loop must handle missing DB gracefully (try/except around the
`sqlite3.connect` call, sleep and retry).

### Pitfall 6: `groups create` requires approval — cannot be called non-interactively

**What goes wrong:** Plan attempts to create a new LAB group by calling
`ncl groups create` from the adapter; the operation blocks on approval.

**Why it happens:** `operations: { create: 'approval' }` in `src/cli/resources/groups.ts`.
The approval system notifies a human and blocks until approved.

**How to avoid:** Group creation must be a one-time manual setup step (Wave 0 human task),
not automated. The adapter takes the group ID as a pre-configured parameter.

---

## Session/Container Lifecycle (Q2)

[VERIFIED: `src/session-manager.ts`, `src/container-runner.ts`, `src/router.ts`]

### How a session + container comes to life

```
resolveSession(agentGroupId, messagingGroupId, threadId, 'shared')
  → if no existing session: createSession() + initSessionFolder()
      initSessionFolder():
        mkdir data/v2-sessions/<agentGroupId>/<sessionId>/
        mkdir data/v2-sessions/<agentGroupId>/<sessionId>/outbox/
        ensureSchema(inbound.db, 'inbound')   # creates messages_in table
        ensureSchema(outbound.db, 'outbound') # creates messages_out + processing_ack
  → writeSessionMessage() → INSERT INTO messages_in
  → wakeContainer(session)
      materializeContainerJson() → writes groups/<folder>/container.json from DB
      buildMounts() → assembles VolumeMount list incl. additional_mounts
      spawn(CONTAINER_RUNTIME_BIN, args)  # docker run ...
      container polls inbound.db every 1 second
```

**No persistent daemon process is required to be running for the container** — once
`docker run` is called, the container runs independently. However, the nanoclaw *host
process* (`src/index.ts`) must be running to call `wakeContainer()` in the daemon-based
paths.

**Session directory path:** `data/v2-sessions/<agentGroupId>/<sessionId>/`
**Inbound DB:** `data/v2-sessions/<agentGroupId>/<sessionId>/inbound.db`
**Outbound DB:** `data/v2-sessions/<agentGroupId>/<sessionId>/outbound.db`

### Container runtime

Uses `CONTAINER_RUNTIME_BIN` from `src/container-runtime.ts`. On this machine: Docker
(not Podman). Container image is `nanoclaw-agent:latest` (or per `CONTAINER_IMAGE` env).

---

## Mount Configuration (Q3 — Detailed)

[VERIFIED: `src/modules/mount-security/index.ts`, `src/container-runner.ts` line 323-327,
`src/container-config.ts`]

### How additional mounts flow

```
1. adapter writes additional_mounts JSON to container_configs table
   (via updateContainerConfigJson or direct DB write)

2. at spawn time: materializeContainerJson() reads container_configs → writes container.json

3. buildMounts() calls validateAdditionalMounts(containerConfig.additionalMounts, groupName)
   for each entry in additionalMounts:
     validateMount():
       load ~/.config/nanoclaw/mount-allowlist.json
       check containerPath is relative, no "..", no "/"
       expandPath(hostPath) → realPath
       check against blockedPatterns
       check realPath is under an allowedRoot
       if readonly=false AND allowedRoot.allowReadWrite=true → RW; else RO
     → assembled as {hostPath: realPath, containerPath: /workspace/extra/<containerPath>, readonly: bool}

4. docker run -v <hostPath>:<containerPath>[:ro]
```

### Required mount-allowlist.json changes (human setup task)

Current state: `allowedRoots: []` — all additional mounts blocked.
Required addition:
```json
{
  "path": "/Users/houfu/Projects/harvey-labs",
  "allowReadWrite": true,
  "description": "Harvey LAB tasks and results (lab-harness-runner)"
}
```

### How the adapter configures mounts (per-run)

The `additional_mounts` JSON column is overwritten wholesale per `updateContainerConfigJson`.
The adapter must:
1. Read existing `additional_mounts` for the group
2. Replace/append the LAB-specific entries for this run (task documents + output dir)
3. The output dir must exist on the host before docker run (mounts a path that doesn't exist
   → docker creates it as root-owned, may block agent writes)

**Conflict:** If other runs are in-flight for the same group, overwriting `additional_mounts`
will affect the next container spawn. For Phase 3 (single-task proof), this is not an issue.
Multi-run concurrency is a Phase 4+ concern.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| nanoclaw-lq daemon | Session creation, container wake | ✓ | 2.0.71 | — |
| Docker | Container runner | Assumed ✓ (ncl.sock exists, sessions active) | unknown | — |
| Harvey LAB repo | Task reading, evaluator | ✓ | (local) | — |
| `~/.config/nanoclaw/mount-allowlist.json` | Additional mounts | ✓ (exists but empty allowedRoots) | — | Add allowedRoots |
| `pnpm`/`tsx` (nanoclaw-lq) | Option A only | ✓ (pnpm@10.33.0 in package.json) | 10.33.0 | — |
| Python `sqlite3` | Outbound DB polling | ✓ (stdlib) | — | — |

**Missing dependencies with no fallback:**
- None that block execution, but:

**Missing dependencies with required config:**
- `mount-allowlist.json.allowedRoots` must include `/Users/houfu/Projects/harvey-labs` before
  any additional mount will pass validation. This is a human Wave 0 task.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Not yet installed (no pytest.ini or test files found) |
| Config file | none — Wave 0 gap |
| Quick run command | `uv run pytest tests/ -x -q` (after Wave 0) |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-DISPATCH | Adapter creates session and enqueues message | integration | Manual — requires running daemon | ❌ Wave 0 |
| REQ-MOUNTS | Documents appear at /workspace/extra/lab-documents | integration | Manual — requires Docker | ❌ Wave 0 |
| REQ-STATUS | STATUS: DONE in outbound.db → end_state="clean" | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_status_done -x` | ❌ Wave 0 |
| REQ-TIMEOUT | Poll timeout → end_state="timeout" | unit | `uv run pytest tests/test_nanoclaw_adapter.py::test_poll_timeout -x` | ❌ Wave 0 |
| REQ-DELIVERABLE | Missing deliverable → FileNotFoundError before score | unit | existing in test suite? | ❌ Wave 0 |
| REQ-EXIT | One real task produces deliverable in output/ | e2e/smoke | `uv run python scripts/nanoclaw_run.py --task corporate-ma/compare-matter-plan-against-engagement-letter` | ❌ Wave 0 |

**Note on integration tests:** The STATUS: poll loop and end_state mapping can be unit-tested
against a synthetic outbound.db written to a tmpdir — no daemon or Docker needed. The
dispatch and mount tests require the real daemon and are smoke/manual-only.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_nanoclaw_adapter.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate (exit criterion):** Manual smoke: `uv run python scripts/nanoclaw_run.py --task corporate-ma/compare-matter-plan-against-engagement-letter`; confirm `results/<run-id>/output/discrepancy-analysis-memo.docx` exists.

### Wave 0 Gaps

- [ ] `tests/test_nanoclaw_adapter.py` — unit tests for STATUS: poll, timeout, end_state mapping
- [ ] `tests/conftest.py` — shared fixtures (tmp_path-based synthetic outbound.db)
- [ ] Framework install: `uv add --dev pytest` — if not already present

---

## Security Domain

ASVS enforcement is not explicitly configured, but the phase touches file I/O and external
process invocation. Key controls:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `_reject_unsafe_relative_path()` already enforced in task_reader; apply to group_id and session_id too |
| V6 Cryptography | no | — |
| Path traversal | yes | Additional mounts use nanoclaw's `validateMount()` which checks for `..` in containerPath |

**Specific risk:** The adapter writes to `~/.config/nanoclaw/mount-allowlist.json` contents
that are later used as Docker bind mount sources. If the Harvey LAB path is added correctly,
this is not a path escalation vector. The adapter should NOT write arbitrary paths to
`additional_mounts` — only the task's known documents dir and the run's known output dir.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Docker (not Podman) is the container runtime on this machine | Environment Availability | Container spawn args may differ; CONTAINER_RUNTIME_BIN resolves the binary |
| A2 | The `main` nanoclaw group uses Anthropic Claude (not Ollama) | Briefing/Group Strategy | LAB tasks may fail or produce poor quality with non-Claude model |
| A3 | Outbound.db messages_out.content is always valid JSON with a "text" key | Completion Signaling | Poll code would miss STATUS: if format differs |
| A4 | `data/ncl.sock` existing implies the daemon is running | Environment Availability | Socket file may be stale from a previous crashed daemon |

---

## Open Questions (RESOLVED)

1. **DISPATCH PATH — USER DECISION REQUIRED (D-03)** — **RESOLVED: Option A (thin Node shim).**
   User selected Option A during /gsd:plan-phase post-research (recorded in 03-CONTEXT.md D-03,
   2026-05-31). Adding `scripts/send-lab-message.ts` to the nanoclaw-lq repo is accepted; it
   imports nanoclaw's `session-manager` and is called by the Python adapter via subprocess.
   No human-verify checkpoint is needed to re-decide dispatch — the choice is locked.
   - What we know: No `ncl` CLI command enqueues an inbound message. Three options: (A) thin
     Node shim in nanoclaw-lq repo, (B) direct Python SQLite write to inbound.db, (C) use
     existing cli.sock chat channel.
   - Resolution: Option A. (B rejected — cannot bootstrap a session, schema-fragile; C rejected
     — no per-task session isolation, existing group uses Ollama.)

2. **Which group to use for LAB runs** — **RESOLVED: dedicated LAB group via human Wave-0 setup.**
   Plan 03 Task 1 (`checkpoint:human-action`) requires creating/configuring a dedicated
   Anthropic-Claude LAB group before the proof run, avoiding pollution of existing group history.
   - What we know: `_ping-test` group uses Ollama (not Anthropic). There is also a `main`
     group folder in `groups/main/` but no corresponding agent group DB row was listed in
     `ncl groups list`. The daemon shows only the `_ping-test` / "Terminal Agent" group.
   - Resolution: Create a dedicated LAB group as a one-time human setup task (Plan 03 Task 1).

3. **Session isolation per LAB run** — **RESOLVED: `sessionMode: 'agent-shared'` for Phase 3.**
   Plan 02 Task 1's shim uses `'agent-shared'`; context-accumulation concerns are deferred to
   Phase 4 per the recommendation below.
   - What we know: Sessions are keyed by (agentGroupId, messagingGroupId, threadId). If the
     adapter reuses the same group without a new messaging group per run, all runs share one
     session and its `inbound.db` accumulates all prior messages.
   - Resolution: Use `sessionMode: 'agent-shared'` (one session per agent group) for
     simplicity in Phase 3; revisit in Phase 4 if context accumulation causes issues.

---

## Sources

### Primary (HIGH confidence)
- `/Users/houfu/Projects/nanoclaw-lq/src/cli/client.ts` — CLI entry point and command parsing
- `/Users/houfu/Projects/nanoclaw-lq/src/cli/resources/sessions.ts` — sessions CLI resource (list/get only, no create)
- `/Users/houfu/Projects/nanoclaw-lq/src/cli/resources/groups.ts` — groups CLI operations
- `/Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts` — session lifecycle, writeSessionMessage, inbound/outbound DB paths
- `/Users/houfu/Projects/nanoclaw-lq/src/container-runner.ts` — spawnContainer, buildMounts, additional_mounts application
- `/Users/houfu/Projects/nanoclaw-lq/src/modules/mount-security/index.ts` — validateAdditionalMounts, mount-allowlist enforcement
- `/Users/houfu/Projects/nanoclaw-lq/src/container-config.ts` — ContainerConfig type, materializeContainerJson
- `/Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts` — messages_in / messages_out / processing_ack table schemas
- `/Users/houfu/Projects/nanoclaw-lq/container/agent-runner/src/index.ts` — /workspace/extra/* discovery
- `/Users/houfu/Projects/nanoclaw-lq/container/agent-runner/src/poll-loop.ts` — STATUS: dispatch, dispatchResultText
- `/Users/houfu/Projects/nanoclaw-lq/src/router.ts` — routeInbound flow
- `/Users/houfu/Projects/nanoclaw-lq/scripts/test-v2-host.ts` — end-to-end test pattern (open/write/close per poll)
- `~/.config/nanoclaw/mount-allowlist.json` — confirmed empty allowedRoots
- `/Users/houfu/Projects/nanoclaw-lq/data/ncl.sock` — confirmed daemon is running
- `/Users/houfu/Projects/harvey-labs/tasks/corporate-ma/compare-matter-plan-against-engagement-letter/task.json` — proof task verified

### Secondary (MEDIUM confidence)
- `docs/verified-contracts.md` — Phase 1 contracts (confirmed by source inspection this session)

---

## Metadata

**Confidence breakdown:**
- Dispatch CLI verdict: HIGH — confirmed by complete source inspection of cli/resources/ directory
- Session/container lifecycle: HIGH — confirmed by session-manager.ts and container-runner.ts
- Mount wiring: HIGH — confirmed by mount-security module + container-runner.ts buildMounts()
- Completion signaling: HIGH — confirmed by schema.ts + poll-loop.ts dispatchResultText()
- Proof task: HIGH — confirmed by direct task.json inspection
- Briefing strategy: MEDIUM — group provider config inferred from container.json (Ollama vs Anthropic)

**Research date:** 2026-05-31
**Valid until:** 2026-07-01 (stable architecture; nanoclaw-lq v2 schema changes infrequently)
