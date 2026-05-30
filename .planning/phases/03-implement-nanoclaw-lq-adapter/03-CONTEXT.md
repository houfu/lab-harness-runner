# Phase 3: Implement Nanoclaw-LQ Adapter - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the `nanoclaw-lq` adapter — a Python class satisfying the
`Adapter.run(task_spec, output_dir) -> RunResult` protocol from Phase 2 — that
dispatches a LAB task into nanoclaw's container, wires the document/output
mounts, waits for completion, and reports a `RunResult`. Then run one real LAB
task through it.

**Exit criterion:** One LAB task reaches nanoclaw and produces at least one
expected deliverable in `results/<run-id>/output/`.

This phase clarifies HOW to implement the adapter. New capabilities (additional
adapters, multi-task/multi-seed orchestration) belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Dispatch Mechanism (discussed this session)
- **D-01:** Primary dispatch path is to **shell out to a nanoclaw CLI** that uses
  nanoclaw's own session-manager API to enqueue the inbound task message. The
  adapter does not write `inbound.db` directly on the happy path. This keeps the
  adapter on nanoclaw's supported API surface rather than coupling to the SQLite
  schema (`schema.ts`).
- **D-02:** **Research must verify** that nanoclaw exposes a suitable CLI/command
  for enqueuing an inbound `messages_in` message. `verified-contracts.md`
  documented the session-DB split and the one-writer invariant but did NOT
  confirm such a CLI exists.
- **D-03:** **Fallback policy — block and report.** If research finds no suitable
  CLI, STOP and surface the finding to the user. Do NOT auto-select direct SQLite
  writes or a Node shim. The user will decide the dispatch path once the real
  nanoclaw surface is known. (Direct SQLite write and a thin Node `send-message`
  shim were both considered as fallbacks and explicitly deferred to that
  decision point.)
- **D-04:** **Inbound message content = instructions + explicit output contract.**
  The dispatched message carries `TaskSpec.instructions` PLUS an explicit footer
  that states (a) the exact output path the agent must write to
  (`/workspace/extra/lab-output`) and (b) the exact expected deliverable
  filenames from `TaskSpec.expected_deliverables`. This removes ambiguity and
  directly serves the locked exact-filename and correct-location goals.
- **D-05:** **Footer also states the completion-signal protocol.** The same
  message footer instructs the agent to emit the locked terminal `STATUS:` signal
  (e.g., `STATUS: DONE`) when finished, so the per-task dispatch message is a
  self-contained contract independent of group briefing correctness.

### Carried Forward (locked in PROJECT.md / Phase 1–2 — do NOT re-decide)
- nanoclaw-lq runs in its own Docker container, not LAB's podman sandbox.
- Task documents mounted read-only; the run output directory mounted read-write.
- Suggested mount paths: `/workspace/extra/lab-documents` (docs, read-only) and
  `/workspace/extra/lab-output` (output, read-write) — per
  `docs/verified-contracts.md` mount-configuration section.
- Deliverables land directly in `results/<run-id>/output/`.
- Completion = a structured terminal `STATUS:` signal plus a wall-clock timeout;
  end-state recorded as `clean` / `agent_error` / `timeout`.
- Adapter contract is the Phase 2 `typing.Protocol`:
  `run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult`.
- Pre-score sanity check: every expected deliverable filename must exist in
  `output/` (Phase 2 `evaluator.py` already enforces this).
- LAB remains an unmodified dependency.

### Claude's Discretion
- Exact CLI command name/flags to call once research confirms the surface.
- Footer wording/format for the output contract and `STATUS:` instruction.
- Which specific LAB task to use as the single-task proof for the exit criterion.

### Areas left to research/planning (not discussed this session)
The user chose to discuss only Dispatch mechanism. These remain open for the
researcher/planner to resolve (grounded in `verified-contracts.md`):
- **Briefing & group strategy** — dedicated LAB nanoclaw group vs full briefing in
  the first inbound message. Contracts warn against mutating an existing group.
- **Completion detection** — poll `outbound.db` `messages_out` for the `STATUS:`
  line vs watch for a sentinel file; concrete wall-clock timeout value.
