# Phase 7: Sweep Driver Hardening And LAB Aggregation - Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 1 modified file + 2 planning artifacts
**Analogs found:** 1 / 1 (self-analog — only `scripts/sweep.sh` changes)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/sweep.sh` | utility / orchestrator | batch, event-driven (xargs parallel) | `scripts/sweep.sh` itself (current state) | exact — self-modification |
| `.planning/phases/07-.../REVIEW.md` | planning artifact | — | none (documentation only) | n/a |
| `.planning/phases/07-.../REPLAY.md` | planning artifact | — | none (documentation only) | n/a |

---

## Pattern Assignments

### `scripts/sweep.sh` (utility, batch orchestrator)

**Analog:** `scripts/sweep.sh` current state (lines 1–112, read in full above)

This is a self-modification. All new code must follow the patterns already established in the file. The five additions map onto five concrete sub-patterns below.

---

#### Sub-pattern A: TIMEOUT header comment (D-07)

**Location to modify:** lines 37–40 (the `TIMEOUT` config block)

**Current pattern** (lines 37–40):
```bash
# Per-task poll timeout (seconds). The poll short-circuits as soon as
# deliverables land and are size-stable, so this only caps the wait on tasks
# that produce NO deliverable -- lowering it stops those failures from
# stalling a worker for the full default 600s.
TIMEOUT="${TIMEOUT:-600}"
```

**New pattern (replace comment block):**
```bash
# Per-task poll timeout (seconds).
# Rationale: p99 of clean runs = 586.2s (n=137), max = 596.1s. 600s catches
# p99+ while bounding non-deliverable stalls. The deliverable-gated poll
# short-circuits early for tasks that finish, so the ceiling only applies to
# tasks that produce no deliverable (timeouts, hard crashes).
# Override: TIMEOUT=300 scripts/sweep.sh
TIMEOUT="${TIMEOUT:-600}"
```

---

#### Sub-pattern B: Per-file marker writes in `run_one` (D-02, D-05)

**Location to modify:** after line 82 (the `return 0` in `run_one`)

**Established patterns from current file:**
- `run_id="${task//\//__}"` — deterministic run-id (line 66)
- `>> "$LOG_DIR/$run_id.log" 2>&1` — per-run log path (line 79)
- `return 0` always — xargs abort prevention (line 82)
- `is_clean "$run_id"` uses `local m="$RESULTS/$1/metrics.json"` (lines 60–62)

**New code to insert (between line 79 and current line 81 comment):**
```bash
  # D-01 failure check: no metrics.json AND no output files = hard crash
  local m="$RESULTS/$run_id/metrics.json"
  local out_dir="$RESULTS/$run_id/output"
  if ! [ -f "$m" ] && ! { [ -d "$out_dir" ] && [ -n "$(ls -A "$out_dir" 2>/dev/null)" ]; }; then
    touch "$LOG_DIR/$run_id.failed"
  fi
  touch "$LOG_DIR/$run_id.attempted"   # D-05: always mark attempted
```

**Key constraints from existing code:**
- `run_one` MUST end with `return 0` (line 82 pattern — xargs abort prevention)
- Use `local` for all new variables (consistent with lines 65–66)
- The `$RESULTS`, `$LOG_DIR` variables are already exported (line 96)

---

#### Sub-pattern C: `inventory` dual-output rewrite (D-08)

**Location to modify:** lines 85–93 (full `inventory()` function replacement)

**Current pattern (lines 85–93):**
```bash
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

**Established patterns to preserve:**
- `[ -f "$TASK_LIST" ] || build_task_list` — lazy task list init (line 86)
- `while IFS= read -r task; do` — safe line-by-line file read (line 88)
- `[ -n "$task" ] || continue` — skip blank lines (line 89)
- `is_clean "${task//\//__}"` — reuse existing helper (line 90)

