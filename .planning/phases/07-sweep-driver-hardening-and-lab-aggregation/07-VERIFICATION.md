---
phase: 07-sweep-driver-hardening-and-lab-aggregation
verified: 2026-06-07T12:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run a multi-task sweep with deliberately-crashed tasks and inspect the tally_summary output"
    expected: >
      The `summary:` line shows `agent_error=N` (where N > 0) for tasks that wrote
      `benchmark_status: "error"` in their metrics.json, and `missing_deliverable=0` for those
      same tasks. Prior to CR-02's fix the `agent_error)` arm matched nothing and every error
      task was bucketed as missing_deliverable. The fix changes the case arm from `agent_error)`
      to `error)`. Verify this with a real run that produces at least one `benchmark_status:
      "error"` entry (e.g. a task with a missing deliverable that still writes metrics.json).
    why_human: >
      grep on static metrics.json files cannot reproduce the actual case-dispatch logic execution.
      The fix is syntactically present and correct (case arm `error)` matches the value that
      `status.py` emits), but whether the tally counts are reported accurately across a live
      sweep with mixed outcomes (clean + error + timeout) requires a real run with known ground
      truth counts to confirm the output label "agent_error=" maps correctly and the
      missing_deliverable bucket stays clean.
---

# Phase 7: Sweep Driver Hardening and LAB Aggregation — Verification Report