- **Session/container lifecycle** — adapter launches the nanoclaw container/session
  itself vs assumes a running nanoclaw daemon and only creates a session.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Verified External Contracts (Phase 1)
- `docs/verified-contracts.md` — Authoritative source for nanoclaw session DBs
  (`inbound.db`/`outbound.db`, one-writer invariant), mount configuration
  (`/workspace`, `/workspace/agent`, `/workspace/extra/*`), and briefing behavior.
  MUST read before implementing dispatch and mounts.

### nanoclaw-lq Source (verify the dispatch CLI surface — D-02)
- `/Users/houfu/Projects/nanoclaw-lq/src/session-manager.ts` — Session APIs and
  the inbound/outbound write model (contract evidence: lines 1, 56, 61).
- `/Users/houfu/Projects/nanoclaw-lq/src/db/schema.ts` — `messages_in` /
  `messages_out` / `processing_ack` schema (evidence: lines 148, 157, 221). Only
  relevant if research forces the SQLite fallback path.
- `/Users/houfu/Projects/nanoclaw-lq/src/container-config.ts` &
  `container-runner.ts` — `additional_mounts` configuration and validation
  (evidence: container-config.ts:26,50; container-runner.ts:267,270,323).
- `/Users/houfu/Projects/nanoclaw-lq/container/agent-runner/src/index.ts:56` —
  How the agent runner discovers `/workspace/extra/*` mounts.
- `/Users/houfu/Projects/nanoclaw-lq/src/claude-md-compose.ts` — Group briefing
  composition (relevant to the deferred briefing/group decision).

### Phase 2 Package Surface (what the adapter plugs into)
- `lab_harness_runner/adapter.py` — `TaskSpec`, `RunResult`, and the `Adapter`
  Protocol the nanoclaw adapter must satisfy.
- `lab_harness_runner/result_builder.py`, `metrics.py`, `evaluator.py` — Result
  directory creation, `metrics.json` writing, and evaluator invocation the
  adapter run path feeds into.
- `scripts/fake_run.py` — Phase 2 end-to-end wiring reference (TaskSpec → output
  dir → metrics.json → evaluator) to mirror for the real run.

### Project Specs
- `.planning/REQUIREMENTS.md` — Functional/quality requirements (harness-agnostic
  core, adapter-owned env/dispatch/completion/metrics, verify-live-interfaces).
- `.planning/PROJECT.md` — Locked decisions (LAB unmodified, uv/black, contract
  shape, end-state taxonomy).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lab_harness_runner/adapter.py` — `RunResult.__post_init__` already validates
  `end_state`; the nanoclaw adapter just needs to populate it correctly.
- `scripts/lab_probe.py` / `scripts/fake_run.py` — Working examples of result
  directory creation and evaluator invocation patterns to reuse.

### Established Patterns
- Flat package layout at `lab_harness_runner/`; new adapter code is a new module
  in that package (no sub-packages — Phase 2 D-02).
- Python 3.11+ syntax, `black` (line-length 88), `uv` for dependency management.
- Subprocess-based integration with external tools (Phase 2 evaluator wrapper
  shells out via `subprocess.run([...], cwd=..., check=True)`) — the same pattern
  fits the "shell out to nanoclaw CLI" dispatch decision (D-01).

### Integration Points
- The adapter is invoked through the Phase 2 `Adapter` protocol and must produce
  output under `results/<run-id>/output/` so the existing evaluator/metrics path
  works unchanged.

</code_context>

<specifics>
## Specific Ideas

- Mirror the Phase 2 evaluator wrapper's subprocess style for the nanoclaw CLI
  dispatch call (explicit arg list, `check=True`, captured output) for
  consistency.
- The output-contract footer should be unambiguous enough that the agent does not
  rely on group briefing or mount-layout inference to know where to write or what
  to name files.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Direct SQLite write and a Node
`send-message` shim are not deferred *ideas* but deferred *fallback decisions*
gated on research per D-03.)

</deferred>

---

*Phase: 3-Implement Nanoclaw-LQ Adapter*
*Context gathered: 2026-05-31*
