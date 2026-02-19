"""Tests for Agent Zero FastAPI application entry point (Phase 6c Step 33).

Tests the /health endpoint and application wiring without starting real services.

Strategy: mock the entire Gradio layer (gr.Blocks, gr.Tab, gr.mount_gradio_app)
so that importing src.ui.app does not attempt UI construction or service I/O.
The FastAPI `api` object is then tested in isolation.
"""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def _gradio_disabled():
    """Context manager that mocks out the entire Gradio layer.

    Gradio's Blocks / Tab context managers execute UI-building code at import
    time in src.ui.app.  We replace them with no-op mocks so the module can
    be imported without real service connections.
    """
    # Build a MagicMock that works as a context manager (with gr.Blocks() as x)
    blocks_instance = MagicMock()
    blocks_instance.__enter__ = MagicMock(return_value=blocks_instance)
    blocks_instance.__exit__ = MagicMock(return_value=False)
    # .load() is called with fn/inputs/outputs — must not raise
    blocks_instance.load = MagicMock()

    tab_instance = MagicMock()
    tab_instance.__enter__ = MagicMock(return_value=tab_instance)
    tab_instance.__exit__ = MagicMock(return_value=False)

    mock_gr = MagicMock()
    mock_gr.Blocks.return_value = blocks_instance
    mock_gr.Tab.return_value = tab_instance
    mock_gr.Markdown.return_value = MagicMock()
    mock_gr.mount_gradio_app = lambda app, *a, **kw: app  # returns FastAPI unchanged
    mock_gr.themes = MagicMock()
    mock_gr.Progress = MagicMock()

    with (
        patch.dict(sys.modules, {"gradio": mock_gr}),
        patch("src.ui.chat.build_chat_ui", return_value=(MagicMock(), MagicMock())),
        patch("src.ui.dashboard.build_admin_ui", return_value=None),
    ):
        # Force fresh import of the app module inside this context
        for mod in ["src.ui.app"]:
            sys.modules.pop(mod, None)

        import src.ui.app as app_module  # noqa: E402 (inside context)
        yield app_module

        # Clean up so other tests don't get the cached mock-built module
        sys.modules.pop("src.ui.app", None)


# ---------------------------------------------------------------------------
# Tests: /health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for the FastAPI /health route."""

    def test_health_returns_200(self) -> None:
        from fastapi.testclient import TestClient

        with _gradio_disabled() as app_module:
            client = TestClient(app_module.api)
            response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_ok_status(self) -> None:
        from fastapi.testclient import TestClient

        with _gradio_disabled() as app_module:
            client = TestClient(app_module.api)
            response = client.get("/health")

        assert response.json() == {"status": "ok"}

    def test_health_response_is_json(self) -> None:
        from fastapi.testclient import TestClient

        with _gradio_disabled() as app_module:
            client = TestClient(app_module.api)
            response = client.get("/health")

        assert "application/json" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Tests: application structure
# ---------------------------------------------------------------------------


class TestAppModuleAttributes:
    """Verify that app.py exposes the expected public attributes."""

    def test_api_is_fastapi_instance(self) -> None:
        from fastapi import FastAPI

        with _gradio_disabled() as app_module:
            assert isinstance(app_module.api, FastAPI)

    def test_api_has_health_route(self) -> None:
        with _gradio_disabled() as app_module:
            paths = [r.path for r in app_module.api.routes]
            assert "/health" in paths

    def test_api_title_contains_agent_zero(self) -> None:
        with _gradio_disabled() as app_module:
            assert "Agent Zero" in app_module.api.title
