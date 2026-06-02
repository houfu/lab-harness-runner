from __future__ import annotations

from pathlib import Path


GUIDE_PATH = Path("docs/adapter-guide.md")
PUBLIC_DOC_PATHS = [
    Path("README.md"),
    Path("docs/adapter-guide.md"),
]


def guide_text() -> str:
    assert GUIDE_PATH.exists(), "docs/adapter-guide.md must exist"
    return GUIDE_PATH.read_text(encoding="utf-8")


def test_adapter_guide_documents_required_contract_terms() -> None:
    text = guide_text()

    required_terms = [
        "run(task_spec, output_dir) -> RunResult",
        "TaskSpec",
        "RunResult",
        "benchmark_status",
        "raw_end_state",
        "terminal_status_seen",
        "completion_signal",
        "expected_deliverables_present",
        "missing_deliverables",
        "metrics.json",
        "summary.json",
        "results/<run-id>/",
    ]

    for term in required_terms:
        assert term in text


def test_adapter_guide_explains_timeout_with_valid_deliverables() -> None:
    text = guide_text()

    assert 'benchmark_status: "clean"' in text
    assert 'raw_end_state: "timeout"' in text
    assert "valid deliverables" in text
    assert "STATUS:DONE" in text


def test_adapter_guide_mentions_second_adapter_without_implementation() -> None:
    text = guide_text().lower()

    assert "second adapter" in text
    assert "do not implement" in text
    assert "deferred" in text

    allowed = {"adapter.py", "nanoclaw_adapter.py"}
    extra_adapters = [
        path
        for path in Path("lab_harness_runner").glob("*adapter.py")
        if path.name not in allowed
    ]
    assert extra_adapters == []


def test_public_docs_do_not_reference_local_user_paths() -> None:
    for path in PUBLIC_DOC_PATHS:
        assert path.exists(), f"{path} must exist"
        text = path.read_text(encoding="utf-8")
        assert "/Users/" not in text
        assert "/Users/houfu" not in text
