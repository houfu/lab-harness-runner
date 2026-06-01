"""Compatibility wrapper for the primary LAB benchmark command.

This legacy entry point keeps the old nanoclaw-focused command shape while
delegating execution to scripts/run_benchmark.py so benchmark status, scoring,
report, and compare semantics stay in one implementation.
"""

from __future__ import annotations

from scripts.run_benchmark import build_parser, run_single_benchmark


def main() -> int:
    parser = build_parser()
    parser.description = __doc__
    parser.set_defaults(adapter="nanoclaw")
    args = parser.parse_args()
    summary = run_single_benchmark(args)

    for key in (
        "run_id",
        "run_dir",
        "output_dir",
        "benchmark_status",
        "raw_end_state",
        "metrics_path",
        "scores_path",
        "report_path",
        "compare_mode",
        "dashboard_paths",
    ):
        if key in summary:
            print(f"{key}: {summary[key]}")
    if "scores_path" not in summary:
        print("Scoring skipped (pass --score to invoke evaluator)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
