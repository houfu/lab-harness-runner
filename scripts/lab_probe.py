#!/usr/bin/env python3
"""Create a deterministic Harvey LAB result skeleton for one task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def reject_unsafe_relative_path(value: str, name: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} contains an unsafe path segment: {value}")
    return path


def load_task(harvey_root: Path, task: Path) -> dict:
    task_json = harvey_root / "tasks" / task / "task.json"
    if not task_json.exists():
        raise FileNotFoundError(f"task.json not found: {task_json}")
    return json.loads(task_json.read_text(encoding="utf-8"))


def expected_deliverables(task_config: dict) -> list[str]:
    names: set[str] = set()
    for criterion in task_config.get("criteria", []):
        for deliverable in criterion.get("deliverables", []):
            if not isinstance(deliverable, str):
                raise ValueError("criterion deliverables must be filenames")
            names.add(deliverable)
    return sorted(names)


def write_dummy_deliverable(path: Path, task_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "Dummy deliverable for LAB result-layout validation.",
                "",
                f"Task: {task_title}",
                "",
                "This file proves the expected filename and output directory shape.",
            ]
        ),
        encoding="utf-8",
    )


def write_metrics(path: Path, task_config: dict, harvey_root: Path, task: Path) -> None:
    documents_dir = harvey_root / "tasks" / task / "documents"
    total_files = 0
    if documents_dir.exists():
        total_files = sum(1 for item in documents_dir.rglob("*") if item.is_file())

    metrics = {
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_clock_seconds": 0,
        "documents_read": 0,
        "total_vdr_files": total_files,
        "documents_skipped": total_files,
        "documents_read_list": [],
        "documents_skipped_list": [],
        "task_title": task_config.get("title", ""),
        "end_state": "dry-run",
    }
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvey-root", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    harvey_root = Path(args.harvey_root).expanduser().resolve()
    task = reject_unsafe_relative_path(args.task, "--task")
    run_id = reject_unsafe_relative_path(args.run_id, "--run-id")

    task_config = load_task(harvey_root=harvey_root, task=task)
    deliverables = expected_deliverables(task_config)
    if not deliverables:
        raise ValueError(f"no criterion deliverables found for task: {task}")

    run_dir = harvey_root / "results" / run_id
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    for deliverable in deliverables:
        filename = reject_unsafe_relative_path(deliverable, "deliverable")
        write_dummy_deliverable(output_dir / filename, task_config.get("title", ""))

    write_metrics(run_dir / "metrics.json", task_config, harvey_root, task)

    eval_command = (
        "uv run python -m evaluation.run_eval "
        f"--run-id {run_id.as_posix()} "
        f"--task {task.as_posix()} "
        "--judge-model claude-sonnet-4-6"
    )
    print(f"Created LAB result skeleton: {run_dir}")
    print(f"Deliverables: {', '.join(deliverables)}")
    print(f"Evaluator command: {eval_command}")
    if args.dry_run:
        print("Dry run: evaluator not invoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
