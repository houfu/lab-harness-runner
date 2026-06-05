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


def test_adapter_guide_documents_null_vs_zero_distinction() -> None:
    """Regression test for D-15 / D-16: the doc must explain the new
    null-vs-zero contract for the LAB-compatible metric fields. Without
    this test, a future edit could quietly drop the wording and adapters
    would be left without a written record of what `None` means on disk
    (adapter did not measure) vs. an explicit `0` (adapter measured zero)."""
    text = guide_text()

    # The new "Metrics And Status Semantics" addendum must surface the
    # three contract terms: null, unmeasured, and "measured zero" as a
    # contrast to "unmeasured".
    assert "null" in text
    assert "unmeasured" in text
    assert "measured zero" in text

    # The RunResult field list must show the list fields as nullable.
    assert "list[str] | None" in text

    # The old "optional document lists." line has been replaced by the
    # new "optional document lists" line that continues with "of type
    # list[str] | None" (line-wrapped in the markdown source). Guard
    # both halves of the new wording.
    assert "of type" in text
    assert "list[str] | None" in text
    # The original phrase "optional document lists." (period then
    # end-of-line) is no longer standalone in the file. The new
    # sentence continues past that boundary, so a naive substring
    # check could still find "optional document lists"; the stronger
    # check is that the file's text now contains the explanatory
    # nullability clause.
    assert "list[str] | None`; `None` means unmeasured" in text
