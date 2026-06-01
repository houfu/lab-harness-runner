from __future__ import annotations

from pathlib import Path

from lab_harness_runner.adapter import RunResult, TaskSpec
from lab_harness_runner.task_reader import _reject_unsafe_relative_path


def derive_benchmark_status(
    task_spec: TaskSpec,
    output_dir: Path,
    result: RunResult,
    adapter_name: str,
) -> dict[str, object]:
    """Derive benchmark-facing status from deliverables and raw adapter state."""
    missing_deliverables: list[str] = []
    for name in task_spec.expected_deliverables:
        deliverable_path = _reject_unsafe_relative_path(name, "expected_deliverable")
        if not (output_dir / deliverable_path).exists():
            missing_deliverables.append(name)

    expected_deliverables_present = not missing_deliverables
    raw_end_state = result.end_state
    if expected_deliverables_present:
        benchmark_status = "clean"
    elif raw_end_state == "timeout":
        benchmark_status = "timeout"
    else:
        benchmark_status = "error"

    completion_signal = {
        "clean": "STATUS:DONE",
        "agent_error": "STATUS:ERROR",
        "timeout": "",
    }[raw_end_state]

    return {
        "task_id": task_spec.task_id,
        "run_id": result.run_id,
        "adapter": adapter_name,
        "raw_end_state": raw_end_state,
        "benchmark_status": benchmark_status,
        "terminal_status_seen": raw_end_state in {"clean", "agent_error"},
        "completion_signal": completion_signal,
        "expected_deliverables_present": expected_deliverables_present,
        "missing_deliverables": missing_deliverables,
        "output_dir": str(output_dir),
    }
