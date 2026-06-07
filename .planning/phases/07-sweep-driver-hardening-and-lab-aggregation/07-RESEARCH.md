# Phase 7: Sweep Driver Hardening And LAB Aggregation - Research

**Researched:** 2026-06-07
**Domain:** Bash shell scripting, LAB integration, sweep orchestration
**Confidence:** HIGH

## Summary

Phase 7 is a pure shell-script hardening and integration exercise. The substrate
(`scripts/sweep.sh`) is fully written and live. All four post-v1.0 commits are on
main and working. The four operator-visible gaps (undocumented TIMEOUT rationale,
CI-hostile `inventory` output format, no post-run summary line, uninformative exit
code) are well-understood and small in scope. The LAB integration surface
(`evaluation.compare`) is verified to accept `--task`, `--area`, and `--all` flags
and reads `scores.json` + `config.json` from each run directory.

One critical gap discovered during research: the runner-produced result directories
do NOT contain `config.json`. LAB's `evaluation.compare` skips any run directory
without `config.json`, so `LAB_COMPARE` integration will silently produce empty
output unless either (a) the runner writes a `config.json` alongside `metrics.json`,
or (b) the planner scopes LAB_COMPARE documentation to note this limitation. This
is not covered by CONTEXT.md decisions and should be flagged for the planner.

The replay analysis on real data found 136 clean + 34 timeout = 170 total task
directories (not 174 as stated in ROADMAP — the ROADMAP figure is 4 higher). This
discrepancy must be documented accurately in RESEARCH. The wall-clock p99 for clean
runs computed from live data is 601.1s (ROADMAP says 586.2s, likely from an earlier
state of results). The 600s TIMEOUT default is slightly below the current observed
p99 on the live data set, not above it. The planner should use the live-computed
figures, not the ROADMAP figures.

**Primary recommendation:** Implement the four `sweep.sh` changes as small, targeted
edits. The per-file marker pattern (`.attempted` / `.failed`) is the correct
mechanism for xargs-safe parallel tracking. The LAB_COMPARE shell-out requires
investigating the `config.json` gap before the integration can work.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** A "failed run" is: after `run_one` completes, the run directory has neither
a `metrics.json` nor any file in `output/`. This captures hard crashes where the
runner died; it excludes operational outcomes like timeout or agent_error (which still
produce `metrics.json`).

**D-02:** Tracking: `run_one` writes `$LOG_DIR/$run_id.failed` when D-01 condition is
met. Race-free across parallel xargs workers. After xargs, `sweep.sh` counts `.failed`
files; if any exist, prints each failed `$LOG_DIR/$run_id.log` to stderr and exits
non-zero. `run_one` must always return 0.

**D-03:** "No deliverable" means `$RESULTS/$run_id/output/` either doesn't exist or
contains no files. Same criterion as `derive_benchmark_status`.

**D-04:** Post-run summary counts only tasks run in THIS sweep pass (skip-on-clean
tasks excluded). A resume sweep over 34 remaining tasks reports over those 34.

**D-05:** `run_one` always writes `$LOG_DIR/$run_id.attempted` after every run
completes (regardless of outcome), using the same per-file marker pattern as D-02.
After xargs, `sweep.sh` reads each `.attempted` marker, looks up its `metrics.json`
for `benchmark_status`, tallies clean/agent_error/timeout/missing_deliverable. A run
with no `metrics.json` counts under `missing_deliverable`.

**D-06:** Summary line format: `summary: clean=N agent_error=M timeout=K missing_deliverable=L`
Printed at the end of `main()`, after the inventory block.

**D-07:** TIMEOUT 600s header comment records: p99 of clean runs = 586.2s (n=137),
max = 596.1s; 600s catches p99+ while bounding non-deliverable stalls; deliverable-
gated poll short-circuits early for tasks that finish. One-line override note included.
*(See Pitfall 1 below — live data yields different figures; use canonical ROADMAP
figures per D-07 unless planner chooses to update.)*

