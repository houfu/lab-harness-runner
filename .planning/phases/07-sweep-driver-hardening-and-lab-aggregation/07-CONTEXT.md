# Phase 7: Sweep Driver Hardening And LAB Aggregation - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the post-v1.0 `scripts/sweep.sh` driver: document the `TIMEOUT` 600s
default with an observed-data rationale, make `inventory` dual-output (CI-
consumable path-list + human-readable counts), add a post-run summary line
derived from tasks attempted in this pass, wire per-run crash detection with
a non-zero exit and per-run log path on stderr, and integrate LAB's
`evaluation.compare` as an opt-in final step via `LAB_COMPARE` env var. No
new aggregation logic lives in the runner.

</domain>

<decisions>
## Implementation Decisions

### Failure detection and exit-code hardening (SWP-04)

- **D-01:** A "failed run" is defined as: after `run_one` completes, the run
  directory has **neither** a `metrics.json` nor any file in `output/`
  (the output directory is empty or absent). This captures hard crashes where
  the runner itself died — it excludes operational outcomes like timeout or
  agent_error, which still produce a `metrics.json` even without a deliverable.

- **D-02:** Tracking mechanism: `run_one` writes a per-run marker file
  `$LOG_DIR/$run_id.failed` whenever the failure condition in D-01 is met.
  This is race-free across parallel `xargs` workers (no shared state, no
  append atomicity concern). After `xargs` finishes, `sweep.sh` counts
  `.failed` marker files; if any exist, it prints each failed run's
  `$LOG_DIR/$run_id.log` path to stderr and exits non-zero. The marker files
  are written by `run_one` after every run that returns from `run_benchmark.py`,
  before the function returns 0 (which it must always do to prevent xargs abort).

- **D-03:** "No deliverable" in D-01 means `$RESULTS/$run_id/output/` either
  does not exist or contains no files. This is the same criterion
  `derive_benchmark_status` uses — deliverable presence is the clean signal.

### Post-run summary scope (SWP-03)

- **D-04:** The post-run summary line counts **only tasks run in this sweep
  pass** — skip-on-clean tasks are excluded. The summary reflects "how did
  this run go", not a cumulative total. A resume sweep that skips 140 already-
  clean tasks and runs 34 remaining tasks reports counts over those 34, not 174.

- **D-05:** Tracking attempted tasks: `run_one` always writes a
  `$LOG_DIR/$run_id.attempted` marker file after the run completes (regardless
  of outcome), reusing the same per-file marker pattern as D-02. After `xargs`
  finishes, `sweep.sh` reads each `.attempted` marker, looks up its
  `metrics.json` for `benchmark_status`, and tallies `clean` / `agent_error` /
  `timeout` / `missing_deliverable` counts. A run with no `metrics.json` (i.e.,
  a failure per D-01) is counted under `missing_deliverable` in the summary
  (it is the most informative bucket — the run produced nothing).

- **D-06:** The summary line format (from ROADMAP.md):
  `summary: clean=N agent_error=M timeout=K missing_deliverable=L`
  This is printed at the end of the `main` function, after the inventory block.

### TIMEOUT documentation (SWP-01)

- **D-07:** The `TIMEOUT` 600s default gets a header comment update in
  `scripts/sweep.sh` recording: p99 of clean runs = 586.2s (n=137), max =
  596.1s; 600s catches p99+ while bounding non-deliverable stalls; the
  deliverable-gated poll short-circuits early for tasks that finish, so the
  ceiling only applies to tasks producing no deliverable. A one-line override
  note is included (`TIMEOUT=300 scripts/sweep.sh` to cap faster).

### inventory dual-output (SWP-02)

- **D-08:** `inventory` outputs to **stdout only**, with a structured format:
  a human-readable header block first (total/clean/incomplete counts, one line
  each), then machine-readable path lines (one bare path per line, no
  `FAILED/MISSING:` prefix). A CI job consuming the path lines pipes
  `inventory` through `grep -v '^[a-z]'` or uses `tail -n +N` to skip the
  header, or the planner may emit a `---` separator between the header and path
  lines. The exact separator is Claude's discretion. The key constraint: path
  lines have no prefix so they are directly consumable by `xargs`.
  Note: the user did not explicitly discuss inventory output channels — this
  follows the ROADMAP.md spec directly. Planner may use stderr for the header
  if that yields a cleaner CI story.

### LAB_COMPARE integration (LAB-02)

- **D-09:** `LAB_COMPARE` env var triggers an opt-in final step that shells
  out to LAB's `evaluation.compare`. The env var carries the scope value
  (`task`, `area`, or `all`), mirroring `run_benchmark.py --compare`. The
  runner contains no new aggregation code — it constructs and runs a
  `uv run python -m evaluation.compare` subprocess with the appropriate flag
  (`--task`, `--area`, or `--all`) against the `$LAB_PATH/results/` directory.
  The exact task/area argument when `LAB_COMPARE=task` or `LAB_COMPARE=area`
  is Claude's discretion (likely inferred from the task list or passed as a
  separate env var — planner decides).