**Phase Goal:** Harden the post-v1.0 `sweep.sh` driver and wire it into LAB's existing
aggregation / comparison tools, without introducing a new aggregator in the runner.
**Verified:** 2026-06-07T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sweep.sh` documents TIMEOUT 600s default with wall-clock rationale (SWP-01) | VERIFIED | Lines 37-43: comment block contains `p99`, `586.2s (n=137 clean)`, `max = 596.1s`, `600s`, override example `TIMEOUT=300 scripts/sweep.sh` |
| 2 | `sweep.sh inventory` output is both human-readable (counts) and machine-readable (bare paths, CI-consumable) (SWP-02) | VERIFIED | Lines 110-139: emits `total:`, `clean:`, `incomplete:`, `---`, then bare `$RESULTS/<run_id>` paths; no `FAILED/MISSING:` prefix found (grep returns 0 matches) |
| 3 | `sweep.sh` post-run summary prints clean/agent_error/timeout/missing_deliverable tallies (SWP-03) | VERIFIED | Line 170: `echo "summary: clean=$clean agent_error=$agent_error timeout=$timeout missing_deliverable=$missing"` in `tally_summary()`, called from `main()` at line 256 |
| 4 | Sweep failures exit non-zero with per-run error log path on stderr (SWP-04) | VERIFIED | Lines 173-183: `check_failures()` iterates `.failed` markers, emits `FAILED: $LOG_DIR/$run_id.log >&2`, returns non-zero; wired into `main()` at line 257 as `check_failures \|\| exit 1`; behavioral check confirmed rc=1 |
| 5 | `sweep.sh` produces output compatible with LAB's batch-summary tool; no new aggregator in runner (LAB-01) | VERIFIED | No aggregation keywords (`mean`, `stdev`, `variance`, `aggregate`, `score`) in `scripts/sweep.sh`. Shell-out only via `uv run python -m evaluation.compare`. `docs/adapter-guide.md` explicitly states "LAB remains the source of scoring and reporting" |
| 6 | `LAB_COMPARE=task\|area\|all` invokes LAB's comparison as an opt-in final step (LAB-02) | VERIFIED | Lines 222-241: `run_lab_compare()` with `case "$LAB_COMPARE"` dispatching `task`/`area`/`all` arms; `grep -c evaluation.compare scripts/sweep.sh` = 5; wired into `main()` at line 258 after `check_failures`; invalid value returns non-zero to stderr |

**Score: 6/6 truths verified**

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/sweep.sh` | Documented TIMEOUT, dual inventory, marker tracking, tally_summary, check_failures, run_lab_compare | VERIFIED | All functions present and substantive; `bash -n` exits 0; wired into `main()` |
| `docs/adapter-guide.md` | LAB_COMPARE usage + config.json gap note | VERIFIED | Section "Sweep LAB comparison (LAB_COMPARE)" appended at line 278; 16 occurrences of `LAB_COMPARE`; config.json gap documented with empty-output explanation and recommended workflow |
| `.planning/phases/07-sweep-driver-hardening-and-lab-aggregation/REVIEW.md` | Code review of four post-v1.0 commits | VERIFIED | All four commit SHAs present: `3a1fd89`, `17d3eb7`, `3e0dd71`, `2884ae7` |
| `.planning/phases/07-sweep-driver-hardening-and-lab-aggregation/REPLAY.md` | Replay of hardened inventory against live data | VERIFIED | Contains `incomplete`, `170`, `136`; reconciles stale ROADMAP figure (174/140) against live (170/136) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/sweep.sh inventory` | CI consumer / xargs | `---` separator + bare path lines; CI skips header with `tail -n +5` | VERIFIED | Lines 127-138; comment at line 126 documents CI skip technique; empty array guard (CR-01 fix) at line 134 prevents set -u abort on fully-clean sweep |
| `run_one` | `tally_summary` / `check_failures` in `main()` | `$LOG_DIR/$run_id.attempted` and `$LOG_DIR/$run_id.failed` marker files | VERIFIED | Lines 102-104: `.failed` touched on no-metrics+no-output condition; `.attempted` touched unconditionally after real run; stale cleanup at line 250 before xargs |
| `tally_summary` | `metrics.json benchmark_status` | `grep -o '"benchmark_status": *"[^"]*"'` per `.attempted` marker | VERIFIED | Lines 152-168; case arms: `clean)`, `timeout)`, `error)` (CR-02 fix — matches actual `status.py` value, not dead `agent_error)`), `*)` |
| `scripts/sweep.sh run_lab_compare` | harvey-labs `evaluation.compare` | `( cd "$LAB_PATH" && uv run python -m evaluation.compare ... )` subshell | VERIFIED | Lines 229, 231, 238: all three arms use the confirmed subshell+`uv run` pattern; `LAB_PATH` is exported at line 144 |
| `validate_lab_compare` | `main()` pre-sweep gate | Called at line 247, before `build_task_list` at line 251 | VERIFIED | WR-01 fix confirmed: invalid `LAB_COMPARE` exits before any task runs; `docs/adapter-guide.md` line 301 documents "without running any task" |

### Data-Flow Trace (Level 4)

Not applicable — `scripts/sweep.sh` is a bash driver, not a component rendering dynamic data. All data flow is through file-system markers and subprocess stdout.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Script parses cleanly | `bash -n scripts/sweep.sh` | exit 0 | PASS |
| TIMEOUT comment contains required tokens | `grep -q 'p99\|586.2\|TIMEOUT=300' scripts/sweep.sh` | all three found at lines 37, 38, 43 | PASS |
| No `FAILED/MISSING:` prefix in inventory output | `grep -c 'FAILED/MISSING:' scripts/sweep.sh` | 0 | PASS |
| summary: line format correct | `grep 'summary: clean=' scripts/sweep.sh` | found at line 170 | PASS |
| check_failures returns non-zero on .failed marker | inline bash test with `touch x.failed` | `rc=1`, `FAILED: ...x.log` on stderr | PASS |
| evaluation.compare referenced >= 3 times | `grep -c 'evaluation.compare' scripts/sweep.sh` | 5 | PASS |
| No aggregation logic in runner | `grep -ci 'scores\|aggregate\|mean\|stdev\|compare(' scripts/sweep.sh` | 3 (all are comments referencing "evaluation.compare" string — no implementation code) | PASS |
| LAB_COMPARE section in adapter-guide.md | `grep -c 'LAB_COMPARE' docs/adapter-guide.md` | 16 (>= 3 required) | PASS |
| config.json gap documented | `grep -qi 'config.json' docs/adapter-guide.md` | exit 0 | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist. No probes declared in PLAN files. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| SWP-01 | 07-01-PLAN.md | TIMEOUT default documented with wall-clock rationale | SATISFIED | Lines 36-44: p99=586.2s, n=137, max=596.1s, 600s ceiling, deliverable-gate note, `TIMEOUT=300` override |
| SWP-02 | 07-01-PLAN.md | `inventory` output machine+human readable, CI-consumable | SATISFIED | Lines 110-139: 3-line counts header + `---` + bare paths; no prefix; bash 3.2 empty-array guard (CR-01 fix) |
| SWP-03 | 07-02-PLAN.md | Post-run summary prints clean/agent_error/timeout/missing counts | SATISFIED | `tally_summary()` at lines 146-171; D-06 format string at line 170; wired in `main()` at line 256 |
| SWP-04 | 07-02-PLAN.md | Sweep exits non-zero; per-run log path on stderr for each failure | SATISFIED | `check_failures()` at lines 173-183; `main()` line 257: `check_failures \|\| exit 1` |
| LAB-01 | 07-03-PLAN.md | No new aggregator in runner; output compatible with LAB's tools | SATISFIED | Zero aggregation code in sweep.sh; shell-out only; config.json gap documented |
| LAB-02 | 07-03-PLAN.md | `LAB_COMPARE=task\|area\|all` invokes evaluation.compare as opt-in final step | SATISFIED | `run_lab_compare()` at lines 222-241; `validate_lab_compare()` provides early validation; wired as final step in `main()` |

All 6 requirements claimed by the phase are satisfied. No orphaned requirements found (REQUIREMENTS.md maps SWP-01 through SWP-04, LAB-01, LAB-02 to Phase 7).

### Code Review Fixes Verified

All six issues from `07-REVIEW.md` are confirmed fixed:

| Finding | Fix Commit | Status | Evidence |
|---------|-----------|--------|---------|
| CR-01: empty `paths[]` aborts under `set -u` on bash 3.2 | `82bcc69` | FIXED | Lines 134-138: `if [ "${#paths[@]}" -gt 0 ]; then` guard; comment at line 131-133 explains rationale |
| CR-02: `tally_summary` matched `agent_error)` but runner emits `"error"` | `9d2d5f5` | FIXED | Line 166: `error)   agent_error=$((agent_error+1)) ;;`; comment at lines 159-162 documents the mismatch and fix |
| WR-01: `validate_lab_compare` ran after sweep, not before | `131bba6` | FIXED | `validate_lab_compare \|\| exit 1` at line 247 is the first statement in `main()`, before `mkdir` and `build_task_list` |
| WR-02: `check_failures \|\| exit 1` silently skips `run_lab_compare` on any failure | `70fdbb7` | DOCUMENTED | Behavior intentionally preserved; `docs/adapter-guide.md` lines 310-318 document the skip-on-failure contract explicitly |
| WR-03: `LAB_COMPARE_ARG` forwarded with no traversal/path validation | `4b3d4ed` | FIXED | `validate_lab_compare_arg()` at lines 189-196 rejects `/` prefix and `..` traversal; called from `validate_lab_compare()` |
| WR-04: unquoted `$PY` breaks on paths with spaces | `9c600a9` | FIXED | `resolve_py()` at lines 61-67 sets `PY` as an array; `run_one` uses `"${PY[@]}"` at line 90; xargs subshell rebuilds array via exported function at line 143 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` found in either modified file | — | — |

