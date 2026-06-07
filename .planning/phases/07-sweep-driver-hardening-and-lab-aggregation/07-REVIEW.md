---
phase: 07-sweep-driver-hardening-and-lab-aggregation
reviewed: 2026-06-07T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - scripts/sweep.sh
  - docs/adapter-guide.md
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-06-07
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed `scripts/sweep.sh` (sweep-driver hardening) and the new `LAB_COMPARE`
section of `docs/adapter-guide.md`. Verified bash-version assumptions against the
actual environment (default `/bin/bash` is **GNU bash 3.2.57**, and the shebang
is `#!/usr/bin/env bash`, so 3.2 is the realistic interpreter on this macOS
target), traced status-string values back to the Python source, and tested
empty-array / quoting / xargs behaviors in a 3.2 shell.

Two BLOCKERs stand out and both are provable, not stylistic:

1. `inventory()` crashes with an "unbound variable" error under `set -u` on
   bash 3.2 whenever the sweep is fully clean (empty `paths` array) — i.e. the
   success case aborts the script.
2. `tally_summary` matches the wrong status string. The runner emits
   `benchmark_status: "error"` (confirmed in `lab_harness_runner/status.py`),
   but the script only has a `agent_error)` case — so the `agent_error` arm is
   dead code and every real failed task is silently bucketed as
   `missing_deliverable`, corrupting the summary line for a 1251-task sweep.

Plus several doc-vs-code contradictions around `LAB_COMPARE` ordering and a
missing traversal-validation that the adapter-guide itself mandates.

## Critical Issues

### CR-01: `inventory()` aborts with "unbound variable" on a fully-clean sweep (bash 3.2)

**File:** `scripts/sweep.sh:117`
**Issue:** Under `set -u` (set at line 29) on bash 3.2 — the default `/bin/bash`
on macOS and the interpreter `#!/usr/bin/env bash` will resolve to here — an
empty array expanded as `"${paths[@]}"` is treated as an unbound variable and
the script exits 1. When every task is clean, `paths=()` stays empty, so the
loop at line 117 kills `inventory()`. This is exactly the "everything
succeeded" path the resumable design is built to reach. It also fires when
`scripts/sweep.sh inventory` is run after a complete sweep. Reproduced:

```
$ /bin/bash -c 'set -u; a=(); for x in "${a[@]}"; do :; done'
bash: a[@]: unbound variable   (exit 1)
```

This is silent at the call site: `inventory` is the last meaningful line of a
successful pass, so the operator sees the script die right after "sweep pass
complete" with a cryptic unbound-variable error and may assume the sweep
itself failed.

**Fix:** Use the count guard before iterating, which is bash-3.2-safe:
```bash
  if [ "${#paths[@]}" -gt 0 ]; then
    for p in "${paths[@]}"; do
      echo "$p"
    done
  fi
```
(`${#paths[@]}` on an empty array is `0` and does NOT trip `set -u`.)

### CR-02: `tally_summary` miscounts failures — matches `agent_error` but runner emits `error`

**File:** `scripts/sweep.sh:138-143`
**Issue:** The `case` arms are `clean)`, `timeout)`, `agent_error)`, and
`*) missing`. But `benchmark_status` is never `agent_error`. Per
`lab_harness_runner/status.py:24-29`, `derive_benchmark_status` only ever sets
`benchmark_status` to one of `"clean"`, `"timeout"`, or `"error"`. Consequences:

- The `agent_error)` arm (line 141) is **dead code** — it can never match.
- Every genuinely failed task (deliverables missing, non-timeout) carries
  `benchmark_status: "error"`, falls through to the `*)` default at line 142,
  and is counted as `missing_deliverable`. The `agent_error` tally is always 0
  and the `missing_deliverable` tally is inflated by every error task.

The summary line printed at line 145 — the headline result of a 1251-task
sweep — is therefore wrong: it understates errors and overstates missing
deliverables.

**Fix:** Match the actual emitted value (`error`) and route it correctly:
```bash
    case "$status" in
      clean)   clean=$((clean+1)) ;;
      timeout) timeout=$((timeout+1)) ;;
      error)   agent_error=$((agent_error+1)) ;;
      *)       missing=$((missing+1)) ;;
    esac
```
Keep the `error` label internal but consider renaming the counter/output token
to `error=` so the summary line vocabulary matches `metrics.json`. Confirm the
canonical set in `status.py` before finalizing.

## Warnings

### WR-01: `run_lab_compare` validation runs AFTER the full sweep — contradicts documented behavior

**File:** `scripts/sweep.sh:191-196`, `docs/adapter-guide.md:295-301`
**Issue:** The docs state that a missing `LAB_COMPARE_ARG` or an invalid
`LAB_COMPARE` value makes the script "print an error to stderr and return
non-zero **without running the sweep**" / "exit non-zero **without running any
task**" (adapter-guide.md:296-301). The implementation calls `run_lab_compare`
at line 196 — the **last** step in `main()`, after `xargs` has already executed
every task. So an operator who typos `LAB_COMPARE=tsak` on a 1251-task run
discovers the error only after the entire (potentially hours-long) sweep
finishes. The code does not match its own contract.