**D-08:** `inventory` outputs to stdout only, structured format: human-readable header
block first (total/clean/incomplete counts), then machine-readable bare path lines
(no `FAILED/MISSING:` prefix). Separator between header and paths is Claude's
discretion (a `---` line, blank line, or stderr/stdout split are all acceptable).

**D-09:** `LAB_COMPARE` env var triggers shell-out to LAB's `evaluation.compare`. The
env var value is the scope (`task`, `area`, or `all`). Shell-out uses
`uv run python -m evaluation.compare` from `$LAB_PATH`. Task/area argument when
`LAB_COMPARE=task` or `LAB_COMPARE=area` is Claude's discretion.

### Claude's Discretion

- Exact separator between human-readable header and machine-readable path lines in
  `inventory` output (D-08).
- Whether `LAB_COMPARE=task` infers the task from the task list or requires a separate
  `LAB_COMPARE_ARG` env var (D-09).
- Whether `.attempted` and `.failed` marker files are cleaned up between sweep runs,
  or accumulated across runs.
- Exact wording of the TIMEOUT header comment (D-07).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SWP-01 | `sweep.sh` defaults documented; TIMEOUT default has rationale grounded in existing `results/` wall-clock data | Wall-clock data verified from 170 live result directories. p99=601.1s, max=601.1s for 136 clean runs. ROADMAP uses n=137, p99=586.2s (earlier snapshot). D-07 specifies ROADMAP figures as canonical. |
| SWP-02 | `sweep.sh inventory` output is both machine-readable (one path per line, `xargs`-suitable) and human-readable (per-task status counts) | Existing `inventory()` function is 8 lines. D-08 specifies the new format precisely. No external library needed. |
| SWP-03 | `sweep.sh` post-run summary prints clean/agent_error/timeout/missing_deliverable counts from `metrics.json` files | D-04/D-05/D-06 specify the mechanism (`.attempted` marker files + `metrics.json` tally). All `metrics.json` files use `benchmark_status` key. |
| SWP-04 | Sweep failures exit non-zero with per-run error log path on stderr | D-01/D-02 specify the mechanism (`.failed` marker files + `run_one` always returns 0). Pattern is clean and race-free. |
| LAB-01 | `sweep.sh` produces output compatible with LAB's existing batch-summary tool | `evaluation.compare` reads `scores.json` + `config.json`. Runner produces `scores.json` but NOT `config.json` — compatibility gap exists (see Pitfall 2). |
| LAB-02 | After a sweep, `sweep.sh` can invoke LAB's comparison/aggregation as final step (opt-in via `LAB_COMPARE` env var) | `evaluation.compare` CLI verified: `--task`, `--area`, `--all`. D-09 specifies shell-out pattern. Blocked by `config.json` gap unless addressed. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-run failure detection | sweep.sh / shell | — | xargs parallelism constraint: run_one must return 0; per-file markers are the only race-free channel |
| Post-run summary tallying | sweep.sh / shell | — | Summary reads `.attempted` markers + `metrics.json` from LAB results tree; purely file-based |
| `inventory` dual-output | sweep.sh / shell | — | Reformatting existing `inventory()` function output |
| TIMEOUT documentation | sweep.sh / shell | — | Header comment update only |
| LAB_COMPARE shell-out | sweep.sh / shell | harvey-labs (evaluate.compare) | sweep.sh constructs and executes subprocess; LAB module does all aggregation |
| Code review document | planning artifact | — | Documentation of four commits; no code change |
| Replay analysis | operator-executed | — | Run `sweep.sh inventory` against existing results; compare counts |

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| bash | 3.2.57 (macOS) | sweep.sh implementation language | Already in use; macOS ships GNU bash 3.x |
| uv | 0.11.8 | Python subprocess invocation for LAB_COMPARE shell-out | Already established in project (`PY` venv-direct pattern) |
| xargs (BSD) | macOS built-in | Parallel worker dispatch | Already in use with `-P` flag |

