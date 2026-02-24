"""Tests for Agent Zero Gradio Chat Tab handlers (Phase 6c Step 33).

All service clients and core classes are imported *inside* each handler
function (lazy imports), so patches must target the original module path,
NOT src.ui.chat.<ClassName>.

Patch targets:
  - src.services.ollama_client.OllamaClient
  - src.services.qdrant_client.QdrantVectorClient
  - src.services.meilisearch_client.MeilisearchClient
  - src.core.agent.AgentOrchestrator
  - src.core.retrieval.RetrievalEngine
  - src.core.ingest.DocumentIngestor
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# initialize_agent
# ===========================================================================


def _mock_healthy_client() -> MagicMock:
    c = MagicMock()
    c.is_healthy.return_value = True
    return c


def _mock_unhealthy_client() -> MagicMock:
    c = MagicMock()
    c.is_healthy.return_value = False
    return c


class TestInitializeAgent:
    """Unit tests for src.ui.chat.initialize_agent."""

    def test_all_services_healthy_returns_state_and_success_status(self) -> None:
        from src.ui.chat import initialize_agent

        agent = MagicMock()
        agent.start_conversation.return_value = "conv-001"

        with (
            patch("src.services.ollama_client.OllamaClient", return_value=_mock_healthy_client()),
            patch("src.services.qdrant_client.QdrantVectorClient", return_value=_mock_healthy_client()),
            patch("src.services.meilisearch_client.MeilisearchClient", return_value=_mock_healthy_client()),
            patch("src.core.retrieval.RetrievalEngine") as MockEngine,
            patch("src.core.agent.AgentOrchestrator", return_value=agent),
        ):
            state, status, *_ = initialize_agent()

        assert "agent" in state
        assert "✅" in status

    def test_ollama_unhealthy_returns_empty_state_with_error(self) -> None:
        from src.ui.chat import initialize_agent

        with patch("src.services.ollama_client.OllamaClient", return_value=_mock_unhealthy_client()):
            state, status, *_ = initialize_agent()

        assert state == {}
        assert "❌" in status
        assert "Ollama" in status

    def test_qdrant_unhealthy_returns_empty_state_with_error(self) -> None:
        from src.ui.chat import initialize_agent

        with (
            patch("src.services.ollama_client.OllamaClient", return_value=_mock_healthy_client()),
            patch("src.services.qdrant_client.QdrantVectorClient", return_value=_mock_unhealthy_client()),
        ):
            state, status, *_ = initialize_agent()

        assert state == {}
        assert "❌" in status
        assert "Qdrant" in status

    def test_meilisearch_unhealthy_returns_empty_state_with_error(self) -> None:
        from src.ui.chat import initialize_agent

        with (
            patch("src.services.ollama_client.OllamaClient", return_value=_mock_healthy_client()),
            patch("src.services.qdrant_client.QdrantVectorClient", return_value=_mock_healthy_client()),
            patch("src.services.meilisearch_client.MeilisearchClient", return_value=_mock_unhealthy_client()),
        ):
            state, status, *_ = initialize_agent()

        assert state == {}
        assert "❌" in status
        assert "Meilisearch" in status

    def test_unexpected_exception_returns_empty_state(self) -> None:
        from src.ui.chat import initialize_agent

        with patch(
            "src.services.ollama_client.OllamaClient",
            side_effect=RuntimeError("container not found"),
        ):
            state, status, *_ = initialize_agent()

        assert state == {}
        assert "❌" in status
        assert "container not found" in status


# ===========================================================================
# respond  (generator)
# ===========================================================================


def _build_state(agent: MagicMock | None = None) -> dict:
    """Return a minimal session state dict with an optional agent.

    Mirrors the structure produced by initialize_agent() so that all handler
    guards (``"ollama" not in state``, ``"agent" not in state``) pass.
    """
    a = agent or MagicMock()
    a.start_conversation.return_value = "conv-001"
    return {
        "agent": a,
        "conversation_id": "conv-001",
        "ollama": MagicMock(),
        "qdrant": MagicMock(),
        "meilisearch": MagicMock(),
    }


def _collect(gen) -> list[tuple[str, list[dict]]]:
    return list(gen)


class TestRespond:
    """Unit tests for src.ui.chat.respond."""

    def test_empty_message_yields_unchanged_history(self) -> None:
        from src.ui.chat import respond

        history = [{"role": "user", "content": "hi"}]
        results = _collect(respond("", history, _build_state()))
        assert len(results) == 1
        cleared, returned_history = results[0]
        assert cleared == ""
        assert returned_history is history

    def test_uninitialized_state_appends_warning(self) -> None:
        from src.ui.chat import respond

        results = _collect(respond("hello", [], {}))
        _, history = results[-1]
        contents = [m["content"] for m in history]
        assert any("⚠️" in c for c in contents)

    def test_normal_message_appends_user_and_assistant(self) -> None:
        from src.ui.chat import respond

        agent = MagicMock()
        agent.process_message.side_effect = lambda conv_id, msg, stream_callback=None, thinking_callback=None: stream_callback("Answer")

        results = _collect(respond("Question?", [], _build_state(agent)))
        final_history = results[-1][1]
        roles = [m["role"] for m in final_history]
        assert "user" in roles
        assert "assistant" in roles

    def test_assistant_content_matches_agent_response(self) -> None:
        from src.ui.chat import respond

        agent = MagicMock()
        agent.process_message.side_effect = lambda conv_id, msg, stream_callback=None, thinking_callback=None: stream_callback(
            "42 is the answer"
        )

        results = _collect(respond("What is the answer?", [], _build_state(agent)))
        final_history = results[-1][1]
        assistant_msgs = [m["content"] for m in final_history if m["role"] == "assistant"]
        assert any("42 is the answer" in c for c in assistant_msgs)

    def test_respond_clears_input_field(self) -> None:
        from src.ui.chat import respond

        agent = MagicMock()
        agent.process_message.side_effect = lambda conv_id, msg, stream_callback=None, thinking_callback=None: stream_callback("ok")

        results = _collect(respond("hello", [], _build_state(agent)))
        # Every yield must return an empty string as the first element (cleared input)
        for cleared, _ in results:
            assert cleared == ""

    def test_agent_exception_appends_error_message(self) -> None:
        from src.ui.chat import respond

        agent = MagicMock()
        agent.process_message.side_effect = RuntimeError("LLM offline")

        results = _collect(respond("hi", [], _build_state(agent)))
        final_history = results[-1][1]
        assistant_msgs = [m["content"] for m in final_history if m["role"] == "assistant"]
        assert any("❌" in c or "Error" in c for c in assistant_msgs)


# ===========================================================================
# ingest_document
# ===========================================================================


def _make_ingest_file(tmp_path, name: str, content: bytes | str) -> MagicMock:
    """Create a real temp file and return a mock Gradio file object."""
    p = tmp_path / name
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")
    mock_file = MagicMock()
    mock_file.name = str(p)
    return mock_file


class TestIngestDocument:
    """Unit tests for src.ui.chat.ingest_document."""

    def test_none_file_returns_warning(self) -> None:
        from src.ui.chat import ingest_document

        result = ingest_document(None, _build_state())
        assert "⚠️" in result

    def test_empty_state_returns_warning(self, tmp_path) -> None:
        from src.ui.chat import ingest_document

        f = _make_ingest_file(tmp_path, "doc.pdf", b"%PDF dummy")
        result = ingest_document(f, {})
        assert "⚠️" in result

    def test_unsupported_extension_returns_error(self, tmp_path) -> None:
        from src.ui.chat import ingest_document

        f = _make_ingest_file(tmp_path, "doc.docx", b"binary")
        result = ingest_document(f, _build_state())
        assert "❌" in result
        assert ".docx" in result

    def test_pdf_success_returns_confirmation(self, tmp_path) -> None:
        from src.ui.chat import ingest_document

        f = _make_ingest_file(tmp_path, "report.pdf", b"%PDF-1.4 dummy content")
        result_obj = SimpleNamespace(
            success=True,
            skipped_duplicate=False,
            chunks_count=5,
            document_id="abc1234567890",
            duration_seconds=1.2,
        )
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_pdf_bytes.return_value = result_obj

        with patch("src.core.ingest.DocumentIngestor", return_value=mock_ingestor):
            result = ingest_document(f, _build_state())

        assert "✅" in result
        assert "report.pdf" in result

    def test_text_success_returns_confirmation(self, tmp_path) -> None:
        from src.ui.chat import ingest_document

        f = _make_ingest_file(tmp_path, "notes.txt", "Hello world notes")
        result_obj = SimpleNamespace(
            success=True,
            skipped_duplicate=False,
            chunks_count=2,
            document_id="def0987654321",
            duration_seconds=0.5,
        )
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_text.return_value = result_obj

        with patch("src.core.ingest.DocumentIngestor", return_value=mock_ingestor):
            result = ingest_document(f, _build_state())

        assert "✅" in result
        assert "notes.txt" in result

    def test_duplicate_document_returns_info(self, tmp_path) -> None:
        from src.ui.chat import ingest_document

        f = _make_ingest_file(tmp_path, "rag.txt", "RAG introduction text")
        result_obj = SimpleNamespace(
            success=True,
            skipped_duplicate=True,
            chunks_count=3,
            document_id="dup1234567890",
            duration_seconds=0.1,
        )
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_text.return_value = result_obj

        with patch("src.core.ingest.DocumentIngestor", return_value=mock_ingestor):
            result = ingest_document(f, _build_state())

        assert "ℹ️" in result

    def test_ingestion_failure_returns_error(self, tmp_path) -> None:
        from src.ui.chat import ingest_document

        f = _make_ingest_file(tmp_path, "broken.txt", "some content")
        result_obj = SimpleNamespace(
            success=False,
            skipped_duplicate=False,
            chunks_count=0,
            document_id="",
            duration_seconds=0.0,
            error="vector DB unreachable",
        )
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_text.return_value = result_obj

        with patch("src.core.ingest.DocumentIngestor", return_value=mock_ingestor):
            result = ingest_document(f, _build_state())

        assert "❌" in result
        assert "vector DB unreachable" in result
