# Phase 3: Implement Nanoclaw-LQ Adapter - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 03-implement-nanoclaw-lq-adapter
**Areas discussed:** Dispatch mechanism

**Area selection:** User chose to discuss only "Dispatch mechanism" from the four
offered gray areas (Dispatch mechanism, Briefing & group strategy, Completion
detection, Session/container lifecycle). The other three were intentionally left
to research/planning.

---

## Dispatch Mechanism

### Q1 — Primary dispatch path

| Option | Description | Selected |
|--------|-------------|----------|
| Direct SQLite write (Python) | sqlite3 stdlib inserts into inbound.db messages_in directly; no Node dep; couples to schema.ts | |
| Shell out to nanoclaw CLI | Subprocess-call an existing nanoclaw CLI that uses session-manager API; schema-resilient; requires CLI to exist | ✓ |
| Thin Node helper shim | Small Node script importing session-manager.ts exposing a send-message CLI | |

**User's choice:** Shell out to nanoclaw CLI.
**Notes:** Keeps the adapter on nanoclaw's supported API surface. Flagged that
`verified-contracts.md` did not confirm such a CLI exists, so research must verify.

### Q2 — Fallback if no suitable CLI exists

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to direct SQLite write | Adapter writes inbound.db directly, preserving one-writer invariant | |
| Add the thin Node shim | Minimal Node send-message script importing session-manager.ts | |
| Block & report to me | Stop and surface the finding rather than auto-choosing | ✓ |

**User's choice:** Block & report to me.
**Notes:** User wants to decide the dispatch path once the real nanoclaw surface
is known, rather than locking a fallback now.

### Q3 — Inbound message content

| Option | Description | Selected |
|--------|-------------|----------|
| Instructions + explicit output contract | instructions + footer with exact output path and expected filenames | ✓ |
| Instructions only | Rely on briefing/mount layout to convey where to write | |
| Instructions + output path only | Path but not filenames | |

**User's choice:** Instructions + explicit output contract.
**Notes:** Removes ambiguity; directly serves the exact-filename and
correct-location goals.

### Q4 — Completion-signal protocol placement

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include STATUS protocol in footer | Same footer instructs the agent to emit terminal STATUS: when done | ✓ |
| No — keep STATUS in group briefing | Footer covers only output path + filenames | |

**User's choice:** Yes — include STATUS protocol in footer.
**Notes:** Makes the per-task dispatch message a self-contained contract,
independent of group-briefing correctness.

---

## Claude's Discretion

- Exact CLI command name/flags once research confirms the surface.
- Footer wording/format for the output contract and STATUS instruction.
- Which specific LAB task to use for the single-task proof.

## Deferred Ideas

None within scope. Direct SQLite write and a Node send-message shim are deferred
*fallback decisions* gated on research (CONTEXT.md D-03), not deferred ideas for
other phases.
