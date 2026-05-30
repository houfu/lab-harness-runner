from __future__ import annotations

from lab_harness_runner.adapter import Adapter, RunResult, TaskSpec

# Wave 2 modules — imported here for public API convenience.
# Each import is guarded independently so that already-created modules
# are available even when sibling modules are not yet created.
try:
    from lab_harness_runner.task_reader import read_task
except ImportError:
    pass  # task_reader not yet created

try:
    from lab_harness_runner.result_builder import build_result_dir
except ImportError:
    pass  # result_builder not yet created

try:
    from lab_harness_runner.metrics import write_metrics
except ImportError:
    pass  # metrics not yet created

try:
    from lab_harness_runner.evaluator import score_run
except ImportError:
    pass  # evaluator not yet created

__all__ = [
    "Adapter",
    "TaskSpec",
    "RunResult",
    "read_task",
    "build_result_dir",
    "write_metrics",
    "score_run",
]
