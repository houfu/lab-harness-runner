---
phase: "02-build-harness-neutral-package-core"
plan: "05"
subsystem: "scripts"
tags: ["fake-adapter", "end-to-end", "wiring-proof", "phase-exit-criterion"]
dependency_graph:
  requires: ["02-04"]
  provides: ["Phase 2 exit criterion — end-to-end package wiring proof"]
  affects: []
tech_stack:
  added: []
  patterns:
    - "Structural subtyping (FakeAdapter satisfies Adapter Protocol without inheritance)"
    - "Minimal valid DOCX writer via ZipFile"
    - "reject_unsafe_relative_path for CLI arg path safety"
key_files:
  created:
    - scripts/fake_run.py
  modified: []
decisions:
  - "FakeAdapter uses structural subtyping (no inheritance from Adapter Protocol) per D-07"
  - "reject_unsafe_relative_path applied to both --task and --run-id before any filesystem use (T-02-12)"
  - "Scoring is opt-in via --score flag; not invoked by default (T-02-14)"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-30"
  tasks_completed: 1
  tasks_total: 1
---

# Phase 02 Plan 05: Fake Run Script Summary

Standalone `scripts/fake_run.py` that proves the full `lab_harness_runner` package API is correctly wired end-to-end: reads a real LAB task, creates a run directory with placeholder deliverables (minimal valid DOCX for `.docx`, plain text otherwise), writes `metrics.json`, and exits 0.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement scripts/fake_run.py | 2f7c12a | scripts/fake_run.py |

## Verification Results

- `uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy` exits 0
- Run directory created at `~/Projects/harvey-labs/results/<uuid>/`
- `metrics.json` exists and is valid JSON with all expected keys
- `output/antitrust-risk-memo.docx` written as minimal valid DOCX (ZipFile)
- `uv run black --check scripts/fake_run.py` exits 0
- `uv run pytest tests/ -x -q`: 45 passed, no regressions

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `fake_run.py` is intentionally a placeholder/wiring-proof script. All deliverables it writes are explicit placeholder content by design.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model. `reject_unsafe_relative_path` is applied to both `--task` and `--run-id` CLI arguments before any filesystem operation (T-02-12 mitigated).

## Self-Check: PASSED

- scripts/fake_run.py: FOUND
- Commit 2f7c12a: FOUND
- `uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy` exits 0: CONFIRMED
- metrics.json valid JSON: CONFIRMED
- black --check: CONFIRMED
- pytest 45 passed: CONFIRMED
