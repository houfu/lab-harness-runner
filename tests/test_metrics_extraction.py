"""Unit tests for lab_harness_runner.metrics_extraction (D-16).

Covers all Phase 6 D-16 scenarios for the ``MetricsExtractor``
Protocol and the four concrete extractors:
``AnthropicUsageExtractor``, ``DocumentReadExtractor``,
``AnthropicTranscriptExtractor``, ``NoOpExtractor``, plus the
``is_claude_model`` routing predicate.

Synthetic jsonl transcripts are built via the local
``_write_transcript`` helper at the top of the file; the
helper writes to
``tmp_path / "v2-sessions" / "ag-test" / ".claude-shared" / "projects" / "-workspace-agent"``
and returns the resolver's input dir (the ``"-workspace-agent"``
parent).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from lab_harness_runner.adapter import RunResult
from lab_harness_runner.metrics_extraction import (
    AnthropicTranscriptExtractor,
    AnthropicUsageExtractor,
    DocumentReadExtractor,
    MetricsExtractor,
    NoOpExtractor,
    is_claude_model,
)


def _write_transcript(
    tmp_path: Path,
    session_id: str,
    lines: list[dict],
    *,
    put_session_id_on_first_line: bool = True,
) -> Path:
    """Write a synthetic transcript jsonl and return the resolver's input dir.

    The transcript lives at::

        tmp_path / "v2-sessions" / "ag-test" / ".claude-shared" /
        "projects" / "-workspace-agent" / "<session_id>.jsonl"

    Each entry in ``lines`` is serialised as one jsonl line. By
    default, the first line gets a top-level ``"sessionId"``
    field added (the resolver matches on this — D-04). The
    returned dir is the parent of the jsonl file, which is
    what the extractor's resolver scans.
    """
    base = (
        tmp_path
        / "v2-sessions"
        / "ag-test"
        / ".claude-shared"
        / "projects"
        / "-workspace-agent"
    )
    base.mkdir(parents=True)
    jsonl_path = base / f"{session_id}.jsonl"
    serialised: list[str] = []
    for index, line in enumerate(lines):
        copy = dict(line)
        if put_session_id_on_first_line and index == 0:
            copy.setdefault("sessionId", session_id)
        serialised.append(json.dumps(copy))
    jsonl_path.write_text("\n".join(serialised) + "\n", encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# Routing predicate (D-10)
# ---------------------------------------------------------------------------


def test_is_claude_model_routes_correctly() -> None:
    """``is_claude_model`` returns True only for case-sensitive 'claude' prefix.

    D-10: a non-empty string starting with the case-sensitive
    prefix ``"claude"`` routes to the Anthropic path;
    anything else (``None``, empty string, ``Ollama``,
    ``"deepseek-v4-flash:cloud"``, ``"qwen2.5"``) routes to
    the no-op extractor.
    """
    assert is_claude_model("claude-opus-4-8") is True
    assert is_claude_model("claude-haiku-4-5") is True
    assert is_claude_model("claude") is True  # boundary: prefix only
    assert is_claude_model(None) is False
    assert is_claude_model("") is False
    assert is_claude_model("deepseek-v4-flash:cloud") is False
    assert is_claude_model("qwen2.5") is False
    assert is_claude_model("Ollama") is False
    # Case-sensitivity: 'Claude' is not 'claude'.
    assert is_claude_model("Claude-opus-4-8") is False


def test_routing_predicate_direct() -> None:
    """The routing predicate is exercised independently of any extractor.

    This is a regression guard that the predicate is preserved
    if a future refactor moves the routing logic.
    """
    assert is_claude_model("claude-opus-4-8") is True
    assert is_claude_model("claude-haiku-4-5") is True
    assert is_claude_model(None) is False
    assert is_claude_model("") is False
    assert is_claude_model("deepseek-v4-flash:cloud") is False
    assert is_claude_model("qwen2.5") is False
    assert is_claude_model("Ollama") is False
    assert is_claude_model("claude") is True


# ---------------------------------------------------------------------------
# NoOpExtractor (D-10)
# ---------------------------------------------------------------------------


def test_noop_extractor_returns_none_metrics() -> None:
    """NoOpExtractor ignores ``messages_out`` and returns all-None fields (D-10)."""
    result = NoOpExtractor().extract(
        messages_out=[{"type": "assistant", "message": {"usage": {"input_tokens": 999}}}]
    )
    assert result.end_state == "clean"
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.documents_read is None
    assert result.documents_read_list is None
    assert result.documents_skipped is None
    assert result.documents_skipped_list is None
    assert result.total_vdr_files is None
    assert result.wall_clock_seconds == 0.0
    assert result.run_id == ""


def test_noop_extractor_does_not_raise_on_non_dict_messages() -> None:
    """NoOpExtractor never raises, even on non-dict / non-list inputs (D-10)."""
    # Strings, ints, None — none of these should raise.
    result = NoOpExtractor().extract(["not-a-dict", 42, None, [1, 2, 3]])
    assert result.end_state == "clean"
    assert result.input_tokens is None


# ---------------------------------------------------------------------------
# Protocol structural check
# ---------------------------------------------------------------------------


def test_protocol_is_satisfied_by_extract_method() -> None:
    """A class with one ``extract(messages_out) -> RunResult`` method satisfies the Protocol."""

    class _Impl:
        def extract(self, messages_out):  # noqa: ARG002
            return RunResult(
                run_id="x", end_state="clean", wall_clock_seconds=0.0
            )

    assert isinstance(_Impl(), MetricsExtractor)


# ---------------------------------------------------------------------------
# AnthropicUsageExtractor (D-03, D-05, D-06)
# ---------------------------------------------------------------------------


def test_anthropic_usage_sums_two_assistant_messages(tmp_path: Path) -> None:
    """D-16 anchor: two assistant lines, input=2587+9846=12433, output=181+89688=89869."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-usage-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": 2587, "output_tokens": 181}
                },
            },
            {
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": 9846, "output_tokens": 89688}
                },
            },
        ],
    )

    result = AnthropicUsageExtractor(
        transcript_dir=transcript_dir, session_id="s-usage-1"
    ).extract([])

    assert result.input_tokens == 12433
    assert result.output_tokens == 89869
    assert result.end_state == "clean"


