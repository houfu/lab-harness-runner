from __future__ import annotations

from lab_harness_runner.adapter import Adapter, RunResult, TaskSpec

# Wave 2 modules — imported here for public API convenience.
# These modules will be created in subsequent plans; until then,
# importing lab_harness_runner directly will raise ImportError for
# any of the four names below. Importing from lab_harness_runner.adapter
# always works.
try:
    from lab_harness_runner.task_reader import read_task
    from lab_harness_runner.result_builder import build_result_dir
    from lab_harness_runner.metrics import write_metrics
    from lab_harness_runner.evaluator import score_run
except ImportError:
    pass  # Wave 2 modules not yet created

__all__ = [
    "Adapter",
    "TaskSpec",
    "RunResult",
    "read_task",
    "build_result_dir",
    "write_metrics",
    "score_run",
]
