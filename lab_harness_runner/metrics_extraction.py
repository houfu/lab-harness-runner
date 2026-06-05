"""Metrics extraction from agent transcripts.

This module defines the ``MetricsExtractor`` Protocol and four concrete
extractors used by the nanoclaw adapter (v1.1 Phase 6, EXT-01..04):

* :class:`AnthropicUsageExtractor` reads token usage from
  Anthropic's ``assistant`` message ``usage`` blocks in the nanoclaw
  transcript jsonl. Both ``cache_creation_input_tokens`` and
  ``cache_read_input_tokens`` are folded into ``input_tokens``
  (D-05) — this matches the user-facing Anthropic bill.
* :class:`DocumentReadExtractor` enumerates ``Read`` ``tool_use``
  blocks in the same transcript and collects the verbatim
  ``input.file_path`` strings into ``documents_read_list``
  (D-07 / D-08), deduplicated with order preserved.
* :class:`AnthropicTranscriptExtractor` composes the two
  Anthropic extractors into a single combined ``RunResult``
  (D-09). The two extractors fill disjoint fields, so the
  merge is "first non-``None`` wins" and degenerates to
  "either value is the value".
* :class:`NoOpExtractor` is the routing target for non-Claude
  models (D-10). It returns a ``RunResult`` with all token /
  coverage fields as ``None`` and never raises.

The :func:`is_claude_model` predicate is the routing rule
(D-10): a model string starting (case-sensitively) with
``"claude"`` routes to ``AnthropicTranscriptExtractor``;
anything else routes to ``NoOpExtractor``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from lab_harness_runner.adapter import RunResult


def is_claude_model(model: str | None) -> bool:
    """Return ``True`` iff ``model`` is a non-empty string with the
    case-sensitive prefix ``"claude"`` (D-10).

    Anything else — ``None``, ``""``, ``"Ollama"``,
    ``"deepseek-v4-flash:cloud"`` — routes to the no-op
    extractor.
    """
    return bool(model) and model.startswith("claude")


@runtime_checkable
class MetricsExtractor(Protocol):
    """Read-side helper that returns a populated ``RunResult``.

    Implementations are stateless from the caller's perspective:
    the protocol carrier ``messages_out`` is preserved for
    uniformity (a future Ollama-aware extractor can read from
    it), but the Anthropic path ignores it and reads the
    transcript jsonl directly per D-03.
    """

    def extract(self, messages_out: list[dict]) -> RunResult: ...


class _TranscriptReader:
    """Shared substrate for the two Anthropic extractors.

    Holds the resolved transcript dir + session id, and exposes
    the resolver and jsonl iterator. ``AnthropicUsageExtractor``
    and ``DocumentReadExtractor`` inherit from it so the
    D-04 resolver lives in one place while keeping the public
    classes distinct (D-09 — the combined class is a thin
    compose, not a deep inheritance).
    """

    def __init__(self, transcript_dir: Path, session_id: str) -> None:
        self.transcript_dir = Path(transcript_dir)
        self.session_id = session_id

    def _resolve_transcript(self) -> Path | None:
        """Locate the jsonl whose top-level ``sessionId`` matches.

        Scans every ``*.jsonl`` entry in ``self.transcript_dir``,
        parses lines until a matching ``sessionId`` is found, and
        returns that jsonl's path. Returns ``None`` if the dir
        does not exist or no jsonl carries a matching
        ``sessionId``. Defensive against:

        * missing dir (returns ``None``, never raises — D-04)
        * malformed jsonl files (skipped, never raised — D-06)
        * non-matching jsonls in the same dir (the v1.0 proof
          group may share a group dir with prior runs; D-04
          anchored this case)
        """
        if not self.transcript_dir.is_dir():
            return None

        for candidate in self.transcript_dir.glob("*.jsonl"):
            for line in self._iter_jsonl(candidate):
                if not isinstance(line, dict):
                    continue
                if line.get("sessionId") == self.session_id:
                    return candidate
        return None

    @staticmethod
    def _iter_jsonl(path: Path):
        """Yield each successfully-parsed line dict; skip malformed lines.

        D-06: malformed JSON is skipped, not raised. ``OSError`` on
        a per-line read (e.g. a vanishing file) is also skipped.
        """
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        yield json.loads(line)
                    except (json.JSONDecodeError, OSError):
                        continue
        except OSError:
            return


class AnthropicUsageExtractor(_TranscriptReader):
    """Sum token usage across all assistant message ``usage`` blocks.

    For every line whose ``type == "assistant"`` and whose
    ``message.usage`` is a dict, folds ``input_tokens``,
    ``cache_creation_input_tokens``, and
    ``cache_read_input_tokens`` into a single ``input_tokens``
    total (D-05) and sums ``output_tokens``. Other line types
    (``user``, ``system``, ``queue-operation``,
    tool-result messages) are skipped (D-06).
    """

    def extract(self, messages_out: list[dict]) -> RunResult:
        # ``messages_out`` is part of the protocol signature; the
        # Anthropic path reads the transcript directly per D-03.
        del messages_out

        transcript = self._resolve_transcript()
        if transcript is None:
            return RunResult(
                run_id="", end_state="clean", wall_clock_seconds=0.0
            )

        input_total = 0
        output_total = 0
        saw_assistant_usage = False

        for line in self._iter_jsonl(transcript):
            if not isinstance(line, dict):
                continue
            if line.get("type") != "assistant":
                continue
            message = line.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue

            saw_assistant_usage = True
            input_total += (
                usage.get("input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
            )
            output_total += usage.get("output_tokens", 0)

        if not saw_assistant_usage:
            return RunResult(
                run_id="", end_state="clean", wall_clock_seconds=0.0
            )

        return RunResult(
            run_id="",
            end_state="clean",
            wall_clock_seconds=0.0,
            input_tokens=input_total,
            output_tokens=output_total,
        )


class DocumentReadExtractor(_TranscriptReader):
    """Collect ``Read`` ``tool_use`` blocks' ``file_path`` strings.

    For every line whose ``type == "assistant"`` and whose
    ``message.content`` is a list, iterate the content blocks.
    For every block with ``type == "tool_use"`` and
    ``name == "Read"``, append the value of
    ``input.file_path`` (when it is a string) to the read
    list, deduplicating with order preserved (first
    occurrence wins — D-07). Non-Read tool_use blocks
    (e.g. ``Bash``, ``Write``, ``Edit``, ``Glob``,
    ``Grep``) contribute nothing. File paths are kept
    verbatim as the agent saw them (D-08 — no
    basename / no remapping against ``lab-documents``).
    """

    def extract(self, messages_out: list[dict]) -> RunResult:
        del messages_out

        transcript = self._resolve_transcript()
        if transcript is None:
            return RunResult(
                run_id="", end_state="clean", wall_clock_seconds=0.0
            )

        read_list: list[str] = []
        seen: set[str] = set()

        for line in self._iter_jsonl(transcript):
            if not isinstance(line, dict):
                continue
            if line.get("type") != "assistant":
                continue
            message = line.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "Read":
                    continue
                payload = block.get("input")
                if not isinstance(payload, dict):
                    continue
                file_path = payload.get("file_path")
                if not isinstance(file_path, str):
                    continue
                if file_path in seen:
                    continue
                seen.add(file_path)
                read_list.append(file_path)

        if not read_list:
            return RunResult(
                run_id="", end_state="clean", wall_clock_seconds=0.0
            )

        return RunResult(
            run_id="",
            end_state="clean",
            wall_clock_seconds=0.0,
            documents_read=len(read_list),
            documents_read_list=read_list,
        )


class AnthropicTranscriptExtractor:
    """Compose the two Anthropic extractors into one ``RunResult`` (D-09).

    The two extractors fill disjoint fields (tokens from
    usage, document list from tool_use), so the merge
    degenerates to "either value is the value". The merge
    is still expressed field-by-field for explicitness.
    """

    def __init__(self, transcript_dir: Path, session_id: str) -> None:
        self._usage = AnthropicUsageExtractor(transcript_dir, session_id)
        self._docs = DocumentReadExtractor(transcript_dir, session_id)

    def extract(self, messages_out: list[dict]) -> RunResult:
        usage_result = self._usage.extract(messages_out)
        docs_result = self._docs.extract(messages_out)

        # Both parents use run_id=""; the adapter overwrites it with
        # the real run_id from task_spec (D-13 step 2 in Plan 02).
        merged = RunResult(
            run_id=usage_result.run_id or docs_result.run_id,
            end_state="clean",
            wall_clock_seconds=0.0,
        )

        # First non-None wins; usage owns the token fields and
        # docs owns the documents_read / list fields. Both are
        # None for the others, so the merge is "either value
        # is the value" in practice.
        merged.input_tokens = (
            usage_result.input_tokens
            if usage_result.input_tokens is not None
            else docs_result.input_tokens
        )
        merged.output_tokens = (
            usage_result.output_tokens
            if usage_result.output_tokens is not None
            else docs_result.output_tokens
        )
        merged.documents_read = (
            usage_result.documents_read
            if usage_result.documents_read is not None
            else docs_result.documents_read
        )
        merged.documents_skipped = (
            usage_result.documents_skipped
            if usage_result.documents_skipped is not None
            else docs_result.documents_skipped
        )
        merged.total_vdr_files = (
            usage_result.total_vdr_files
            if usage_result.total_vdr_files is not None
            else docs_result.total_vdr_files
        )
        merged.documents_read_list = (
            usage_result.documents_read_list
            if usage_result.documents_read_list is not None
            else docs_result.documents_read_list
        )
        merged.documents_skipped_list = (
            usage_result.documents_skipped_list
            if usage_result.documents_skipped_list is not None
            else docs_result.documents_skipped_list
        )
        return merged


class NoOpExtractor:
    """Return a ``RunResult`` with all token / coverage fields as ``None``.

    The routing decision (D-10) is made before this class is
    constructed, so the no-op does not need a path. The
    optional ``__init__`` accepts and ignores any args for
    protocol uniformity with the path-taking extractors. The
    no-op MUST NOT raise under any input (D-10).
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Accept-and-ignore: protocol uniformity only.
        del args
        del kwargs

    def extract(self, messages_out: list[dict]) -> RunResult:
        # ``messages_out`` is part of the signature for protocol
        # uniformity; the no-op ignores it. Do not raise on any
        # input shape.
        del messages_out
        return RunResult(
            run_id="", end_state="clean", wall_clock_seconds=0.0
        )