def test_anthropic_usage_folds_cache_fields(tmp_path: Path) -> None:
    """D-05 cache fold: input = raw + cache_creation + cache_read (100+50+200=350)."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-cache-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "usage": {
                        "input_tokens": 100,
                        "cache_creation_input_tokens": 50,
                        "cache_read_input_tokens": 200,
                        "output_tokens": 30,
                    }
                },
            },
        ],
    )

    result = AnthropicUsageExtractor(
        transcript_dir=transcript_dir, session_id="s-cache-1"
    ).extract([])

    assert result.input_tokens == 350
    assert result.output_tokens == 30


def test_empty_transcript_returns_none(tmp_path: Path) -> None:
    """A jsonl with no assistant messages yields all-None fields."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-empty-1",
        lines=[
            {"type": "system", "content": "boot"},
            {"type": "user", "message": {"content": "hi"}},
        ],
    )

    result = AnthropicUsageExtractor(
        transcript_dir=transcript_dir, session_id="s-empty-1"
    ).extract([])

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.documents_read is None
    assert result.documents_read_list is None


def test_malformed_lines_are_skipped(tmp_path: Path) -> None:
    """D-06: a malformed line is skipped; valid lines still contribute; no exception."""
    base = (
        tmp_path
        / "v2-sessions"
        / "ag-test"
        / ".claude-shared"
        / "projects"
        / "-workspace-agent"
    )
    base.mkdir(parents=True)
    jsonl_path = base / "s-bad-1.jsonl"
    # One BAD line, then a valid assistant line, then a sessionId
    # on a non-first line as a safety net (the resolver still
    # finds the matching sessionId because the first line carries
    # it by default — the bad line is skipped, not parsed).
    bad = "not-json-at-all"
    valid = json.dumps(
        {
            "type": "assistant",
            "message": {"usage": {"input_tokens": 100, "output_tokens": 50}},
        }
    )
    jsonl_path.write_text(
        json.dumps({"sessionId": "s-bad-1"}) + "\n"
        + bad + "\n"
        + valid + "\n",
        encoding="utf-8",
    )

    result = AnthropicUsageExtractor(
        transcript_dir=base, session_id="s-bad-1"
    ).extract([])

    # The valid line still contributes; the bad line is skipped.
    assert result.input_tokens == 100
    assert result.output_tokens == 50