**New pattern (replace entire function):**
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
  # Human-readable header (CI: pipe through `grep -v '^[a-z]'` or `tail -n +4` to skip)
  echo "total: $total"
  echo "clean: $clean_count"
  echo "incomplete: $incomplete"
  echo "---"
  # Machine-readable bare paths (no prefix — directly consumable by xargs)
  for p in "${paths[@]}"; do echo "$p"; done
}
```

**Bash 3.x note (macOS):** Indexed arrays (`local paths=()`) work in bash 3.x when called from `main()`, not from xargs. `inventory()` is called from `main()`, so this is safe. Do NOT move `inventory()` into the xargs invocation.

---

#### Sub-pattern D: Post-run summary tally in `main()` (D-05, D-06)

**Location to modify:** inside `main()` after the `xargs` line (line 102) and after the `inventory` call (line 104)

**Established patterns from current file:**
- `"$(grep -o ..."` — inline grep for JSON value (used by `is_clean` at line 61)
- `$((n+1))` — arithmetic in bash 3.x (line 92)
- Glob guard pattern: globs that may produce no matches need `[ -f "$marker" ] || continue`

**New code — `tally_summary()` function (add before `main()`):**
```bash
tally_summary() {
  local clean=0 agent_error=0 timeout=0 missing=0
  for marker in "$LOG_DIR"/*.attempted; do
    [ -f "$marker" ] || continue          # guard: no-match glob expands to literal
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
      clean)       clean=$((clean+1)) ;;
      timeout)     timeout=$((timeout+1)) ;;
      agent_error) agent_error=$((agent_error+1)) ;;
      *)           missing=$((missing+1)) ;;
    esac
  done
  echo "summary: clean=$clean agent_error=$agent_error timeout=$timeout missing_deliverable=$missing"
}
```

**Call site in `main()` (after `inventory`):**
```bash
  tally_summary
```

**Marker cleanup in `main()` (before `xargs`, after `mkdir -p "$LOG_DIR"`):**
```bash
  # Clean up stale markers so summary reflects only this sweep pass (D-04)
  rm -f "$LOG_DIR"/*.attempted "$LOG_DIR"/*.failed 2>/dev/null || true
```

---

#### Sub-pattern E: Exit-code hardening in `main()` (D-02)

**Location to modify:** end of `main()`, after `tally_summary`

**Established patterns:**
- `echo ... >&2` — stderr output (implicit in error-reporting convention)
- `exit 1` — non-zero exit (bash convention)
- Same glob guard pattern as sub-pattern D

**New code — `check_failures()` function (add before `main()`):**
```bash
check_failures() {
  local failed=0
  for marker in "$LOG_DIR"/*.failed; do
    [ -f "$marker" ] || continue
    failed=$((failed+1))
    local run_id
    run_id="$(basename "$marker" .failed)"
    echo "FAILED: $LOG_DIR/$run_id.log" >&2
  done
  [ "$failed" -eq 0 ]   # returns 0 if no failures, 1 if any
}
```

**Call site in `main()` (after `tally_summary`, as final statement):**
```bash
  check_failures || exit 1
```

---

#### Sub-pattern F: LAB_COMPARE shell-out in `main()` (D-09)

**Established patterns:**
- `( cd "$HERE" && $PY scripts/run_benchmark.py ... )` — subshell for subprocess (line 72–79)
- `uv run python` fallback from `PY` venv-direct pattern (lines 50–51)
- `case "${1:-run}" in` — case statement for value dispatch (line 107)

**New code — `run_lab_compare()` function (add before `main()`):**
```bash
run_lab_compare() {
  [ -n "${LAB_COMPARE:-}" ] || return 0
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
      # Note: evaluation.compare requires config.json in each run directory.
      # Runner-produced results lack config.json; use LAB_COMPARE=all only against
      # LAB-native results (harvey-labs/results/). See RESEARCH.md Pitfall 2.
      ( cd "$LAB_PATH" && uv run python -m evaluation.compare --all )
      ;;
    *)
      echo "LAB_COMPARE must be task|area|all (got: $LAB_COMPARE)" >&2; return 1
      ;;
  esac
}
```

**Call site in `main()` (after `check_failures || exit 1`):**
```bash
  run_lab_compare
```

**New exports needed (add to the `export` line at line 96):**
```bash
export -f run_one is_clean
export RESULTS NANOCLAW_DIR MODEL HERE LOG_DIR PY TIMEOUT LAB_PATH
```
(`LAB_PATH` is already set at line 32 but needs to be in `export` for `run_lab_compare`; it is already in the local scope of `main()` so this is a minor addition.)

---

## Shared Patterns

### xargs-safe parallel state (no shared mutable files)
**Source:** `scripts/sweep.sh` lines 80–83 (`run_one` return 0 comment)
**Apply to:** all new code inside `run_one`
```bash
# Never propagate non-zero: a single failure returning 255 makes xargs abort
# the entire sweep. Failures are recovered by re-running (skip-on-clean).
return 0
```
Any new code in `run_one` that detects failures MUST write to per-file markers (`touch "$LOG_DIR/$run_id.failed"`) rather than a shared file, and MUST NOT change the `return 0`.

### Glob no-match guard
**Source:** bash 3.x behavior (no `nullglob` set in current script)
**Apply to:** `tally_summary()` and `check_failures()` — any `for marker in "$LOG_DIR"/*.ext` loop
```bash
[ -f "$marker" ] || continue
```

### Venv-direct python / subshell pattern
**Source:** `scripts/sweep.sh` lines 50–51, 72–79
**Apply to:** `run_lab_compare()` shell-out
```bash
PY="$HERE/.venv/bin/python"
[ -x "$PY" ] || PY="uv run python"
# ...
( cd "$LAB_PATH" && uv run python -m evaluation.compare ... )
```
The LAB shell-out uses `uv run` explicitly (not `$PY`) because it needs `uv` to discover `$LAB_PATH/pyproject.toml`.

### `local` variable declaration
**Source:** `scripts/sweep.sh` lines 65–66
**Apply to:** all new bash functions
```bash
local task="$1"
local run_id="${task//\//__}"
```
All variables in new functions must be declared `local`. No globals leaked from function scope.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `.planning/phases/07-.../REVIEW.md` | planning artifact | n/a | Documentation only; no code analog exists |
| `.planning/phases/07-.../REPLAY.md` | planning artifact | n/a | Documentation only; no code analog exists |

---

## Assembly Order for `scripts/sweep.sh`

The planner should apply changes in this order to minimize diff complexity:

1. **Lines 37–40:** Replace TIMEOUT comment block (sub-pattern A)
2. **Line 85–93:** Replace `inventory()` function body (sub-pattern C)
3. **Before `main()` (~line 98):** Insert `tally_summary()` function (sub-pattern D)
4. **Before `main()` (~line 98):** Insert `check_failures()` function (sub-pattern E)
5. **Before `main()` (~line 98):** Insert `run_lab_compare()` function (sub-pattern F)
6. **Inside `run_one()` (after line 79, before line 81 comment):** Insert `.failed`/`.attempted` marker writes (sub-pattern B)
7. **Inside `main()` (after `mkdir -p "$LOG_DIR"`, line 99):** Insert marker cleanup `rm -f` line (sub-pattern D)
8. **Inside `main()` (after `inventory` call):** Add `tally_summary` call (sub-pattern D)
9. **End of `main()`:** Add `check_failures || exit 1` (sub-pattern E)
10. **End of `main()`:** Add `run_lab_compare` call (sub-pattern F)
11. **Export line (line 96):** Add `LAB_PATH` to exported vars if needed (sub-pattern F)

---

## Metadata

**Analog search scope:** `scripts/` directory
**Files scanned:** 1 (`scripts/sweep.sh`, 112 lines, read in full)
**Pattern extraction date:** 2026-06-07