### Claude's Discretion

- The exact separator between the human-readable header and machine-readable
  path lines in `inventory` output (D-08). A `---` separator, blank line, or
  stderr/stdout split are all acceptable.
- Whether `LAB_COMPARE=task` infers the task from the task list or requires a
  separate `LAB_COMPARE_ARG` env var (D-09).
- Whether `.attempted` and `.failed` marker files are cleaned up between sweep
  runs, or accumulated across runs.
- The exact wording of the `TIMEOUT` header comment (D-07).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary
- `scripts/sweep.sh` — the file being hardened; all four post-v1.0 commits
  (`3a1fd89`, `17d3eb7`, `3e0dd71`, `2884ae7`) are the substrate. Read the
  current file before planning.
- `.planning/ROADMAP.md` — Phase 7 Goal / Context / Deliverables / Exit
  Criteria. The four post-v1.0 commits section documents what each commit
  contributed. The wall-clock data (174 runs, p99=586.2s, max=596.1s) is
  recorded here and is the basis for D-07.
- `.planning/REQUIREMENTS.md` v1.1 — SWP-01, SWP-02, SWP-03, SWP-04, LAB-01,
  LAB-02 are the binding requirements.
- `.planning/PROJECT.md` — "runner stays thin" and "no new aggregator in the
  runner" locked decisions. LAB-02 integration must use LAB's existing tools
  (D-09).

### LAB integration surface
- `~/Projects/harvey-labs/evaluation/compare.py` — LAB's `evaluation.compare`
  module. Accepts `--task <area/slug>`, `--area <area>`, or `--all`. Reads
  `results/` for `scores.json` + `config.json`. The runner shells out to it;
  read the top-level docstring for its CLI interface.
- `~/Projects/harvey-labs/utils/sweep.py` — LAB's own sweep utility (for
  reference; the runner does NOT use it directly).

### Existing results data (verification anchor)
- `~/Projects/harvey-labs/results/` — 174 task directories with `metrics.json`.
  The replay analysis (ROADMAP Exit Criterion) validates `inventory` against
  this data: expected 140 clean, 34 timeout, 34 incomplete.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `is_clean()` in `sweep.sh` — checks `benchmark_status: "clean"` in
  `metrics.json`. Used by skip-on-clean logic; can also be used to classify
  completed tasks in the post-run summary.
- `$LOG_DIR/$run_id.log` — already created by `run_one`'s redirect (`>> "$LOG_DIR/$run_id.log" 2>&1`).
  The per-run log path is the stderr output SWP-04 requires.
- `inventory()` — current implementation walks `$TASK_LIST` and prints
  `FAILED/MISSING: $task` for non-clean tasks. D-08 replaces the prefix with
  bare paths and adds a header block.

### Established Patterns
- "Per-file side channel" — `run_one` already returns 0 unconditionally (to
  prevent xargs abort). The per-run `.failed` / `.attempted` marker files
  extend this pattern cleanly without shared state.
- "Deterministic run_id" — `${task//\//__}` (slash to double-underscore).
  Already used; `.attempted` and `.failed` markers use the same naming.
- "Venv-direct python" — `PY="$HERE/.venv/bin/python"` with `uv run` fallback.
  The LAB_COMPARE shell-out should use the same pattern, invoking
  `uv run python -m evaluation.compare` from `$LAB_PATH`.

### Integration Points
- `run_one` → `.attempted` + `.failed` marker writes (new, D-02, D-05)
- `main()` → post-summary tally from `.attempted` markers (new, D-05, D-06)
- `main()` → `.failed` check → stderr + non-zero exit (new, D-02)
- `main()` → optional `LAB_COMPARE` shell-out (new, D-09)
- `inventory()` → dual-output rewrite (D-08)
- `TIMEOUT` header comment update (D-07)

</code_context>

<specifics>
## Specific Ideas

- The "no metrics AND no output" crash definition (D-01) is deliberate: a
  timeout run that produced no deliverable still writes `metrics.json`
  (with `end_state: timeout`, `benchmark_status: timeout`). That is an
  expected operational outcome, not a crash. The crash definition catches
  the case where `run_benchmark.py` itself died before writing anything.
- The `.attempted` + `.failed` marker pair lets the post-run summary and the
  exit-code logic share the same side channel. A run that is `.attempted` but
  not `.failed` succeeded in the D-01 sense (it produced at least one artifact).
  A run that is both `.attempted` and `.failed` is a hard crash.
- The replay analysis (ROADMAP exit criterion) can be run with the hardened
  `inventory` against the existing `~/Projects/harvey-labs/results/` data
  without a new live sweep.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

Items not discussed (user selected only failure detection and summary scope):
- `inventory` dual-output channel split — left to Claude's discretion per D-08.
- `LAB_COMPARE` task-filter granularity — left to Claude's discretion per D-09.

</deferred>

---

*Phase: 7-Sweep Driver Hardening And LAB Aggregation*
*Context gathered: 2026-06-07*
