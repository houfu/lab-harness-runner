# Phase 1 Manual Scorer Check

The automated Phase 1 validation stops at dry-run result creation because
`evaluation.run_eval` uses an external LLM judge and may require paid API
credentials from the Harvey LAB `.env`.

After running the dry-run probe, this optional command proves the live scorer
path:

```bash
cd /Users/houfu/Projects/harvey-labs && uv run python -m evaluation.run_eval --run-id manual-probe --task banking-finance/identify-term-sheet-issues --judge-model claude-sonnet-4-6
```

Expected artifacts:

- `/Users/houfu/Projects/harvey-labs/results/manual-probe/scores.json`
- `/Users/houfu/Projects/harvey-labs/results/manual-probe/report.html`

Expected caveat: the dummy deliverable is not meant to pass the legal rubric.
This check proves the directory shape, evaluator command, score writing, and
report generation path.