No new packages are installed in this phase. All changes are to `scripts/sweep.sh` (bash) and
planning documents. The `## Package Legitimacy Audit` section is omitted — no packages to audit.

---

## Architecture Patterns

### System Architecture Diagram

```
sweep.sh main()
  │
  ├─ build_task_list() → $TASK_LIST
  │
  ├─ xargs -P $PARALLEL
  │     └─ run_one() [per task, parallel]
  │           ├─ is_clean($run_id) → skip if true
  │           ├─ run_benchmark.py (subprocess, stdout → $run_id.log)
  │           ├─ [D-01 failure check] → write $run_id.failed if no metrics.json AND no output/
  │           └─ write $run_id.attempted  [always]
  │
  ├─ inventory() [after xargs]
  │     ├─ header block: total / clean / incomplete counts  →  stdout
  │     ├─ [separator: --- or blank line]
  │     └─ bare paths for incomplete tasks  →  stdout
  │
  ├─ post-run summary tally [D-05/D-06]
  │     ├─ read each $run_id.attempted
  │     ├─ look up $RESULTS/$run_id/metrics.json → benchmark_status
  │     └─ print: summary: clean=N agent_error=M timeout=K missing_deliverable=L
  │
  ├─ exit-code hardening [D-02]
  │     ├─ count $LOG_DIR/*.failed
  │     ├─ if any: print $run_id.log paths to stderr
  │     └─ exit 1
  │
  └─ [opt-in] LAB_COMPARE shell-out [D-09]
        └─ cd $LAB_PATH && uv run python -m evaluation.compare --{scope}
```

### Recommended File Changes
```
scripts/
└── sweep.sh         # all changes land here; ~50-80 new lines total

.planning/phases/07-sweep-driver-hardening-and-lab-aggregation/
├── REVIEW.md        # code review of 4 post-v1.0 commits (planning artifact)
└── REPLAY.md        # replay analysis results (or inline in plan summary)
```

### Pattern 1: Per-file Side Channel (D-02 / D-05)

**What:** `run_one` writes `$LOG_DIR/$run_id.attempted` and optionally
`$LOG_DIR/$run_id.failed` as empty files after each run. The main function
counts them via glob after `xargs` finishes.

**When to use:** Any xargs-parallel scenario where you need per-run state
without shared memory or atomic appends.

**Example:**
```bash
run_one() {
  local task="$1"
  local run_id="${task//\//__}"
  if is_clean "$run_id"; then echo "skip  $task"; return 0; fi

  echo "run   $task"
  ( cd "$HERE" && $PY scripts/run_benchmark.py \
      --task "$task" --run-id "$run_id" \
      --adapter nanoclaw --nanoclaw-dir "$NANOCLAW_DIR" \
      --model "$MODEL" --timeout "$TIMEOUT" \
  ) >> "$LOG_DIR/$run_id.log" 2>&1

  # D-01 failure check: no metrics.json AND no output files = hard crash
  local m="$RESULTS/$run_id/metrics.json"
  local out_dir="$RESULTS/$run_id/output"
  if ! [ -f "$m" ] && ! { [ -d "$out_dir" ] && [ -n "$(ls -A "$out_dir" 2>/dev/null)" ]; }; then
    touch "$LOG_DIR/$run_id.failed"
  fi
  touch "$LOG_DIR/$run_id.attempted"   # D-05: always mark attempted
  return 0   # NEVER propagate non-zero — xargs abort prevention
}
```

### Pattern 2: Post-run Summary Tally (D-05/D-06)

**What:** After `xargs`, iterate `.attempted` marker files, read `benchmark_status`
from each run's `metrics.json`, and accumulate counts.

