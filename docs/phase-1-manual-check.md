# Phase 1 Manual Scorer Check

The automated Phase 1 validation stops at dry-run result creation because
`evaluation.run_eval` uses an external LLM judge and may require paid API
credentials from the Harvey LAB `.env`.

After running the dry-run probe, this optional command proves the live scorer
path:

```bash
cd <harvey-labs> && uv run python -m evaluation.run_eval --run-id manual-probe --task banking-finance/identify-term-sheet-issues --judge-model claude-sonnet-4-6
```

Expected artifacts:

- `<harvey-labs>/results/manual-probe/scores.json`
- `<harvey-labs>/results/manual-probe/report.html`

Expected caveat: the dummy deliverable is not meant to pass the legal rubric.
For `.docx` deliverables, `scripts/lab_probe.py` writes a minimal valid DOCX
package so LAB's `pandoc` extraction path can read it when `pandoc` is installed
in the LAB runtime.

This check proves the directory shape, evaluator command, document extraction,
score writing, and report generation path.
