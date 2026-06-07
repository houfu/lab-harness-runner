# Replay Analysis: Hardened inventory() Against Live results/

**Phase:** 07-sweep-driver-hardening-and-lab-aggregation  
**Executed:** 2026-06-07  
**Executor:** GSD agent (07-04 Task 2)  
**Data source:** `~/Projects/harvey-labs/results_ollamadeepseekv4flas_20260607.zip`  
  (runner-produced result directories; zip archived from the live results tree)  
**Script version:** `scripts/sweep.sh` post Plan 07-01 (TIMEOUT rationale + dual-output inventory)

---

## 1. Live Metrics Counts (re-measured)

All counts below were produced by running the commands specified in the plan against the
170 runner-produced `metrics.json` files extracted from the zip archive. They are
measured values, not copied from prior documentation.

### (a) Total metrics.json files

```
find "$HOME/Projects/harvey-labs/results" -maxdepth 2 -name metrics.json | wc -l
```

**Result: 170**

The zip contains 1422 `metrics.json` files total, but 1252 of those are nested inside
LAB-native run directories (at depth > 2). The runner-produced files are at
`results/<run_id>/metrics.json` (exactly depth 2), which is the structure `is_clean()`
and `inventory()` in `sweep.sh` operate on. Only the 170 flat runner-produced files are
relevant to the sweep driver replay.

### (b) Clean runs

```
grep -rl '"benchmark_status": *"clean"' "$HOME/Projects/harvey-labs/results"/*/metrics.json | wc -l
```

**Result: 136**

### (c) Timeout runs

```
grep -rl '"benchmark_status": *"timeout"' "$HOME/Projects/harvey-labs/results"/*/metrics.json | wc -l
```

**Result: 34**

### Summary of live metrics counts

| Metric | Count |
|--------|-------|
| Total result directories (runner-produced) | 170 |
| benchmark_status = "clean" | 136 |
| benchmark_status = "timeout" | 34 |
| Other statuses | 0 |
| Total accounted | 170 |

---

## 2. Hardened inventory() Output

The following was produced by running `bash scripts/sweep.sh inventory` with the
pre-built task list (1251 tasks from `~/Projects/harvey-labs/tasks/`) and the
results tree from the extracted zip:

```
$ TASK_LIST=/tmp/harvey-lab-sweep-replay.txt \
  LAB_PATH=/tmp/harvey-replay-tmp \
  bash scripts/sweep.sh inventory
```

**Header block (human-readable, first 4 lines):**

```
total: 1251
clean: 136
incomplete: 1115
---
```

**Path lines (machine-readable, lines 5+):**

```
/tmp/harvey-replay-tmp/results/antitrust-competition__prepare-antitrust-risk-assessment
/tmp/harvey-replay-tmp/results/arbitration-international-dispute-resolution__draft-interim-measures-request
/tmp/harvey-replay-tmp/results/arbitration-international-dispute-resolution__draft-markup-of-proposed-interim-order
/tmp/harvey-replay-tmp/results/arbitration-international-dispute-resolution__draft-objections-to-document-production-request
/tmp/harvey-replay-tmp/results/arbitration-international-dispute-resolution__draft-statement-of-defense
... (1115 lines total)
```

### Observations

- **Header is human-readable:** three counts plus `---` separator, consistent with D-08.
- **Path lines carry no `FAILED/MISSING:` prefix.** Verified: `grep "FAILED/MISSING"` on
  the path lines returns 0 matches.
- **Path lines are bare `$RESULTS/<run_id>` strings** — no quotes, no flags, no prefix.
  They are directly consumable by `xargs`, e.g.:
  ```bash
  bash scripts/sweep.sh inventory | tail -n +5 | xargs -I{} ls "{}"
  ```
- **CI skip pattern works:** `tail -n +5` strips the header block entirely, leaving
  only bare paths.

---

## 3. Why incomplete = 1115, Not 34

The inventory `incomplete` count (1115) differs from the `timeout` count (34). This is
expected and correct, not an error.