**Example:**
```bash
tally_summary() {
  local clean=0 agent_error=0 timeout=0 missing=0
  for marker in "$LOG_DIR"/*.attempted; do
    [ -f "$marker" ] || continue
    local run_id
    run_id="$(basename "$marker" .attempted)"
    local m="$RESULTS/$run_id/metrics.json"
    if [ ! -f "$m" ]; then
      missing=$((missing+1))
      continue
    fi
    local status
    status="$(grep -o '"benchmark_status": *"[^"]*"' "$m" | grep -o '"[^"]*"$' | tr -d '"')"
    case "$status" in
      clean)   clean=$((clean+1)) ;;
      timeout) timeout=$((timeout+1)) ;;
      agent_error) agent_error=$((agent_error+1)) ;;
      *)       missing=$((missing+1)) ;;
    esac
  done
  echo "summary: clean=$clean agent_error=$agent_error timeout=$timeout missing_deliverable=$missing"
}
```

### Pattern 3: Inventory Dual-Output (D-08)

**What:** Print human-readable header block to stdout, then separator, then
bare path lines (no prefix) to stdout. CI strips header with `grep -v '^[a-z]'`
or `tail -n +N`.

**Example:**
```bash
inventory() {
  [ -f "$TASK_LIST" ] || build_task_list
  local total=0 clean_count=0 incomplete=0
  local paths=()
  while IFS= read -r task; do
    [ -n "$task" ] || continue
    total=$((total+1))
    if is_clean "${task//\//__}"; then
      clean_count=$((clean_count+1))
    else
      incomplete=$((incomplete+1))
      paths+=("$RESULTS/${task//\//__}")
    fi
  done < "$TASK_LIST"
  # Human-readable header
  echo "total: $total"
  echo "clean: $clean_count"
  echo "incomplete: $incomplete"
  echo "---"
  # Machine-readable bare paths
  for p in "${paths[@]}"; do echo "$p"; done
}
```

### Pattern 4: Exit-Code Hardening (D-02)

**What:** After `xargs` finishes, count `.failed` marker files. If any exist,
print the corresponding `.log` path to stderr for each, then exit 1.

**Example:**
```bash
check_failures() {
  local failed=0
  for marker in "$LOG_DIR"/*.failed; do
    [ -f "$marker" ] || continue
    failed=$((failed+1))
    local run_id
    run_id="$(basename "$marker" .failed)"
    echo "$LOG_DIR/$run_id.log" >&2
  done
  [ "$failed" -eq 0 ]  # returns 0 if clean, 1 if any failures
}
```

### Pattern 5: LAB_COMPARE Shell-Out (D-09)

**What:** If `LAB_COMPARE` is set, run `evaluation.compare` as a final step from
`$LAB_PATH`, using the scope value to select the flag.

**Example:**
```bash
run_lab_compare() {
  case "$LAB_COMPARE" in
    task)
      local arg="${LAB_COMPARE_ARG:-}"
      [ -n "$arg" ] || { echo "LAB_COMPARE=task requires LAB_COMPARE_ARG=<area/slug>" >&2; return 1; }
      ( cd "$LAB_PATH" && uv run python -m evaluation.compare --task "$arg" )
      ;;
    area)
      local arg="${LAB_COMPARE_ARG:-}"
      [ -n "$arg" ] || { echo "LAB_COMPARE=area requires LAB_COMPARE_ARG=<area>" >&2; return 1; }
      ( cd "$LAB_PATH" && uv run python -m evaluation.compare --area "$arg" )
      ;;
    all)
      ( cd "$LAB_PATH" && uv run python -m evaluation.compare --all )
      ;;
    *)
      echo "LAB_COMPARE must be task|area|all (got: $LAB_COMPARE)" >&2; return 1
      ;;
  esac
}
```

### Anti-Patterns to Avoid

- **Appending to a shared file from parallel workers:** `echo "fail" >> shared.txt` under
  xargs -P has TOCTOU/truncation risk on BSD/macOS. Use per-file marker files instead
  (the established project pattern).
- **Returning non-zero from `run_one`:** Makes xargs abort the entire sweep on the first
  failure. `run_one` MUST always return 0.
