---
phase: 01-verify-external-contracts-and-scoring-pipeline
plan: 01
subsystem: tooling
tags: [harvey-lab, nanoclaw, evaluation, probe]
requires: []
provides:
  - Verified Harvey LAB task/result/evaluator contract notes
  - Verified nanoclaw-lq session, mount, and briefing contract notes
  - Dry-run LAB result-layout probe
  - Manual LAB scorer check instructions
affects: [phase-2, phase-3, lab-runner-core, nanoclaw-adapter]
tech-stack:
  added: [python, uv]
  patterns:
    - Dry-run validation before live judge execution
    - Explicit path traversal rejection before result writes
key-files:
  created:
    - docs/verified-contracts.md
    - docs/phase-1-manual-check.md
    - scripts/lab_probe.py
    - pyproject.toml
    - uv.lock
    - .gitignore
  modified:
    - .planning/STATE.md
key-decisions:
  - "Phase 1 does not modify nanoclaw-lq; adapter changes are deferred."
  - "Dry-run validation creates LAB result layout without invoking the external judge."
  - "Exact expected deliverable filenames are generated from criteria[].deliverables."
patterns-established:
  - "Probe scripts reject absolute paths, '.', '..', and empty path segments before writing."
  - "DOCX dummy deliverables are real Office Open XML packages, not plain text with a .docx suffix."
  - "Manual scorer commands are documented separately from automated dry-run validation."
requirements-completed: []
duration: 12min
completed: 2026-05-30
---

# Phase 1: Verify External Contracts And Scoring Pipeline Summary

**Verified LAB/nanoclaw contracts with a dry-run LAB result skeleton probe and documented scorer command**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-30T03:12:00Z
- **Completed:** 2026-05-30T03:24:22Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Captured verified Harvey LAB task schema, result layout, evaluator, report, and
  deliverable-matching contracts in `docs/verified-contracts.md`.
- Captured verified nanoclaw-lq DB ownership, mount, and briefing contracts in
  the same contract note.
- Added `scripts/lab_probe.py`, a deterministic dry-run probe that creates a
  LAB-compatible result skeleton and dummy expected deliverable. `.docx`
  deliverables are written as minimal valid DOCX packages so LAB's scorer can
  feed them to `pandoc`.
- Documented the optional live judge-backed scorer command in
  `docs/phase-1-manual-check.md`.

## Task Commits

Each task was committed atomically:

1. **Document verified external contracts** - `45d4389` (docs)
2. **Create deterministic LAB result-layout probe** - `19dfd47` (feat)
3. **Document optional manual scorer proof** - `b36f5d3` (docs)
4. **Harden DOCX probe output for scorer parsing** - current fix commit

## Files Created/Modified

- `docs/verified-contracts.md` - verified external contracts and implementation consequences.
- `docs/phase-1-manual-check.md` - optional scorer command and expected artifacts.
- `scripts/lab_probe.py` - dry-run LAB result skeleton generator with minimal DOCX output support.
- `pyproject.toml` - minimal Python project metadata for `uv run`.
- `uv.lock` - `uv` lockfile for the local package.
- `.gitignore` - ignores local virtualenv, caches, `.DS_Store`, and local results.
- `.planning/STATE.md` - timestamp update from phase execution start.

## Decisions Made

- No changes to `/Users/houfu/Projects/nanoclaw-lq` in Phase 1.
- Live LAB scoring remains manual because it can require judge credentials and
  external model calls.
- Dry-run validation writes only the result skeleton, dummy deliverable, and
  metrics file.

## Deviations from Plan

None - plan executed as written. `uv.lock` was also created by `uv run` and
committed with the Python probe scaffold.

## Issues Encountered

The initial probe wrote plain text for every deliverable extension. A review of
LAB's scorer showed `.docx` files are extracted through `pandoc`, so the probe
was hardened to write a minimal valid DOCX package for `.docx` deliverables.

The probe wrote the dry-run output successfully:

- `/Users/houfu/Projects/harvey-labs/results/manual-probe/output/term-sheet-issues-memo.docx`
- `/Users/houfu/Projects/harvey-labs/results/manual-probe/metrics.json`

## User Setup Required

Optional: to prove live scoring, run the command in
`docs/phase-1-manual-check.md` from the Harvey LAB repo with judge API
credentials configured.

## Self-Check: PASSED

- `uv run python -m py_compile scripts/lab_probe.py` passed.
- `uv run python scripts/lab_probe.py --harvey-root /Users/houfu/Projects/harvey-labs --task banking-finance/identify-term-sheet-issues --run-id manual-probe --dry-run` passed.
- Expected dummy deliverable exists.
- Expected `metrics.json` exists.
- `file /Users/houfu/Projects/harvey-labs/results/manual-probe-docx-check/output/term-sheet-issues-memo.docx` identifies the hardened output as `Microsoft Word 2007+`.
- Local `pandoc` extraction was not run because `pandoc` is not installed on this machine's PATH.

## Next Phase Readiness

Phase 2 can build the harness-neutral package core using the documented LAB
contracts. Phase 3 can use the documented nanoclaw contracts when implementing
the reference adapter.

---
*Phase: 01-verify-external-contracts-and-scoring-pipeline*
*Completed: 2026-05-30*