def test_transcript_missing_returns_none(tmp_path: Path) -> None:
    """D-04: pointing at a non-existent transcript dir yields all-None and does not raise."""
    missing_dir = tmp_path / "no-such-dir"
    assert not missing_dir.exists()

    usage_result = AnthropicUsageExtractor(
        transcript_dir=missing_dir, session_id="x"
    ).extract([])
    assert usage_result.input_tokens is None
    assert usage_result.output_tokens is None
    assert usage_result.documents_read is None
    assert usage_result.documents_read_list is None

    docs_result = DocumentReadExtractor(
        transcript_dir=missing_dir, session_id="x"
    ).extract([])
    assert docs_result.documents_read is None
    assert docs_result.documents_read_list is None


def test_anthropic_usage_ignores_non_assistant_lines_with_usage_block(
    tmp_path: Path,
) -> None:
    """D-06: only ``type == "assistant"`` lines contribute; a ``user`` line with usage is skipped."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-mix-1",
        lines=[
            {
                "type": "user",
                "message": {
                    "usage": {"input_tokens": 999, "output_tokens": 999}
                },
            },
            {
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": 100, "output_tokens": 50}
                },
            },
        ],
    )

    result = AnthropicUsageExtractor(
        transcript_dir=transcript_dir, session_id="s-mix-1"
    ).extract([])

    # The user line must NOT contribute; only the assistant line does.
    assert result.input_tokens == 100
    assert result.output_tokens == 50


# ---------------------------------------------------------------------------
# DocumentReadExtractor (D-07, D-08)
# ---------------------------------------------------------------------------


def test_document_read_dedup(tmp_path: Path) -> None:
    """D-07 dedup: two Read blocks for the same path yield one entry; order preserved."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-doc-dedup-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/engagement.txt"},
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/engagement.txt"},
                        }
                    ]
                },
            },
        ],
    )

    result = DocumentReadExtractor(
        transcript_dir=transcript_dir, session_id="s-doc-dedup-1"
    ).extract([])

    assert result.documents_read_list == ["/tmp/engagement.txt"]
    assert result.documents_read == 1


def test_document_read_skips_non_read_tool_use(tmp_path: Path) -> None:
    """Non-Read tool_use blocks (Bash) contribute nothing; only Read blocks do."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-doc-skip-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/a.txt"},
                        },
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ls"},
                        },
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/b.txt"},
                        },
                    ]
                },
            },
        ],
    )

    result = DocumentReadExtractor(
        transcript_dir=transcript_dir, session_id="s-doc-skip-1"
    ).extract([])

    assert result.documents_read_list == ["/tmp/a.txt", "/tmp/b.txt"]
    assert result.documents_read == 2


def test_documents_skipped_fields_remain_none(tmp_path: Path) -> None:
    """D-07: even when Read blocks are found, the documents_skipped fields stay None."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-skip-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/a.txt"},
                        }
                    ]
                },
            },
        ],
    )

    result = DocumentReadExtractor(
        transcript_dir=transcript_dir, session_id="s-skip-1"
    ).extract([])

    assert result.documents_read == 1
    assert result.documents_read_list == ["/tmp/a.txt"]
    assert result.documents_skipped is None
    assert result.documents_skipped_list is None


