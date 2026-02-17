"""Chainlit admin slash command tests for migration parity."""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _load_main_module() -> object:
    """Import and reload `src.ui.main` to ensure mocked Chainlit is used."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


@pytest.mark.asyncio
async def test_help_command_renders_admin_help(mock_chainlit) -> None:
    """`/help` should emit admin command guide."""
    main_module = _load_main_module()

    handled = await main_module._try_handle_admin_command("/help")

    assert handled is True
    assert any("Admin Commands" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_logs_command_outputs_filtered_report(mock_chainlit) -> None:
    """`/logs` should return logs report with supplied filters."""
    main_module = _load_main_module()

    with patch.object(main_module, "_tail_logs", return_value="INFO sample log line"):
        handled = await main_module._try_handle_admin_command("/logs 25 INFO AGENT")

    assert handled is True
    assert any("Application Logs" in msg.content for msg in mock_chainlit["messages"])
    assert any("INFO sample log line" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_qdrant_list_command_outputs_collections(mock_chainlit) -> None:
    """`/qdrant list` should show available collections."""
    main_module = _load_main_module()

    qdrant_client = MagicMock()
    qdrant_client.list_collections.return_value = [
        {"name": "documents", "vectors_count": 10, "points_count": 10}
    ]

    with patch("src.services.qdrant_client.QdrantVectorClient", return_value=qdrant_client):
        handled = await main_module._try_handle_admin_command("/qdrant list")

    assert handled is True
    assert any("Qdrant Collections" in msg.content for msg in mock_chainlit["messages"])
    assert any("documents" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_promptfoo_summary_command_outputs_metrics(mock_chainlit) -> None:
    """`/promptfoo summary` should include aggregate metrics."""
    main_module = _load_main_module()

    promptfoo_client = MagicMock()
    promptfoo_client.get_summary_metrics.return_value = {
        "total_scenarios": 2,
        "total_runs": 1,
        "average_pass_rate": 90.0,
        "latest_run": None,
    }
    promptfoo_client.list_scenarios.return_value = []
    promptfoo_client.list_runs.return_value = []

    with patch("src.services.promptfoo_client.PromptfooClient", return_value=promptfoo_client):
        handled = await main_module._try_handle_admin_command("/promptfoo summary")

    assert handled is True
    assert any("Promptfoo Testing Summary" in msg.content for msg in mock_chainlit["messages"])
    assert any("Total Scenarios" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_promptfoo_create_and_delete_commands(mock_chainlit) -> None:
    """`/promptfoo create` and `/promptfoo delete` should manage scenarios."""
    main_module = _load_main_module()

    promptfoo_client = MagicMock()
    promptfoo_client.create_scenario.return_value = SimpleNamespace(name="Smoke", id="abc-123")
    promptfoo_client.delete_scenario.return_value = True

    with patch("src.services.promptfoo_client.PromptfooClient", return_value=promptfoo_client):
        created = await main_module._try_handle_admin_command(
            '/promptfoo create "Smoke" "Basic" "hello"'
        )
        deleted = await main_module._try_handle_admin_command("/promptfoo delete abc-123")

    assert created is True
    assert deleted is True
    assert any("Scenario created" in msg.content for msg in mock_chainlit["messages"])
    assert any("Scenario deleted" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_langfuse_command_outputs_summary(mock_chainlit) -> None:
    """`/langfuse` should include summary and trace rows."""
    main_module = _load_main_module()

    langfuse_client = MagicMock()
    langfuse_client.enabled = True
    langfuse_client.get_trace_summary.return_value = SimpleNamespace(
        total_traces=10,
        traces_24h=4,
        avg_latency_ms=123.0,
        error_rate=5.0,
    )
    langfuse_client.get_recent_traces.return_value = [
        SimpleNamespace(name="chat", status="success", duration_ms=100.0, input_tokens=10, output_tokens=20)
    ]

    with patch("src.services.langfuse_client.LangfuseClient", return_value=langfuse_client):
        handled = await main_module._try_handle_admin_command("/langfuse 24h")

    assert handled is True
    assert any("Langfuse Observability" in msg.content for msg in mock_chainlit["messages"])
    assert any("Recent Traces" in msg.content for msg in mock_chainlit["messages"])