from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class TaskSpec:
    """Parsed representation of a Harvey LAB task."""

    task_id: str
    instructions: str
    documents_dir: Path
    expected_deliverables: list[str]
    run_id: str


@dataclass
class RunResult:
    """Outcome reported by an adapter after executing a task.

    end_state must be one of: "clean", "agent_error", "timeout"
    """

    run_id: str
    end_state: str
    wall_clock_seconds: float
    # Optional metrics — None when adapter cannot provide them
    input_tokens: int | None = None
    output_tokens: int | None = None
    documents_read: int | None = None
    total_vdr_files: int | None = None
    documents_skipped: int | None = None
    documents_read_list: list[str] = field(default_factory=list)
    documents_skipped_list: list[str] = field(default_factory=list)


class Adapter(Protocol):
    """Contract for all harness adapters.

    Any class implementing run(task_spec, output_dir) -> RunResult
    satisfies this protocol without explicit inheritance.
    """

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult: ...
