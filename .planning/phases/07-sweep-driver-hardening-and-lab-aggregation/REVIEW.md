# Code Review: Four Post-v1.0 sweep.sh Commits

**Phase:** 07-sweep-driver-hardening-and-lab-aggregation  
**Reviewed:** 2026-06-07  
**Reviewer:** GSD executor (07-04)  
**Scope:** `scripts/sweep.sh` commits `3a1fd89`, `17d3eb7`, `3e0dd71`, `2884ae7`  
**Verification method:** `git show --stat <sha>` and `git show --patch <sha>` for each commit

---

## Overview

These four commits, all authored 2026-06-04, constitute the post-v1.0 sweep driver that
Phase 7 hardens. Together they provide: a resumable parallel sweep, FD-exhaustion
resistance, an operator-controllable timeout knob, and diagnostic stderr surfacing for
ephemeral teardown failures. They are the substrate that SWP-01..04 and LAB-01..02 build on.

---

### 3a1fd89 — feat: resumable parallel LAB sweep driver

**Date:** 2026-06-04 00:21:51 +0800  
**File:** `scripts/sweep.sh` (new file, 96 lines)  
**Diff stat:** 1 file changed, 96 insertions(+)

**What the commit changed:**

Introduced `scripts/sweep.sh` from scratch, replacing the sequential, non-resumable
`run_benchmark.py --tasks` batch loop as the production sweep driver. Core additions:

- Deterministic `run_id` derived from task path (`${task//\//__}`) instead of random UUIDs,
  making every run stable and addressable across restarts.
- `is_clean()` helper: checks for `benchmark_status: "clean"` in the run's `metrics.json`;
  `run_one()` calls it at the top of each worker to skip completed tasks.
- `xargs -P "$PARALLEL"` dispatch: each task runs in a separate process, with a
  configurable worker count (default 4).
- `inventory()` subcommand: scans all tasks and prints `FAILED/MISSING: <task>` lines
  plus an `incomplete: N` footer. (This format is superseded by Plan 07-01.)
- `main()` wiring: `build_task_list()` → `xargs` → `inventory`.
- All exported env vars: `RESULTS`, `NANOCLAW_DIR`, `MODEL`, `HERE`, `LOG_DIR`.

**The problem it solved:**

`run_benchmark.py --tasks` used random per-run UUIDs and only wrote `summary.json` after
the whole loop finished. A single crash aborted the entire batch and lost all progress
records. The driver makes each task independent: crashed tasks don't affect their
neighbours, and re-running the script resumes from where it left off (clean tasks skip
instantly).

**Notable gap (not yet fixed in this commit):** `run_one` propagated exit codes to
xargs, meaning any single failed subprocess could abort the entire sweep. This was
addressed in the next commit.

**What v1.1 Phase 7 builds on this commit:**

- SWP-01 (TIMEOUT rationale): extends the configuration block `3a1fd89` established
  with a documented empirical rationale comment.
- SWP-02 (inventory dual-output): rewrites the `inventory()` function introduced here;
  the new format replaces the `FAILED/MISSING:` prefix with bare result-directory paths.
- SWP-03 (post-run summary): extends `main()` with the `.attempted`/`.failed` marker
  accumulation pattern after the `xargs` invocation this commit defined.
- SWP-04 (non-zero exit): extends `main()` with failure detection after `xargs` returns.
- LAB-02 (LAB_COMPARE shell-out): extends `main()` with an opt-in final step.

---

### 17d3eb7 — fix: prevent FD exhaustion and xargs abort in sweep driver

**Date:** 2026-06-04 07:23:08 +0800  
**File:** `scripts/sweep.sh` (11 insertions, 2 deletions)  
**Diff stat:** 1 file changed, 11 insertions(+), 2 deletions(-)

**What the commit changed:**

Two targeted fixes, both motivated by a real production failure:

1. **`uv run python` → `$PY` (venv-direct invocation):**
   Added `PY="$HERE/.venv/bin/python"` with a fallback to `uv run python` if absent.
   Changed `run_one()` to call `$PY` instead of `uv run python`. `PY` is exported so
   xargs subshells inherit it. The comment explains why: `uv run` re-validates the
   project environment and opens several cache files (`uv_cache.json` etc.) on every
   invocation; under `xargs -P 4` with 1251 tasks this exhausted the system-wide FD
   table (ENFILE) and crashed a prior sweep at approximately 193 tasks.

2. **`return 0` at end of `run_one()`:**
   Added an explicit `return 0` so `run_one` never propagates a non-zero exit code
   to xargs. Without this, any individual task subprocess exiting 255 (the code that
   xargs treats as a signal to stop immediately) would abort the entire sweep. The
   comment notes: "Failures are recovered by re-running (skip-on-clean)."

**The problem it solved:**

A 1251-task sweep on 2026-06-04 crashed approximately 193 tasks in with `ENFILE` (too
many open files). Investigation revealed two compounding causes: `uv run` opening cache
files under parallel load, and the first xargs worker to return non-zero causing xargs
to abort. Both are fixed here.

**What v1.1 Phase 7 builds on this commit:**

- SWP-04 (non-zero exit on hard crash): the `return 0` from this commit makes the
  contract explicit. Phase 7's failure detection uses per-file `.failed` marker files
  precisely because exit codes from workers are always 0 — the only race-free side
  channel available is the filesystem.
- The `$PY` variable and its export are inherited unchanged by the hardened script.

---

### 3e0dd71 — feat: TIMEOUT knob for sweep driver

**Date:** 2026-06-04 07:34:06 +0800  
**File:** `scripts/sweep.sh` (7 insertions, 1 deletion)  
**Diff stat:** 1 file changed, 7 insertions(+), 1 deletion(-)

**What the commit changed:**

Added `TIMEOUT="${TIMEOUT:-600}"` to the configuration block with a four-line comment
explaining its semantics. Wired `--timeout "$TIMEOUT"` into the `run_benchmark.py`
invocation inside `run_one()`. Added `TIMEOUT` to the `export` line.

The comment in this commit reads:
```
# Per-task poll timeout (seconds). The poll short-circuits as soon as
# deliverables land and are size-stable, so this only caps the wait on tasks
# that produce NO deliverable -- lowering it stops those failures from
# stalling a worker for the full default 600s.
```

**The problem it solved:**

Previously `run_one()` called `run_benchmark.py` without a `--timeout` argument. When
`run_benchmark.py` uses its default timeout, the sweep had no operator control over
how long a non-deliverable task would stall a worker. Adding the `TIMEOUT` env var
lets operators dial down the ceiling (e.g. `TIMEOUT=300 scripts/sweep.sh`) for
exploratory runs where a shorter stall is acceptable.

**Relationship to ROADMAP figures:**

The 600s default was chosen against observed wall-clock data, referenced in the ROADMAP
as "p99 = 586.2s (n=137 clean), max = 596.1s". RESEARCH Pitfall 1 notes the live data
as of 2026-06-07 yields p99 = 601.1s, max = 601.1s for 136 clean runs — the ROADMAP
figures appear to be from an earlier snapshot. Plan 07-01 replaced the brief comment
from this commit with the full empirically-grounded rationale block (SWP-01).

**What v1.1 Phase 7 builds on this commit:**

- SWP-01 (TIMEOUT rationale): replaces the brief comment here with a multi-line block
  citing p99/max/n figures plus a one-line override example.
- The `TIMEOUT` variable, default value, and `--timeout "$TIMEOUT"` wiring are
  preserved unchanged.

---

### 2884ae7 — diag: surface destroy-shim stderr in ephemeral teardown warning

**Date:** 2026-06-04 08:19:41 +0800  
**File:** `lab_harness_runner/nanoclaw_adapter.py` (5 insertions, 1 deletion)  
**Diff stat:** 1 file changed, 5 insertions(+), 1 deletion(-)

**What the commit changed:**

This commit modifies `nanoclaw_adapter.py`, not `sweep.sh`. It targets
`EphemeralNanoclawAdapter._destroy_group()` in the `run()` method's teardown path.