**Fix:** Hoist a validation-only check to the top of `main()` (before
`build_task_list`/`xargs`). Either factor the `case` validation into a
`validate_lab_compare` helper called first, or have `run_lab_compare` accept a
`--check-only` mode invoked up front:
```bash
main() {
  validate_lab_compare || exit 1   # fail fast, before any task runs
  mkdir -p "$LOG_DIR"
  ...
  run_lab_compare
}
```

### WR-02: `check_failures || exit 1` silently skips `run_lab_compare` on any failure

**File:** `scripts/sweep.sh:195-196`
**Issue:** Line 195 exits the script with status 1 whenever any `.failed`
marker exists. Because `run_lab_compare` is line 196, the opt-in LAB comparison
**never runs** if even one task hard-crashed — which on a 1251-task sweep is
likely. A user who set `LAB_COMPARE=all` expecting a comparison at the end gets
neither the comparison nor any indication that it was skipped because of an
unrelated single-task failure. This interaction is undocumented in the
adapter-guide LAB_COMPARE section.

**Fix:** Decide intent and make it explicit. If comparison should still run on
partial success, run it before the failure-gated exit:
```bash
  run_lab_compare
  check_failures || exit 1
```
Otherwise document that `LAB_COMPARE` is skipped when any task failed. Capture
`check_failures`' result without exiting immediately if both must run.

### WR-03: `LAB_COMPARE_ARG` is passed to `evaluation.compare` with no traversal/path validation

**File:** `scripts/sweep.sh:164-171`
**Issue:** `LAB_COMPARE_ARG` flows straight into `--task "$arg"` / `--area
"$arg"`. It is argv-quoted (no shell injection — verified), but the
adapter-guide explicitly requires rejecting absolute and traversal paths for
"deliverables, run IDs, task IDs, batch IDs, or harness group IDs"
(adapter-guide.md:111-113). A value like `LAB_COMPARE_ARG=../../something` is
forwarded unchecked; whether it is dangerous depends entirely on LAB's
`evaluation.compare`, which the runner treats as an unmodified third party. The
script bypasses a contract it documents for itself.

**Fix:** Validate before shelling out, mirroring the project's
`_reject_unsafe_relative_path` intent:
```bash
case "$arg" in
  /*|*..*) echo "LAB_COMPARE_ARG must be a relative area/slug path" >&2; return 1 ;;
esac
```

### WR-04: Unquoted `$PY` relies on word-splitting and breaks if the path contains spaces

**File:** `scripts/sweep.sh:54-55,76`
**Issue:** `PY` is either `$HERE/.venv/bin/python` (a single path that may
contain spaces if `$HERE` does) or the literal string `"uv run python"` (which
*must* word-split into three argv tokens). Line 76 uses bare `$PY` to satisfy
the `uv run python` case via word-splitting. This is intentionally fragile: if
the checkout path contains a space, the `.venv` branch breaks; the two branches
have incompatible quoting requirements. On a stable CI path this is latent, but
it is a correctness footgun.

**Fix:** Use an array to hold the interpreter invocation so both forms quote
correctly:
```bash
if [ -x "$HERE/.venv/bin/python" ]; then PY=("$HERE/.venv/bin/python");
else PY=(uv run python); fi
...
( cd "$HERE" && "${PY[@]}" scripts/run_benchmark.py ... )
```
Note: arrays do not survive `export` to the xargs subshell, so if `run_one`
needs `PY` it must be reconstructed inside the function rather than relying on
the exported scalar at line 123.

## Info

### IN-01: Stale comment hint references behavior that may mislead CI scrapers

**File:** `scripts/sweep.sh:112`
**Issue:** The comment suggests CI strip the header with
`tail -n +5 or grep -v '^[a-z]\|^---'`. After CR-01's fix the body section is
conditional, but the header lines (`total:`/`clean:`/`incomplete:`/`---`) are
always 4 lines, so `tail -n +5` is correct only when there is at least one
incomplete path. On a fully-clean sweep `tail -n +5` yields empty output, which
is the intended "nothing incomplete" result — acceptable, but worth a one-line
clarification that empty output means zero incomplete.
**Fix:** Tighten the comment to state that an empty post-header section means
zero incomplete tasks.

### IN-02: `is_clean` grep duplicates status-parsing logic also in `tally_summary`

**File:** `scripts/sweep.sh:65,137`
**Issue:** Two different ad-hoc grep expressions parse `benchmark_status` from
`metrics.json` (line 65 uses `grep -q '"benchmark_status": *"clean"'`; line 137
uses a two-stage `grep -o`). They must stay in sync with the JSON formatting
emitted by `metrics.py` (`json.dumps(..., indent=2)` — verified to produce one
space after the colon). Any change to serialization (e.g. `separators` or
sort_keys) silently breaks both. Low risk today; flagged as a coupling/
duplication smell.
**Fix:** Factor a single `read_benchmark_status() { ... }` helper used by both
`is_clean` and `tally_summary`, or parse with the project's Python so the
contract lives in one place.

---

_Reviewed: 2026-06-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