- **Using `export -f` with bash 3.x functions referencing local arrays:** Bash 3.x (macOS)
  does not support `local` arrays in all contexts passed via `export -f`. Arrays in
  `inventory()` should be tested; if an issue arises, replace with a temp file pattern.
- **Relying on `evaluation.compare` without `config.json`:** The tool's `collect_runs()`
  skips any directory missing `config.json`. Runner results currently lack this file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel worker result aggregation | Shared counter file with locking | Per-file `.attempted`/`.failed` markers | Race-free on macOS BSD filesystem; already established pattern |
| LAB comparison/scoring | New aggregator in sweep.sh | `evaluation.compare` shell-out | "Runner stays thin" locked decision; LAB already does this |
| `benchmark_status` classification | New status logic | Read from existing `metrics.json` | Status already written by `derive_benchmark_status` in the adapter |

---

## Common Pitfalls

### Pitfall 1: ROADMAP Wall-Clock Figures vs. Live Data
**What goes wrong:** D-07 specifies the TIMEOUT header comment should record
p99=586.2s, max=596.1s, n=137. Live data (as of 2026-06-07) from
`~/Projects/harvey-labs/results/` yields: 136 clean runs, p99=601.1s, max=601.1s.
The 600s TIMEOUT is actually at or BELOW the observed p99, not above it. The
ROADMAP figures appear to be from an earlier state of the results.
**Why it happens:** The results directory has grown/changed since ROADMAP was written.
**How to avoid:** The planner should use D-07's canonical figures (ROADMAP) in the
comment since that is the locked decision, but note the live discrepancy. Total
results count is 170, not 174 as stated in ROADMAP (which may include 4 area
directories in the count).
**Warning signs:** Exit criterion says "confirm 140 clean + 34 timeout = 174 total".
Live data shows 136 clean + 34 timeout = 170.

### Pitfall 2: LAB_COMPARE Compatibility Gap (LAB-01)
**What goes wrong:** `evaluation.compare.collect_runs()` silently skips run
directories that lack `config.json`. The runner's `run_benchmark.py` writes
`metrics.json` and `scores.json` but NOT `config.json`. Running `LAB_COMPARE=all`
against runner-produced results will produce empty comparison output with no error.
**Why it happens:** `config.json` is a LAB-native convention (contains model, task,
run_id, reasoning_effort, etc.) that the runner's result_builder never adopted.
**How to avoid:** The planner must decide: (a) scope the LAB_COMPARE integration
to use only scores.json-bearing runs from native LAB, or (b) have the
`LAB_COMPARE` documentation note the gap explicitly, or (c) treat LAB-01 as
requiring a separate `config.json` write in the runner (out of scope per CONTEXT).
Option (b) is most consistent with the locked "runner stays thin" decision.
**Warning signs:** `LAB_COMPARE=all` produces empty output or "no runs found".

### Pitfall 3: Bash 3.x Array Limitations (macOS)
**What goes wrong:** macOS ships bash 3.2.57. Bash 3.x does not support
associative arrays (`declare -A`). The `inventory()` rewrite uses indexed arrays
for path accumulation — this works in bash 3.x. But if `inventory()` is exported
via `export -f` and called from xargs subshells, local array behavior can be
surprising.
**Why it happens:** `sweep.sh` uses `export -f` for `run_one` and `is_clean`.
`inventory()` is called from main, not from xargs, so this is not an issue for the
current design. Do not move `inventory()` into the xargs invocation.
**Warning signs:** "syntax error" or unexpected behavior when running sweep.sh
with the new `inventory()` containing arrays.

### Pitfall 4: Glob Expansion When No `.attempted` Files Exist
**What goes wrong:** In bash, `for marker in "$LOG_DIR"/*.attempted` expands to
the literal string `*.attempted` if no files match. The `[ -f "$marker" ]`
guard inside the loop prevents false-positive processing, but the guard must
be present.
**Why it happens:** BSD/GNU bash glob does not fail silently for no-match by
default (unless `nullglob` is set).
**Warning signs:** Error or spurious output on first sweep run before any
`.attempted` markers exist.