Previously the teardown warning printed only the exception object:
```python
f"manual cleanup may be needed: {exc}"
```

After the fix, it also extracts and appends the shim's stderr:
```python
shim_stderr = getattr(exc, "stderr", None)
detail = f": {shim_stderr.strip()}" if shim_stderr else ""
f"manual cleanup may be needed: {exc}{detail}"
```

**The problem it solved:**

The teardown warning was not actionable. The actual cause of destroy failures is
typically `EACCES` on a busy bind-mount (the live nanoclaw daemon respawns the
container between teardown attempts), but the exit code alone does not convey this.
By including `exc.stderr` the warning now shows the raw shim error message, letting
an operator diagnose the failure without attaching a debugger.

**Relationship to the sweep driver:**

This commit is not a `sweep.sh` change but is grouped with the sweep driver commits
because it targets the same production-scale sweep path. The ephemeral teardown
warning is most visible during parallel sweeps where many containers are created and
destroyed concurrently.

**What v1.1 Phase 7 builds on this commit:**

No direct Phase 7 changes build on `2884ae7`. The diagnostic surfacing is inherited
as-is. It is a prerequisite for diagnosing live sweep problems that SWP-03/SWP-04
monitoring would expose (the post-run summary and non-zero exit make sweep failures
more visible, and the improved warning makes teardown failures diagnosable once found).

---

## What v1.1 Hardens

The following table maps each Phase 7 change to the commit(s) it extends:

| Phase 7 Change | Req ID | Extends Commit(s) | What It Adds |
|----------------|--------|-------------------|--------------|
| TIMEOUT 600s rationale comment | SWP-01 | `3e0dd71` | Replaces the 4-line comment with a multi-line block citing p99=586.2s, n=137, max=596.1s and a one-line override example |
| `inventory()` dual-output rewrite | SWP-02 | `3a1fd89` | Removes `FAILED/MISSING:` prefix; adds human-readable header (total/clean/incomplete) + `---` separator + bare result-directory paths (CI-consumable via `xargs` or `tail -n +5`) |
| Per-run `.attempted`/`.failed` markers + post-run summary | SWP-03 | `3a1fd89`, `17d3eb7` | `run_one()` writes `$run_id.attempted` and `$run_id.failed` (D-01/D-05); `main()` tallies `benchmark_status` from each `.attempted` marker's `metrics.json` and prints `summary: clean=N agent_error=M timeout=K missing_deliverable=L` (D-06) |
| Non-zero exit on hard crash | SWP-04 | `17d3eb7` | After xargs, counts `.failed` markers; prints per-run log path to stderr for each; exits non-zero if any failures. Relies on `run_one` always returning 0 (established in `17d3eb7`) |
| LAB_COMPARE shell-out | LAB-02 | `3a1fd89` | Adds opt-in `LAB_COMPARE=task|area|all` env var that shells out to `cd $LAB_PATH && uv run python -m evaluation.compare` as the final step of `main()` |
| destroy-shim stderr (no change) | — | `2884ae7` | Inherited as-is; `2884ae7`'s diagnostic improvement was complete on commit |

---

## Observations

1. All four commits were authored on the same day (2026-06-04) in a short window (~8 hours),
   suggesting they followed a single production sweep incident (the ~193-task ENFILE crash).

2. Commits `3a1fd89`, `17d3eb7`, and `3e0dd71` form a logical sequence: introduce the driver,
   fix the FD exhaustion crash, then add the timeout knob. They could have been squashed but
   were kept separate, which makes the git history self-documenting.

3. Commit `2884ae7` is the only one that does not touch `sweep.sh`. Its diff is clean and
   contained; the exception attribute access (`getattr(exc, "stderr", None)`) is safe because
   it falls back to `None` for exceptions that do not carry `stderr`.

4. The ROADMAP description references commits in a different order from their actual
   chronological order (`3a1fd89`, `17d3eb7`, `3e0dd71`, `2884ae7`). The chronological
   order matches the description exactly.
