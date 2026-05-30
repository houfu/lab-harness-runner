"""Fake adapter run — proves the full package wiring end-to-end.
Creates a hand-crafted output directory (placeholder deliverables),
writes metrics.json, and optionally invokes the LAB evaluator.
Usage:
    uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy
    uv run python scripts/fake_run.py --task antitrust-competition/analyze-antitrust-hsr-strategy --score
"""

from __future__ import annotations

import argparse
import os
import time
import uuid
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lab_harness_runner import (
    Adapter,
    RunResult,
    TaskSpec,
    build_result_dir,
    read_task,
    score_run,
    write_metrics,
)


def reject_unsafe_relative_path(value: str, name: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{name} must be relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} contains an unsafe path segment: {value}")
    return path


def write_minimal_docx(path: Path, lines: list[str]) -> None:
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in lines
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}<w:sectPr/></w:body>"
        "</w:document>"
    )

    with ZipFile(path, "w", ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        docx.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            "</Relationships>",
        )
        docx.writestr("word/document.xml", document_xml)


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


class FakeAdapter:
    def run(self, task_spec: TaskSpec, output_dir: Path) -> RunResult:
        start = time.monotonic()
        for filename in task_spec.expected_deliverables:
            filepath = output_dir / filename
            if filepath.suffix.lower() == ".docx":
                write_minimal_docx(
                    filepath, ["Placeholder", f"Task: {task_spec.task_id}"]
                )
            else:
                filepath.write_text(
                    f"Placeholder for {filename} — fake_run.py", encoding="utf-8"
                )
        return RunResult(
            run_id=task_spec.run_id,
            end_state="clean",
            wall_clock_seconds=time.monotonic() - start,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="area/slug task path")
    parser.add_argument(
        "--run-id", default=None, help="explicit run ID (default: uuid4)"
    )
    parser.add_argument(
        "--lab-path",
        default=None,
        help="explicit LAB root (default: env var / home fallback)",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="invoke LAB evaluator after writing deliverables",
    )
    parser.add_argument(
        "--judge-model", default="claude-sonnet-4-6", help="judge model name"
    )
    args = parser.parse_args()

    reject_unsafe_relative_path(args.task, "--task")
    if args.run_id is not None:
        reject_unsafe_relative_path(args.run_id, "--run-id")

    run_id = args.run_id or str(uuid.uuid4())
    lab_path = (
        Path(args.lab_path).expanduser().resolve() if args.lab_path else _lab_path()
    )

    task_spec = read_task(lab_path=lab_path, task_id=args.task, run_id=run_id)
    run_dir, output_dir = build_result_dir(lab_path=lab_path, run_id=run_id)

    adapter = FakeAdapter()
    result = adapter.run(task_spec=task_spec, output_dir=output_dir)

    write_metrics(run_dir=run_dir, result=result)

    print(f"Run directory: {run_dir}")
    print(f"Run ID: {run_id}")
    print(f"Deliverables: {', '.join(task_spec.expected_deliverables)}")

    if args.score:
        scores_path = score_run(
            lab_path=lab_path,
            run_id=run_id,
            task_id=args.task,
            expected_deliverables=task_spec.expected_deliverables,
            judge_model=args.judge_model,
        )
        print(f"Scores: {scores_path}")
    else:
        print("Scoring skipped (pass --score to invoke evaluator)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