`inventory()` iterates over the **full task list** (`~/Projects/harvey-labs/tasks/`,
1251 tasks). A task is "incomplete" if it does not have a `results/<run_id>/metrics.json`
with `benchmark_status: "clean"`. This includes:

- 34 tasks that ran and timed out (have `metrics.json` with `benchmark_status: "timeout"`)
- 1081 tasks that have never been run at all (no result directory exists for them)

The 170 runner-produced result directories represent only a subset of the 1251 tasks in
the LAB task corpus. The remaining 1081 tasks were never swept.

| Category | Count | How counted |
|----------|-------|-------------|
| Tasks that ran and are clean | 136 | `grep '"benchmark_status": *"clean"'` on flat metrics.json |
| Tasks that ran and timed out | 34 | `grep '"benchmark_status": *"timeout"'` on flat metrics.json |
| Tasks that ran, total | 170 | flat metrics.json count |
| Tasks never run | 1081 | 1251 total tasks − 170 run |
| Tasks inventory marks incomplete | 1115 | 34 timeout + 1081 never run |
| Total tasks in LAB corpus | 1251 | `find tasks/ -name task.json | wc -l` |

---

## 4. Reconciliation: Stale ROADMAP Figure (174) vs. Live Data (170)

The ROADMAP Phase 7 context states:

> "174 task directories in `~/Projects/harvey-labs/results/` with `metrics.json`."
> "140 benchmark-clean, 34 timeout."

The exit criterion repeats: "140 clean + 34 timeout = 174 total; 34 incomplete."

The live data measured in this replay shows:

| Field | ROADMAP figure | Live figure (2026-06-07) | Delta |
|-------|---------------|--------------------------|-------|
| Total result directories | 174 | 170 | −4 |
| benchmark_status = "clean" | 140 | 136 | −4 |
| benchmark_status = "timeout" | 34 | 34 | 0 |

Per RESEARCH.md Pitfall 1, the ROADMAP figures are from an **earlier state of the results
tree**. The 4-directory discrepancy likely reflects 4 clean runs that were present when
the ROADMAP was written but whose result directories were subsequently removed or not
included in the zip archive. The timeout count (34) is consistent.

**The corrected exit-criterion figures, based on live data:**

- Total runner-produced result directories: **170**
- `benchmark_status = "clean"`: **136**
- `benchmark_status = "timeout"`: **34**
- `inventory incomplete` (over full 1251-task corpus): **1115**

The ROADMAP's stale 174/140 figure should be treated as a documentation artifact of an
earlier state; the authoritative figures for Phase 7 verification are 170/136/34 as
measured here.

---

## 5. Verification of CI Consumability

The hardened `inventory()` output satisfies all of D-08's requirements:

| Requirement (D-08) | Verified |
|--------------------|---------|
| Output goes to stdout only | Yes — no stderr output from inventory |
| Human-readable header block first (total/clean/incomplete counts) | Yes — lines 1-3 |
| Machine-readable bare path lines (no FAILED/MISSING: prefix) | Yes — 0 prefixed lines found |
| Separator between header and paths | Yes — `---` on line 4 (per 07-01 decision) |
| Path lines xargs-consumable | Yes — bare `$RESULTS/<run_id>` strings with no spaces or special characters |
| Header skippable by CI | Yes — `tail -n +5` or `grep -v '^[a-z]\|^---'` both work |

---

## 6. Conclusion

The hardened `inventory()` (Plan 07-01) behaves correctly against the live results data:

- It correctly identifies 136 clean runs (matching the direct `grep` count).
- It correctly marks 1115 tasks as incomplete (34 timeout runs + 1081 never-run tasks).
- Path lines carry no `FAILED/MISSING:` prefix and are consumable by `xargs` directly.
- The human-readable header (total/clean/incomplete) and `---` separator function as
  designed.

The ROADMAP exit criterion (174 total, 140 clean, 34 timeout) is stale by 4 runs.
The corrected exit criterion is **170 total, 136 clean, 34 timeout** as measured here.
