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
TASK_LIST="${TASK_LIST:-/tmp/harvey-lab-sweep.txt}"
LOG_DIR="${LOG_DIR:-/tmp/harvey-lab-logs}"

RESULTS="$LAB_PATH/results"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
  ( cd "$HERE" && uv run python scripts/run_benchmark.py \
      --task "$task" \
      --run-id "$run_id" \
      --adapter nanoclaw \
      --nanoclaw-dir "$NANOCLAW_DIR" \
      --model "$MODEL" \
  ) >> "$LOG_DIR/$run_id.log" 2>&1
}

inventory() {
  [ -f "$TASK_LIST" ] || build_task_list
  local n=0
  while IFS= read -r task; do
    [ -n "$task" ] || continue
    is_clean "${task//\//__}" || { echo "FAILED/MISSING: $task"; n=$((n+1)); }
  done < "$TASK_LIST"
  echo "incomplete: $n"
}

export -f run_one is_clean
export RESULTS NANOCLAW_DIR MODEL HERE LOG_DIR

main() {
  mkdir -p "$LOG_DIR"
  build_task_list
  echo "sweep: $PARALLEL workers, model=$MODEL, logs -> $LOG_DIR"
  xargs -P "$PARALLEL" -I{} bash -c 'run_one "$@"' _ {} < "$TASK_LIST"
  echo "--- sweep pass complete; remaining incomplete tasks: ---"
  inventory
}

case "${1:-run}" in
  run)       main ;;
  inventory) inventory ;;
  *) echo "usage: $0 [run|inventory]" >&2; exit 2 ;;
esac