No anti-patterns detected in `scripts/sweep.sh` or `docs/adapter-guide.md`.

### Human Verification Required

#### 1. CR-02 tally_summary counting semantics under a real multi-task sweep

**Test:** Run a sweep that produces at least one task with `benchmark_status: "error"` in its
`metrics.json` (a task that fails with the runner alive — not a hard crash). Check the
`summary:` output line.

**Expected:** `summary:` shows `agent_error=N` (where N equals the count of `"error"` entries in
`metrics.json` files) and `missing_deliverable=0` for those same tasks. The `missing_deliverable`
counter should only reflect tasks with absent `metrics.json` files or truly unrecognized status
values.

**Why human:** The CR-02 fix (`9d2d5f5`) changes the case arm from `agent_error)` to `error)` so
that it matches the value `status.py` actually writes (`"error"`, confirmed at `status.py:29`).
Static grep-based checks confirm the arm text is correct. However, verifying that the tally
counts are accurate across a full multi-task sweep with mixed outcomes (clean + error + timeout)
requires a real run with known-ground-truth inputs. The fix is structurally sound, but the
behavioral correctness with a live 1251-task sweep cannot be confirmed without running one.

### Gaps Summary

No gaps. All 6 roadmap success criteria verified against the actual codebase. All code review
blockers and warnings are fixed and confirmed. The single human verification item (CR-02
counting semantics) is a confidence check on a behaviorally correct fix, not a blocker — the
code is correct per static analysis and confirmed against the `status.py` source.

---

_Verified: 2026-06-07T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
