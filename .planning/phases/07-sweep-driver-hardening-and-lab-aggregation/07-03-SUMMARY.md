---
phase: 07-sweep-driver-hardening-and-lab-aggregation
plan: "03"
subsystem: sweep-driver
tags: [sweep, lab-integration, shell, documentation]
dependency_graph:
  requires: ["07-02"]
  provides: ["LAB_COMPARE opt-in shell-out", "config.json gap documentation"]
  affects: ["scripts/sweep.sh", "docs/adapter-guide.md"]
tech_stack:
  added: []
  patterns: ["subshell cd+uv run pattern", "case-dispatch input validation"]
key_files:
  created: []
  modified:
    - scripts/sweep.sh
    - docs/adapter-guide.md
decisions:
  - "LAB_COMPARE=task|area arg sourced from separate LAB_COMPARE_ARG env var (D-09 discretion; explicit over inferred)"
  - "run_lab_compare uses uv run python (not $PY) so uv discovers $LAB_PATH/pyproject.toml"
  - "config.json gap accepted as documented limitation (T-07-10 — accept disposition)"
metrics:
  duration: "~4 minutes"
  completed: "2026-06-07"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 7 Plan 3: LAB_COMPARE Integration and Documentation Summary

opt-in `LAB_COMPARE` shell-out to LAB's `evaluation.compare` via
`( cd "$LAB_PATH" && uv run python -m evaluation.compare ... )`, with
config.json compatibility gap documented in adapter guide.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add run_lab_compare() and wire into main | 0867412 | scripts/sweep.sh |
| 2 | Document LAB_COMPARE usage and config.json gap | f42a481 | docs/adapter-guide.md |

## What Was Built

### Task 1: run_lab_compare() function (scripts/sweep.sh)

Added `run_lab_compare()` before `main()` with:
- Guard: `[ -n "${LAB_COMPARE:-}" ] || return 0` — no-op when env var unset
- `case "$LAB_COMPARE"` with arms `task`, `area`, `all`, and default error arm
- `task` and `area` arms read `LAB_COMPARE_ARG`; print error to stderr and return 1 if unset
- `all` arm includes inline comment documenting the config.json gap
- Each arm runs `( cd "$LAB_PATH" && uv run python -m evaluation.compare --{task|area|all} ... )`
- Default arm: prints `LAB_COMPARE must be task|area|all (got: ...)` to stderr, returns 1
- Wired as final `main()` step after `check_failures || exit 1` — clean sweeps reach compare
- Added `LAB_PATH` to the `export` line

No aggregation logic added to runner — shell-out only (LAB-01 preserved).

### Task 2: LAB_COMPARE documentation (docs/adapter-guide.md)

Appended new section "Sweep LAB comparison (LAB_COMPARE)" covering:
- Three scopes (task/area/all) with LAB_COMPARE_ARG requirements table
- Runner-stays-thin principle: LAB is the source of scoring/reporting
- config.json compatibility gap: `collect_runs()` skips dirs without `config.json`;
  runner-produced results lack it, yielding empty compare output by design
- Recommendation to point LAB_COMPARE at LAB-native results for non-empty output
- Concrete example invocations for all three scopes

## Verification

- `bash -n scripts/sweep.sh` exits 0 (syntax clean)
- `grep -c 'evaluation.compare' scripts/sweep.sh` returns 4 (>= 3 required)
- `LAB_COMPARE=bogus run_lab_compare` returns 1 with stderr error
- Unset `LAB_COMPARE` returns 0 without subprocess
- `LAB_COMPARE=task` with unset `LAB_COMPARE_ARG` returns 1 with stderr error
- `grep -c 'LAB_COMPARE' docs/adapter-guide.md` returns 14 (>= 3 required)
- `grep -qi 'config.json' docs/adapter-guide.md` exits 0
- Thin-runner principle documented: "LAB remains the source of scoring and reporting"

## Deviations from Plan

None — plan executed exactly as written. The `run_lab_compare()` function and
documentation match Sub-pattern F from 07-PATTERNS.md verbatim.

## Threat Model Coverage

| Threat | Disposition | Implementation |
|--------|-------------|----------------|
| T-07-08 Input Validation LAB_COMPARE | mitigate | `case` matches only task/area/all; default arm errors and returns 1 |
| T-07-09 Tampering LAB_COMPARE_ARG | mitigate | Value quoted as `"$arg"` — not eval'd; passed to argparse as a string |
| T-07-10 Empty compare output against runner dirs | accept | config.json gap documented in adapter-guide.md |
| T-07-11 Subprocess inherits sweep env | accept | Subprocess is LAB's own tool in a subshell; no privilege escalation |

## Self-Check: PASSED

- scripts/sweep.sh: present and syntactically valid
- docs/adapter-guide.md: LAB_COMPARE section appended
- Commit 0867412: feat(07-03) — verified in git log
- Commit f42a481: docs(07-03) — verified in git log
