"""Chainlit action callback tests for Phase 6b Step 27."""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _load_main_module() -> object:
    """Import and reload `src.ui.main` to ensure mocked Chainlit is used."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


@pytest.mark.asyncio
async def test_system_health_action_sends_report(mock_chainlit) -> None:
    """System health action sends status message."""
    main_module = _load_main_module()

    healthy_status = SimpleNamespace(
        name="Ollama",
        is_healthy=True,
        message="OK",
        details={"models": 1},
    )
    checker = MagicMock()
    checker.check_all.return_value = {"ollama": healthy_status}

    with patch("src.services.health_check.HealthChecker", return_value=checker):
        await main_module.on_system_health_action(SimpleNamespace())

    assert any("System Health Report" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_qdrant_info_action_sends_collection_info(mock_chainlit) -> None:
    """Qdrant action shows collection statistics when collection exists."""
    main_module = _load_main_module()

    qdrant_client = MagicMock()
    qdrant_client.is_healthy.return_value = True
    qdrant_client.list_collections.return_value = [{"name": "documents", "vectors_count": 10}]
    qdrant_client.get_collection_stats.return_value = {
        "vectors_count": 10,
        "points_count": 10,
        "vector_size": 768,
        "distance_metric": "cosine",
    }

    cfg = SimpleNamespace(qdrant=SimpleNamespace(collection_name="documents"))

    with patch("src.services.qdrant_client.QdrantVectorClient", return_value=qdrant_client), patch(
        "src.config.get_config",
        return_value=cfg,
    ):
        await main_module.on_qdrant_info_action(SimpleNamespace())

    assert any("Qdrant Vector Database Info" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_settings_action_sends_configuration(mock_chainlit) -> None:
    """Settings action renders current app configuration summary."""
    main_module = _load_main_module()

    cfg = SimpleNamespace(
        app_version="0.1.0",
        env="development",
        debug=False,
        log_level="INFO",
        ollama=SimpleNamespace(
            model="m",
            embed_model="e",
            host="http://ollama:11434",
            timeout=300,
        ),
        qdrant=SimpleNamespace(
            collection_name="documents",
            host="qdrant",
            port=6333,
            vector_size=768,
        ),
        meilisearch=SimpleNamespace(
            index_name="documents",
            host="http://meilisearch:7700",
        ),
        security=SimpleNamespace(
            llm_guard_enabled=False,
            llm_guard_input_scan=True,
            llm_guard_output_scan=True,
            max_input_length=10000,
            max_output_length=5000,
        ),
        langfuse=SimpleNamespace(
            enabled=True,
            host="http://langfuse:3000",
        ),
    )

    with patch("src.config.get_config", return_value=cfg):
        await main_module.on_settings_info_action(SimpleNamespace())

    assert any("Agent Zero Configuration" in msg.content for msg in mock_chainlit["messages"])
