"""Chainlit chat handler tests for Phase 6b Step 27.

Validates lifecycle handlers in `src.ui.main`:
- `start`
- `main`
- `end`
"""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _load_main_module() -> object:
    """Import and reload `src.ui.main` to ensure mocked Chainlit is used."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


@pytest.mark.asyncio
async def test_chat_start_initializes_agent(mock_chainlit) -> None:
    """`start` stores initialized agent and conversation in session."""
    main_module = _load_main_module()
    mock_agent = MagicMock()

    with patch.object(main_module, "_initialize_agent", return_value=(mock_agent, "conv-123", None)):
        await main_module.start()

    assert mock_chainlit["session"]["agent"] == mock_agent
    assert mock_chainlit["session"]["conversation_id"] == "conv-123"
    assert mock_chainlit["session"]["agent_initialized"] is True


@pytest.mark.asyncio
async def test_chat_start_handles_initialization_error(mock_chainlit) -> None:
    """`start` marks session uninitialized when setup fails."""
    main_module = _load_main_module()

    with patch.object(main_module, "_initialize_agent", return_value=(None, None, "failed")):
        await main_module.start()

    assert mock_chainlit["session"]["agent_initialized"] is False


@pytest.mark.asyncio
async def test_message_processing_success(mock_chainlit) -> None:
    """`main` processes user message and writes response content."""
    main_module = _load_main_module()

    mock_agent = MagicMock()
    mock_chainlit["session"]["agent_initialized"] = True
    mock_chainlit["session"]["agent"] = mock_agent
    mock_chainlit["session"]["conversation_id"] = "conv-123"

    with patch.object(main_module, "_process_message_async", return_value=("response text", None)) as process_mock:
        await main_module.main(SimpleNamespace(content="hello", elements=[]))

    process_mock.assert_called_once_with(mock_agent, "conv-123", "hello")
    assert any(msg.content == "response text" for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_message_processing_requires_initialized_agent(mock_chainlit) -> None:
    """`main` responds with warning when session is not initialized."""
    main_module = _load_main_module()
    mock_chainlit["session"]["agent_initialized"] = False

    await main_module.main(SimpleNamespace(content="hello", elements=[]))

    assert any("Agent not initialized" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_chat_end_runs_without_error(mock_chainlit) -> None:
    """`end` executes cleanly and logs conversation end if present."""
    main_module = _load_main_module()
    mock_chainlit["session"]["conversation_id"] = "conv-123"

    await main_module.end()
