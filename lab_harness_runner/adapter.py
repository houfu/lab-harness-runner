from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

_VALID_END_STATES = {"clean", "agent_error", "timeout"}


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

    end_state must be one of: "clean", "agent_error", "timeout".
    None on a metric field means the adapter did not measure it (distinct
    from a measured value of 0 or []).
    """

    run_id: str
    end_state: Literal["clean", "agent_error", "timeout"]
    wall_clock_seconds: float
    # Optional metrics — None when adapter cannot provide them
    input_tokens: int | None = None
    output_tokens: int | None = None
    documents_read: int | None = None
    total_vdr_files: int | None = None
    documents_skipped: int | None = None
    documents_read_list: list[str] | None = None
    documents_skipped_list: list[str] | None = None

    def __post_init__(self) -> None:
        if self.end_state not in _VALID_END_STATES:
            raise ValueError(
                f"end_state must be one of {sorted(_VALID_END_STATES)}, "
                f"got: {self.end_state!r}"
            )


class Adapter(Protocol):
    """Contract for all harness adapters.

    Any class implementing run(task_spec, output_dir) -> RunResult
    satisfies this protocol without explicit inheritance.
    """

    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult: ...
