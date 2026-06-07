#!/usr/bin/env bash
#
# Resumable, parallel sweep of Harvey LAB tasks through the nanoclaw adapter.
#
# Why this exists instead of `run_benchmark.py --tasks`:
#   The batch loop in run_benchmark.py is sequential and NOT crash-resumable.
#   It uses random per-run UUIDs and only writes its summary.json after the
#   whole loop finishes, so a single hard failure (e.g. a group-create shim
#   crash) aborts the run AND loses the record of everything already done.
#
#   This driver runs one task per process with a DETERMINISTIC run-id derived
#   from the task path, and skips any task already marked benchmark_status
#   "clean" in its metrics.json. Recovery is therefore just re-running this
#   script: completed tasks skip instantly, crashes touch only their own task,
#   and xargs -P keeps the rest moving.
#
#   "clean" is decided purely by deliverable presence on disk (see
#   derive_benchmark_status), so skipping on it skips only genuinely-complete
#   tasks -- a timeout/error task has missing deliverables and will re-run.
#
# Usage:
#   scripts/sweep.sh                 # run with defaults below
#   PARALLEL=2 scripts/sweep.sh      # override worker count
#   MODEL=claude-opus-4-8 scripts/sweep.sh
#
# After a run, list anything that did not complete:
#   scripts/sweep.sh inventory
#
set -uo pipefail

# --- configuration (override via environment) -------------------------------
LAB_PATH="${LAB_PATH:-$HOME/Projects/harvey-labs}"
NANOCLAW_DIR="${NANOCLAW_DIR:-$HOME/Projects/nanoclaw-lq}"
MODEL="${MODEL:-deepseek-v4-flash:cloud}"
PARALLEL="${PARALLEL:-4}"
# Per-task wall-clock timeout (seconds).
# Rationale: empirical data from 174 runs in results/ shows p99 of clean runs
# = 586.2s (n=137 clean), max = 596.1s. 600s catches p99+ while bounding
# non-deliverable stalls to a finite interval. The deliverable-gated poll
# short-circuits as soon as output files land and are size-stable, so the
# 600s ceiling only applies to tasks that produce NO deliverable (hard
# crashes, infinite loops). Tasks that finish cleanly exit well before 600s.
# Override: TIMEOUT=300 scripts/sweep.sh
TIMEOUT="${TIMEOUT:-600}"
TASK_LIST="${TASK_LIST:-/tmp/harvey-lab-sweep.txt}"
LOG_DIR="${LOG_DIR:-/tmp/harvey-lab-logs}"

RESULTS="$LAB_PATH/results"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Call the venv interpreter directly instead of `uv run`: the latter
# re-validates the env and opens uv cache files on every single invocation,
# which under parallel load exhausted the system-wide FD table (ENFILE) and
# crashed an earlier sweep ~193 tasks in. Fall back to `uv run` if absent.
PY="$HERE/.venv/bin/python"
[ -x "$PY" ] || PY="uv run python"

build_task_list() {
  find "$LAB_PATH/tasks" -name task.json \
    | sed 's#.*/tasks/##; s#/task.json$##' | sort > "$TASK_LIST"
  echo "task list: $(wc -l < "$TASK_LIST") tasks -> $TASK_LIST"
}

is_clean() {  # $1 = run_id
  local m="$RESULTS/$1/metrics.json"
  [ -f "$m" ] && grep -q '"benchmark_status": *"clean"' "$m"
}

run_one() {
  local task="$1"
  local run_id="${task//\//__}"          # area/slug -> area__slug (run-id safe)
  if is_clean "$run_id"; then
    echo "skip  $task"
    return 0
  fi
  echo "run   $task"
  ( cd "$HERE" && $PY scripts/run_benchmark.py \
      --task "$task" \
      --run-id "$run_id" \
      --adapter nanoclaw \
      --nanoclaw-dir "$NANOCLAW_DIR" \
      --model "$MODEL" \
      --timeout "$TIMEOUT" \
  ) >> "$LOG_DIR/$run_id.log" 2>&1
  # D-01 failure check: no metrics.json AND no output files = hard crash
  local m="$RESULTS/$run_id/metrics.json"
  local out_dir="$RESULTS/$run_id/output"
  if ! [ -f "$m" ] && ! { [ -d "$out_dir" ] && [ -n "$(ls -A "$out_dir" 2>/dev/null)" ]; }; then
    touch "$LOG_DIR/$run_id.failed"
  fi
  touch "$LOG_DIR/$run_id.attempted"   # D-05: always mark attempted
  # Never propagate non-zero: a single failure returning 255 makes xargs abort
  # the entire sweep. Failures are recovered by re-running (skip-on-clean).
  return 0
}

inventory() {
  [ -f "$TASK_LIST" ] || build_task_list
  local total=0
  local clean_count=0
  local incomplete=0
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
  # CI: skip header with tail -n +5 or grep -v '^[a-z]\|^---'
  echo "total: $total"
  echo "clean: $clean_count"
  echo "incomplete: $incomplete"
  echo "---"
  for p in "${paths[@]}"; do
    echo "$p"
  done
}

export -f run_one is_clean
export RESULTS NANOCLAW_DIR MODEL HERE LOG_DIR PY TIMEOUT

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

main() {
  mkdir -p "$LOG_DIR"
  # Clean up stale markers so summary reflects only this sweep pass (D-04)
  rm -f "$LOG_DIR"/*.attempted "$LOG_DIR"/*.failed 2>/dev/null || true
  build_task_list
  echo "sweep: $PARALLEL workers, model=$MODEL, logs -> $LOG_DIR"
  xargs -P "$PARALLEL" -I{} bash -c 'run_one "$@"' _ {} < "$TASK_LIST"
  echo "--- sweep pass complete; remaining incomplete tasks: ---"
  inventory
  tally_summary
  check_failures || exit 1
}

case "${1:-run}" in
  run)       main ;;
  inventory) inventory ;;
  *) echo "usage: $0 [run|inventory]" >&2; exit 2 ;;
esac
