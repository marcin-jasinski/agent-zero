"""Integration tests for the Gradio Chat tab workflow (Phase 6c).

Validates the full session lifecycle — initialize_agent → respond → ingest_document
— using mocked service clients so tests run offline without Docker.

These are "workflow" integration tests: they exercise multiple handler functions
in sequence, verifying that state flows correctly from one step to the next.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_healthy_client() -> MagicMock:
    c = MagicMock()
    c.is_healthy.return_value = True
    return c


def _make_agent(responses: list[str] | None = None) -> MagicMock:
    """Build a mock AgentOrchestrator that streams via its stream_callback."""
    agent = MagicMock()
    agent.start_conversation.return_value = "conv-001"

    resp_iter = iter(responses or ["Agent answer"])

    def _process(conv_id, msg, stream_callback=None, thinking_callback=None):
        token = next(resp_iter, "done")
        if stream_callback:
            stream_callback(token)

    agent.process_message.side_effect = _process
    return agent


def _collect(gen) -> list[tuple[str, list[dict]]]:
    return list(gen)


# ---------------------------------------------------------------------------
# Workflow: full init → send → send → ingest
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestChatSessionWorkflow:
    """Exercise multiple chat handlers in sequence, verifying state continuity."""

    def test_init_then_respond_uses_same_conversation_id(self) -> None:
        """State produced by initialize_agent is consumed correctly by respond."""
        from src.ui.chat import initialize_agent, respond

        agent = _make_agent(["Hello back"])

        with (
            patch("src.services.ollama_client.OllamaClient", return_value=_make_healthy_client()),
            patch("src.services.qdrant_client.QdrantVectorClient", return_value=_make_healthy_client()),
            patch("src.services.meilisearch_client.MeilisearchClient", return_value=_make_healthy_client()),
            patch("src.core.retrieval.RetrievalEngine"),
            patch("src.core.agent.AgentOrchestrator", return_value=agent),
        ):
            state, status, *_ = initialize_agent()

        assert "agent" in state, "initialize_agent must populate state['agent']"
        assert "✅" in status

        conv_id_from_init = state["conversation_id"]

        # Now respond must route the message through the same conversation
        results = _collect(respond("Hi there", [], state))
        final_history = results[-1][1]
        agent.process_message.assert_called_once()
        call_args = agent.process_message.call_args
        assert call_args[0][0] == conv_id_from_init, "respond must use conversation_id from state"

        assistant_msgs = [m["content"] for m in final_history if m["role"] == "assistant"]
        assert any("Hello back" in c for c in assistant_msgs)

    def test_multiple_turns_accumulate_history(self) -> None:
        """Respond yields growing history across consecutive messages."""
        from src.ui.chat import respond

        agent = _make_agent(["A1", "A2", "A3"])
        state = {
            "agent": agent,
            "conversation_id": "conv-xyz",
            "ollama": MagicMock(),
            "qdrant": MagicMock(),
            "meilisearch": MagicMock(),
        }

        history: list[dict] = []
        for question in ["Q1", "Q2", "Q3"]:
            for _, history in respond(question, list(history), state):
                pass  # drain to final state

        roles = [m["role"] for m in history]
        assert roles.count("user") == 3
        assert roles.count("assistant") == 3

    def test_error_in_respond_does_not_break_state(self) -> None:
        """When the LLM raises, respond appends an error message and the state is intact."""
        from src.ui.chat import respond

        crashing_agent = MagicMock()
        crashing_agent.process_message.side_effect = RuntimeError("LLM unavailable")
        state = {
            "agent": crashing_agent,
            "conversation_id": "conv-err",
            "ollama": MagicMock(),
            "qdrant": MagicMock(),
            "meilisearch": MagicMock(),
        }

        results = _collect(respond("Any question", [], state))
        _, final_history = results[-1]
        assistant_msgs = [m["content"] for m in final_history if m["role"] == "assistant"]
        assert any("❌" in c or "Error" in c for c in assistant_msgs)
        # State still intact for next turn
        assert state["agent"] is crashing_agent


# ---------------------------------------------------------------------------
# Workflow: ingest then respond
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIngestThenChatWorkflow:
    """Verify that an ingested document flows into a subsequent chat."""

    def test_text_ingest_then_respond_succeeds(self, tmp_path) -> None:
        """Upload a text file then send a message — no exceptions."""
        from src.ui.chat import ingest_document, respond

        # Write temp file
        p = tmp_path / "guide.txt"
        p.write_text("RAG stands for Retrieval Augmented Generation.")
        mock_file = MagicMock()
        mock_file.name = str(p)

        ingest_result = SimpleNamespace(
            success=True,
            skipped_duplicate=False,
            chunks_count=3,
            document_id="doc-00001",
            duration_seconds=0.9,
        )
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_text.return_value = ingest_result

        state = {
            "agent": _make_agent(["RAG is a retrieval technique"]),
            "conversation_id": "conv-rag",
            "ollama": MagicMock(),
            "qdrant": MagicMock(),
            "meilisearch": MagicMock(),
        }

        with patch("src.core.ingest.DocumentIngestor", return_value=mock_ingestor):
            ingest_status = ingest_document(mock_file, state)

        assert "✅" in ingest_status

        # Now ask a question — must not raise
        results = _collect(respond("What is RAG?", [], state))
        final_history = results[-1][1]
        assistant_msgs = [m["content"] for m in final_history if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1

    def test_duplicate_ingest_then_respond_succeeds(self, tmp_path) -> None:
        """Uploading a duplicate document returns info but does not break chat."""
        from src.ui.chat import ingest_document, respond

        p = tmp_path / "dup.txt"
        p.write_text("Duplicate content.")
        mock_file = MagicMock()
        mock_file.name = str(p)

        dup_result = SimpleNamespace(
            success=True,
            skipped_duplicate=True,
            chunks_count=2,
            document_id="doc-99999",
            duration_seconds=0.05,
        )
        mock_ingestor = MagicMock()
        mock_ingestor.ingest_text.return_value = dup_result

        state = {
            "agent": _make_agent(["ok"]),
            "conversation_id": "conv-dup",
            "ollama": MagicMock(),
            "qdrant": MagicMock(),
            "meilisearch": MagicMock(),
        }

        with patch("src.core.ingest.DocumentIngestor", return_value=mock_ingestor):
            status = ingest_document(mock_file, state)

        assert "ℹ️" in status

        # Chat still works
        results = _collect(respond("Tell me something", [], state))
        _, history = results[-1]
        assert any(m["role"] == "assistant" for m in history)


# ---------------------------------------------------------------------------
# Workflow: initialization failure → partial usage
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestInitializationFailureWorkflow:
    """Verify graceful degradation when services are unavailable."""

    def test_respond_without_init_returns_warning(self) -> None:
        """Calling respond with empty state never raises — appends ⚠️ message."""
        from src.ui.chat import respond

        # Empty state (startup never ran)
        results = _collect(respond("Hello?", [], {}))
        _, history = results[-1]
        assert any("⚠️" in m["content"] for m in history)

    def test_ingest_without_init_returns_warning(self, tmp_path) -> None:
        """Calling ingest_document with empty state returns ⚠️ without crashing."""
        from src.ui.chat import ingest_document

        p = tmp_path / "orphan.txt"
        p.write_text("some content")
        mock_file = MagicMock()
        mock_file.name = str(p)

        result = ingest_document(mock_file, {})
        assert "⚠️" in result

    def test_ollama_down_returns_error_status(self) -> None:
        """When Ollama reports unhealthy, initialize_agent returns error status."""
        from src.ui.chat import initialize_agent

        unhealthy = MagicMock()
        unhealthy.is_healthy.return_value = False

        with patch("src.services.ollama_client.OllamaClient", return_value=unhealthy):
            state, status, *_ = initialize_agent()

        assert state == {}
        assert "❌" in status
        assert "Ollama" in status