### Pitfall 5: LAB_COMPARE Working Directory
**What goes wrong:** `evaluation.compare` uses `BENCH_ROOT = Path(__file__).resolve().parent.parent`
to locate `results/`. This is correct when invoked as `cd $LAB_PATH && uv run python -m evaluation.compare`.
If invoked from a different working directory, it still resolves correctly because
`__file__` is the installed module path. The `cd "$LAB_PATH"` subshell is still
required because `uv run` discovers the project from `pyproject.toml` in `$LAB_PATH`.
**How to avoid:** Always run the shell-out inside `( cd "$LAB_PATH" && uv run python -m evaluation.compare ... )`.

---

## Runtime State Inventory

> This phase is not a rename/refactor/migration phase. However, it does create new
> runtime state (marker files) that accumulates between runs.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `.attempted` and `.failed` markers in `$LOG_DIR` (default `/tmp/harvey-lab-logs`) | Accumulate across runs unless explicitly cleaned. Planner must document cleanup policy (Claude's discretion per CONTEXT). |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | `LAB_COMPARE`, `LAB_COMPARE_ARG` (new env vars introduced by this phase) | Code-only; no secrets involved |
| Build artifacts | None | None |

**Nothing found in categories** "live service config", "OS-registered state", "secrets/env vars" (beyond new env vars added by this phase).

---

## Code Examples

### Current sweep.sh inventory() — baseline
```bash
# Source: scripts/sweep.sh (verified, lines 85-93)
inventory() {
  [ -f "$TASK_LIST" ] || build_task_list
  local n=0
  while IFS= read -r task; do
    [ -n "$task" ] || continue
    is_clean "${task//\//__}" || { echo "FAILED/MISSING: $task"; n=$((n+1)); }
  done < "$TASK_LIST"
  echo "incomplete: $n"
}
```

### evaluation.compare CLI (verified)
```python
# Source: ~/Projects/harvey-labs/evaluation/compare.py, lines 1-14 (verified)
"""
Usage:
    uv run python -m evaluation.compare --task funds-asset-management/respond-to-comment-memo
    uv run python -m evaluation.compare --area funds-asset-management
    uv run python -m evaluation.compare --all
    uv run python -m evaluation.compare --all --save-images
"""
# collect_runs() skips any run directory without config.json (verified line 94)
```

### metrics.json benchmark_status key (verified)
```bash
# Pattern already used by is_clean():
grep -q '"benchmark_status": *"clean"' "$m"

# Extended pattern for tally (all status values observed in live data):
# "clean", "timeout" — these are the two values in the 170-run live dataset
# "agent_error" and "missing_deliverable" are possible per adapter contract
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `uv run python` per task | `$HERE/.venv/bin/python` direct | commit 17d3eb7 | Eliminated ENFILE FD exhaustion at ~193 parallel tasks |
| Random UUID run-ids | `${task//\//__}` deterministic | commit 3a1fd89 | Enables skip-on-clean resumption |
| Sequential `run_benchmark.py --tasks` | `xargs -P` parallel | commit 3a1fd89 | 4x+ throughput for 1251-task sweeps |
| No exit code from sweep | All failures silent via `return 0` | — | Phase 7 SWP-04 addresses this |
| Human-only inventory | `FAILED/MISSING:` prefix lines | commit 3a1fd89 | Phase 7 SWP-02 removes prefix for CI consumability |

**Deprecated/outdated:**
- `FAILED/MISSING:` prefix on inventory lines: replaced by bare paths in Phase 7 (SWP-02)

---

## Open Questions (RESOLVED)

1. **LAB-01 / LAB_COMPARE with no config.json**
   - What we know: `evaluation.compare` requires `config.json` in each run directory.
     Runner results have no `config.json`. `LAB_COMPARE=all` will produce empty output.
   - What's unclear: Does the plan scope LAB-01 as "output format is compatible" (true,
     since scores.json is present) but LAB_COMPARE only works on LAB-native runs? Or
     does the plan add a minimal `config.json` write to `run_benchmark.py`?
   - Recommendation: Scope LAB_COMPARE to use `--all` against LAB-native results (not
     runner-produced ones) and document in the LAB_COMPARE header comment. This is
     consistent with the "runner stays thin" principle. Do not add config.json in this
     phase unless the planner explicitly decides to.
   - **RESOLVED:** Implement option (b) — document the config.json gap in `docs/adapter-guide.md`.
     LAB_COMPARE is scoped to LAB-native results only. Plan 07-03 Task 2 writes the
     docs section. No config.json write added to the runner (consistent with "runner stays thin").

2. **ROADMAP figures vs. live data (exit criterion)**
   - What we know: ROADMAP exit criterion says "140 clean + 34 timeout = 174 total".
     Live data shows 136 clean + 34 timeout = 170 total.
   - What's unclear: Was 174 an earlier snapshot? Are 4 of the 170 task-result
     directories area-level (not task-level)?
   - Recommendation: The replay analysis plan should run `sweep.sh inventory` against
     live data and report actual figures. Document the live figure as the correct one.
     The exit criterion should be updated to match live data.
   - **RESOLVED:** Plans use live-measured figures (170 total, 136 clean, 34 timeout).
     Plan 07-04 Task 2 runs `sweep.sh inventory` against `~/Projects/harvey-labs/results/`
     and records actual output in REPLAY.md, explicitly reconciling the stale ROADMAP 174 figure.
     The TIMEOUT comment in Plan 07-01 uses the ROADMAP-locked p99=586.2s figure per D-07.

3. **Marker file cleanup policy**
   - What we know: `.attempted` and `.failed` files accumulate in `$LOG_DIR`.
     If `LOG_DIR=/tmp/harvey-lab-logs` (the default), they persist across sweep runs.
     A second resume sweep will see `.attempted` markers from the first sweep, causing
     the post-run summary to count previously-run tasks.
   - What's unclear: Should `main()` delete `*.attempted` and `*.failed` at the start
     of each run? Or accumulate them?
   - Recommendation: Delete both at the start of `main()` before the `xargs` invocation.
     This makes the summary reflect only the current pass. The skip-on-clean logic
     (D-04) explicitly excludes skipped tasks anyway.
   - **RESOLVED:** `main()` deletes `*.attempted` and `*.failed` at the start of each
     sweep pass (before the `xargs` invocation). Plan 07-02 Task 2 action implements this.
     Summary counts reflect only the current pass (D-04 alignment).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| bash | sweep.sh | ✓ | 3.2.57 (macOS) | — |
| uv | LAB_COMPARE shell-out | ✓ | 0.11.8 | `python -m evaluation.compare` if venv active |
| xargs (BSD) | parallel dispatch | ✓ | macOS built-in | — |
| harvey-labs/evaluation/compare.py | LAB-02 | ✓ | verified at path | — |
| $HOME/Projects/harvey-labs/results/ | Replay analysis | ✓ | 170 dirs with metrics.json | — |
| bats (bash test framework) | sweep.sh unit tests | ✗ | — | Manual smoke test + replay analysis |

**Missing dependencies with no fallback:**
- bats: no shell unit test framework available. Sweep.sh changes are tested via
  replay analysis against real data (not automated unit tests).

**Missing dependencies with fallback:**
- None beyond bats (which is excluded by project convention — no shell tests exist).

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from config.json — treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml `[tool.uv.build-backend]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SWP-01 | TIMEOUT comment in sweep.sh contains p99 data | manual-only | `grep 'p99\|586\|600' scripts/sweep.sh` | ✅ (grep check) |
| SWP-02 | inventory output has no `FAILED/MISSING:` prefix; paths consumable by xargs | manual-only / replay | `bash scripts/sweep.sh inventory \| grep -v '^[a-z]\|^---'` | ✅ (via replay) |
| SWP-03 | summary line printed with correct format | manual-only | `bash scripts/sweep.sh 2>&1 \| grep '^summary:'` | ✅ (format check) |
| SWP-04 | non-zero exit when `.failed` markers exist | manual-only | `touch /tmp/harvey-lab-logs/test.failed && bash scripts/sweep.sh inventory; echo "exit: $?"` | ✅ (manual) |
| LAB-01 | runner output compatible with evaluate.compare (via scores.json) | manual-only | docs/notes only | ✅ (doc) |
| LAB-02 | LAB_COMPARE shell-out invokes evaluation.compare | manual-only | `LAB_COMPARE=all bash scripts/sweep.sh 2>&1` | ✅ (smoke) |

**Note:** `sweep.sh` is pure bash and has no automated test harness (bats not installed).
All SWP/LAB requirements are validated via:
1. Replay analysis: `sweep.sh inventory` against existing 170-task results
2. Code review: planner REVIEW.md document
3. Manual smoke tests noted above

### Wave 0 Gaps
- None — no new Python modules being added. Existing test suite (pytest) covers
  unchanged Python code. sweep.sh changes have no automated test coverage by
  project convention.

---

## Security Domain

> This phase makes no network calls, handles no user authentication, introduces no
> new secrets, and modifies only a local bash orchestration script. ASVS categories
> V2/V3/V4/V6 do not apply. V5 is limited to env var validation (LAB_COMPARE
> value must be one of task|area|all).

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (minimal) | Case-match on LAB_COMPARE value; print error to stderr and return 1 for invalid values |
| V6 Cryptography | no | — |

**Known Threat Patterns for sweep.sh:**

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via task path | Tampering | Task paths come from `find` on LAB tasks dir; not user-supplied at runtime |
| Arbitrary env var expansion | Tampering | `LAB_COMPARE_ARG` carries user-supplied task/area name; quote all expansions in shell-out |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ROADMAP wall-clock figures (p99=586.2s, n=137) are the canonical figures for D-07's TIMEOUT comment, even though live data differs | User Constraints D-07 | Comment will cite figures that don't match current live data; minor documentation inaccuracy |
| A2 | The 4-task discrepancy (174 vs 170) in ROADMAP exit criterion is due to stale data, not a methodology difference | Open Questions | Replay analysis may fail its exit criterion; planner should update criterion to match live count |
| A3 | `evaluation.compare` requires `config.json` in the run directory to include a run in comparisons | Pitfall 2 / LAB-01 | If wrong, LAB_COMPARE integration works without changes |
| A4 | Bash 3.x indexed arrays in `inventory()` work correctly when `inventory()` is called from `main()` (not from xargs) | Architecture Patterns | Array syntax may fail on macOS bash 3.x; fall back to temp file accumulation |

---

## Sources

### Primary (HIGH confidence)
- `scripts/sweep.sh` — read and verified in session; all function bodies and current
  limitations confirmed
- `.planning/phases/07-sweep-driver-hardening-and-lab-aggregation/07-CONTEXT.md` —
  all locked decisions D-01 through D-09 verified
- `~/Projects/harvey-labs/evaluation/compare.py` — CLI interface and `collect_runs()`
  skip condition verified in session
- `~/Projects/harvey-labs/results/` — 170 task directories with `metrics.json`
  verified; wall-clock stats computed from live data

### Secondary (MEDIUM confidence)
- `git log --oneline` for commits 3a1fd89, 17d3eb7, 3e0dd71, 2884ae7 — commit
  messages and dates verified; diff stats verified

### Tertiary (LOW confidence / ASSUMED)
- None — all critical claims were directly verified from source files or computed
  from live data in this session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all tools verified installed
- Architecture: HIGH — all patterns derived from locked CONTEXT.md decisions and
  verified source code
- Pitfalls: HIGH — config.json gap verified directly from source; bash 3.x version
  confirmed; glob behavior well-established

**Research date:** 2026-06-07
**Valid until:** 2026-07-07 (stable domain — bash scripting, existing files)
