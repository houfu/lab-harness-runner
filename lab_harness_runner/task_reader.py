from __future__ import annotations

import json
import os
from pathlib import Path

from lab_harness_runner.adapter import TaskSpec


def _reject_unsafe_relative_path(value: str, name: str) -> Path:
    """Validate that value is a safe relative path with no traversal segments.

    Raises ValueError for absolute paths or paths containing "", ".", or "..".
    """
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} contains an unsafe path segment: {value}")
    return path


def _lab_path(override: Path | None = None) -> Path:
    """Return the Harvey LAB root directory.

    Resolution order:
    1. override if provided
    2. HARVEY_LAB_PATH env var
    3. Path.home() / "Projects" / "harvey-labs"
    """
    if override is not None:
        return override
    env = os.environ.get("HARVEY_LAB_PATH")
    if env:
        return Path(env)
    return Path.home() / "Projects" / "harvey-labs"


def read_task(lab_path: Path, task_id: str, run_id: str) -> TaskSpec:
    """Read task.json and return a TaskSpec.

    Args:
        lab_path: Root directory of the Harvey LAB installation.
        task_id: Slash-separated relative task path, e.g. "area/slug".
        run_id: Unique identifier for this run.

    Returns:
        TaskSpec populated from task.json.

    Raises:
        ValueError: If task_id contains path traversal characters or is absolute.
        FileNotFoundError: If task.json does not exist at the expected path.
        KeyError: If "instructions" key is missing from task.json.
    """
    task_path = _reject_unsafe_relative_path(task_id, "task_id")
    task_dir = lab_path / "tasks" / task_path
    task_json = task_dir / "task.json"

    if not task_json.exists():
        raise FileNotFoundError(f"task.json not found: {task_json}")

    config = json.loads(task_json.read_text(encoding="utf-8"))

    # KeyError propagates if "instructions" is missing — do not silently fall back
    instructions = config["instructions"]

    # Extract unique deliverable filenames from criteria[].deliverables only.
    # The top-level "deliverables" key is a dict used by the evaluator differently
    # and must NOT be used here.
    names: set[str] = set()
    for criterion in config.get("criteria", []):
        for deliverable in criterion.get("deliverables", []):
            if not isinstance(deliverable, str):
                raise ValueError(
                    f"criterion deliverable must be a filename string, got: {deliverable!r}"
                )
            names.add(deliverable)

    return TaskSpec(
        task_id=task_id,
        instructions=instructions,
        documents_dir=task_dir / "documents",
        expected_deliverables=sorted(names),
        run_id=run_id,
    )