def test_document_read_preserves_order_with_duplicates_across_messages(
    tmp_path: Path,
) -> None:
    """D-07 dedup with order preserved: first occurrence wins, later duplicates dropped."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-doc-order-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/a.txt"},
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/b.txt"},
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/a.txt"},
                        }
                    ]
                },
            },
        ],
    )

    result = DocumentReadExtractor(
        transcript_dir=transcript_dir, session_id="s-doc-order-1"
    ).extract([])

    # First occurrence wins: /tmp/a.txt comes first, /tmp/b.txt
    # second; the second /tmp/a.txt is dropped.
    assert result.documents_read_list == ["/tmp/a.txt", "/tmp/b.txt"]
    assert result.documents_read == 2


# ---------------------------------------------------------------------------
# AnthropicTranscriptExtractor (D-09)
# ---------------------------------------------------------------------------


def test_combined_anthropic_path_populates_both_fields(tmp_path: Path) -> None:
    """D-09: combined extractor returns BOTH input_tokens AND documents_read_list populated."""
    transcript_dir = _write_transcript(
        tmp_path,
        session_id="s-combo-1",
        lines=[
            {
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/engagement.txt"},
                        }
                    ],
                },
            },
        ],
    )

    result = AnthropicTranscriptExtractor(
        transcript_dir=transcript_dir, session_id="s-combo-1"
    ).extract([])

    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.documents_read_list == ["/tmp/engagement.txt"]
    assert result.documents_read == 1
    # documents_skipped / list stay None: D-07.
    assert result.documents_skipped is None
    assert result.documents_skipped_list is None
    # The merged RunResult's end_state is clean and run_id is "":
    # the adapter overwrites run_id (D-13 step 2 in Plan 02).
    assert result.end_state == "clean"
    assert result.run_id == ""


# ---------------------------------------------------------------------------
# D-19 live schema deviation: shim session id != transcript sessionId
# ---------------------------------------------------------------------------


def test_d19_fallback_extracts_when_shim_id_mismatches(tmp_path: Path) -> None:
    """The nanoclaw shim returns its agent-shared session id (``sess-...``),
    but the Claude transcript lines carry Claude's own session UUID. The
    two never match in a live run (confirmed by the Phase 6 live-verify
    run on corporate-ma/compare-matter-plan-against-engagement-letter).
    Because ``transcript_dir`` is per-ephemeral-group, the resolver must
    fall back to the sole jsonl when no line matches the shim id.
    """
    claude_uuid = "27d79058-b2d9-4904-b436-0563d5135d9b"
    transcript_dir = _write_transcript(
        tmp_path,
        claude_uuid,  # the jsonl's sessionId field is the Claude UUID
        [
            {
                "type": "assistant",
                "message": {
                    "usage": {
                        "input_tokens": 8904,
                        "cache_creation_input_tokens": 62352,
                        "cache_read_input_tokens": 364925,
                        "output_tokens": 4701,
                    },
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/engagement.txt"},
                        },
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/matterplan.txt"},
                        },
                    ],
                },
            },
        ],
    )

    # Query with the shim's agent-shared id, which is NOT the Claude UUID.
    shim_session_id = "sess-1780871426814-f7fh70"
    result = AnthropicTranscriptExtractor(
        transcript_dir=transcript_dir, session_id=shim_session_id
    ).extract([])

    # D-05 cache fold: 8904 + 62352 + 364925 = 436181.
    assert result.input_tokens == 436181
    assert result.output_tokens == 4701
    assert result.documents_read == 2
    assert result.documents_read_list == [
        "/tmp/engagement.txt",
        "/tmp/matterplan.txt",
    ]


def test_d19_session_id_match_still_wins_over_fallback(tmp_path: Path) -> None:
    """When a jsonl DOES carry the matching sessionId, it is preferred over
    the newest-file fallback — preserving D-04 multi-run discrimination.
    """
    base = (
        tmp_path
        / "v2-sessions"
        / "ag-test"
        / ".claude-shared"
        / "projects"
        / "-workspace-agent"
    )
    base.mkdir(parents=True)

    # Older jsonl carries the matching shim id with 11 output tokens.
    (base / "match.jsonl").write_text(
        json.dumps(
            {
                "sessionId": "s-match",
                "type": "assistant",
                "message": {"usage": {"input_tokens": 1, "output_tokens": 11}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # Newer jsonl (would win the mtime fallback) carries a different id.
    other = base / "other.jsonl"
    other.write_text(
        json.dumps(
            {
                "sessionId": "s-other",
                "type": "assistant",
                "message": {"usage": {"input_tokens": 2, "output_tokens": 99}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    os.utime(other, (10**10, 10**10))  # force "other" to be newest

    result = AnthropicUsageExtractor(
        transcript_dir=base, session_id="s-match"
    ).extract([])

    # The sessionId match wins: output_tokens from match.jsonl (11), not 99.
    assert result.output_tokens == 11
