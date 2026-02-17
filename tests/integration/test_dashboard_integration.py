"""Integration tests for Chainlit dashboard actions and chat workflow.

These tests validate the end-to-end flow of:
- chat session initialization
- document upload processing
- admin action callbacks
"""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.integration


def _load_main_module() -> object:
    """Import and reload `src.ui.main` to ensure mocked Chainlit is used."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


@pytest.mark.asyncio
async def test_chainlit_chat_start_to_message_flow(mock_chainlit) -> None:
    """Chat flow initializes session and processes a user message."""
    main_module = _load_main_module()

    mock_agent = MagicMock()
    with patch.object(main_module, "_initialize_agent", return_value=(mock_agent, "conv-123", None)), patch.object(
        main_module,
        "_process_message_async",
        return_value=("assistant reply", None),
    ):
        await main_module.start()
        await main_module.main(SimpleNamespace(content="hello", elements=[]))

    assert mock_chainlit["session"]["agent_initialized"] is True
    assert any(msg.content == "assistant reply" for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_chainlit_file_upload_then_chat(mock_chainlit) -> None:
    """Upload succeeds and session can continue chatting."""
    main_module = _load_main_module()

    result = SimpleNamespace(
        success=True,
        skipped_duplicate=False,
        document_id="doc-123",
        chunks_count=4,
        duration_seconds=0.8,
        error=None,
        existing_document_id=None,
    )

    with patch.object(main_module, "_get_or_create_ingestor", return_value=(object(), None)), patch.object(
        main_module,
        "_ingest_document_async",
        return_value=(result, None),
    ):
        file_obj = mock_chainlit["module"].File(name="notes.md", content=b"# notes")
        await main_module.process_file_upload(file_obj)

    assert any("Document indexed successfully" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_chainlit_dashboard_actions_workflow(mock_chainlit) -> None:
    """System health, qdrant info, and settings actions each produce a report."""
    main_module = _load_main_module()

    healthy_status = SimpleNamespace(name="Ollama", is_healthy=True, message="OK", details={})
    checker = MagicMock()
    checker.check_all.return_value = {"ollama": healthy_status}

    qdrant = MagicMock()
    qdrant.is_healthy.return_value = True
    qdrant.list_collections.return_value = [{"name": "documents", "vectors_count": 1}]
    qdrant.get_collection_stats.return_value = {
        "vectors_count": 1,
        "points_count": 1,
        "vector_size": 768,
        "distance_metric": "cosine",
    }

    cfg = SimpleNamespace(
        app_version="0.1.0",
        env="development",
        debug=False,
        log_level="INFO",
        ollama=SimpleNamespace(model="m", embed_model="e", host="http://ollama:11434", timeout=300),
        qdrant=SimpleNamespace(collection_name="documents", host="qdrant", port=6333, vector_size=768),
        meilisearch=SimpleNamespace(index_name="documents", host="http://meilisearch:7700"),
        security=SimpleNamespace(
            llm_guard_enabled=False,
            llm_guard_input_scan=True,
            llm_guard_output_scan=True,
            max_input_length=10000,
            max_output_length=5000,
        ),
        langfuse=SimpleNamespace(enabled=True, host="http://langfuse:3000"),
    )

    with patch("src.services.health_check.HealthChecker", return_value=checker), patch(
        "src.services.qdrant_client.QdrantVectorClient", return_value=qdrant
    ), patch("src.config.get_config", return_value=cfg):
        await main_module.on_system_health_action(SimpleNamespace())
        await main_module.on_qdrant_info_action(SimpleNamespace())
        await main_module.on_settings_info_action(SimpleNamespace())

    full_output = "\n".join(msg.content for msg in mock_chainlit["messages"])
    assert "System Health Report" in full_output
    assert "Qdrant Vector Database Info" in full_output
    assert "Agent Zero Configuration" in full_output
