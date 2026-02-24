"""Integration tests for the Gradio Admin Dashboard workflow (Phase 6c).

Validates the full admin dashboard flow — health check, Qdrant stats, Langfuse
tracing, Promptfoo report, settings, and logs — using mocked service clients
so tests run offline without Docker.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_status(name: str, healthy: bool, msg: str = "OK") -> SimpleNamespace:
    return SimpleNamespace(name=name, is_healthy=healthy, message=msg, details={})


# ---------------------------------------------------------------------------
# Workflow: full admin dashboard end-to-end
# ---------------------------------------------------------------------------


class TestFullDashboardWorkflow:
    """Exercise all admin tab handlers in sequence."""

    def test_health_then_qdrant_then_settings_workflow(self) -> None:
        """Consecutive admin calls produce non-empty markdown for each section."""
        from src.ui.dashboard import (
            get_health_report,
            get_qdrant_collections,
            get_settings_report,
        )

        # --- Health ---
        checker = MagicMock()
        checker.check_all.return_value = {
            "ollama": _make_status("Ollama", True),
            "qdrant": _make_status("Qdrant", True),
            "meilisearch": _make_status("Meilisearch", True),
        }
        with patch("src.services.health_check.HealthChecker", return_value=checker):
            health_md = get_health_report()
        assert "✅" in health_md
        assert "Ollama" in health_md

        # --- Collections ---
        qdrant = MagicMock()
        qdrant.is_healthy.return_value = True
        qdrant.list_collections.return_value = [
            {"name": "documents", "vectors_count": 512, "points_count": 512},
        ]
        with patch("src.services.qdrant_client.QdrantVectorClient", return_value=qdrant):
            stats_md, names = get_qdrant_collections()
        assert "documents" in stats_md
        assert names == ["documents"]

        # --- Settings (no mocks needed — reads real config) ---
        settings_md = get_settings_report()
        assert len(settings_md) > 50
        assert "Ollama" in settings_md or "LLM" in settings_md

    def test_search_after_collections_workflow(self) -> None:
        """get_qdrant_collections followed by search_qdrant in the same collection."""
        from src.ui.dashboard import get_qdrant_collections, search_qdrant

        qdrant = MagicMock()
        qdrant.is_healthy.return_value = True
        qdrant.list_collections.return_value = [
            {"name": "kb", "vectors_count": 10, "points_count": 10}
        ]
        qdrant.search_by_text.return_value = [
            {"content": "RAG overview document", "source": "rag.pdf", "score": 0.91}
        ]
        ollama = MagicMock()

        with patch("src.services.qdrant_client.QdrantVectorClient", return_value=qdrant):
            _, names = get_qdrant_collections()

        assert "kb" in names

        with (
            patch("src.services.qdrant_client.QdrantVectorClient", return_value=qdrant),
            patch("src.services.ollama_client.OllamaClient", return_value=ollama),
        ):
            result = search_qdrant("RAG", names[0])

        assert "0.91" in result
        assert "rag.pdf" in result

    def test_langfuse_then_promptfoo_workflow(self) -> None:
        """Langfuse report followed by Promptfoo report — both produce output."""
        from src.ui.dashboard import get_langfuse_report, get_promptfoo_report

        summary = SimpleNamespace(total_traces=5, traces_24h=3, avg_latency_ms=420.0, error_rate=0.0)
        trace = SimpleNamespace(name="chat", status="ok", duration_ms=400.0, input_tokens=80, output_tokens=60)
        lf_client = MagicMock()
        lf_client.enabled = True
        lf_client.get_trace_summary.return_value = summary
        lf_client.get_recent_traces.return_value = [trace]

        with patch("src.services.langfuse_client.LangfuseClient", return_value=lf_client):
            lf_report = get_langfuse_report("24h")

        assert "5" in lf_report
        assert "chat" in lf_report

        pf_client = MagicMock()
        pf_client.get_summary_metrics.return_value = {
            "total_scenarios": 2, "total_runs": 4, "average_pass_rate": 91.0
        }
        pf_client.list_scenarios.return_value = [
            SimpleNamespace(name="rag-basic", id="sc-001-xxxx"),
            SimpleNamespace(name="rag-edge", id="sc-002-yyyy"),
        ]
        pf_client.list_runs.return_value = [
            SimpleNamespace(prompt_version="v1", pass_rate=91.0, passed_tests=9, total_tests=10),
        ]

        with patch("src.services.promptfoo_client.PromptfooClient", return_value=pf_client):
            pf_report = get_promptfoo_report()

        assert "rag-basic" in pf_report
        assert "91.0" in pf_report


# ---------------------------------------------------------------------------
# Workflow: degraded services
# ---------------------------------------------------------------------------


class TestDegradedServiceWorkflow:
    """Verify admin tab handlers degrade gracefully when services fail."""

    def test_qdrant_down_collections_and_search_both_fail_gracefully(self) -> None:
        """Unhealthy Qdrant returns error in collections; search short-circuits."""
        from src.ui.dashboard import get_qdrant_collections, search_qdrant

        down_qdrant = MagicMock()
        down_qdrant.is_healthy.return_value = False

        with patch("src.services.qdrant_client.QdrantVectorClient", return_value=down_qdrant):
            stats_md, names = get_qdrant_collections()

        assert "❌" in stats_md
        assert names == []

        # search with empty collection name from step above
        result = search_qdrant("query", "")
        assert "⚠️" in result

    def test_langfuse_disabled_returns_warning(self) -> None:
        """When Langfuse is disabled the report says so clearly."""
        from src.ui.dashboard import get_langfuse_report

        client = MagicMock()
        client.enabled = False

        with patch("src.services.langfuse_client.LangfuseClient", return_value=client):
            result = get_langfuse_report()

        assert "disabled" in result.lower() or "⚠️" in result

    def test_health_exception_does_not_raise(self) -> None:
        """get_health_report wraps exceptions and returns error markdown."""
        from src.ui.dashboard import get_health_report

        with patch("src.services.health_check.HealthChecker", side_effect=RuntimeError("chaos")):
            result = get_health_report()

        assert "❌" in result
        assert "chaos" in result

    def test_promptfoo_empty_scenarios_returns_info(self) -> None:
        """No test scenarios returns a string with info (no crash)."""
        from src.ui.dashboard import get_promptfoo_report

        client = MagicMock()
        client.get_summary_metrics.return_value = {
            "total_scenarios": 0, "total_runs": 0, "average_pass_rate": 0.0
        }
        client.list_scenarios.return_value = []
        client.list_runs.return_value = []

        with patch("src.services.promptfoo_client.PromptfooClient", return_value=client):
            result = get_promptfoo_report()

        assert isinstance(result, str)
        assert len(result) > 10


# ---------------------------------------------------------------------------
# Workflow: logs tab
# ---------------------------------------------------------------------------


class TestLogsWorkflow:
    """Verify logs handler works under various filter combinations."""

    def test_all_filter_combination_returns_string(self) -> None:
        from src.ui.dashboard import get_logs

        result = get_logs(50, "ALL", "ALL")
        assert isinstance(result, str)

    def test_error_filter_returns_string(self) -> None:
        from src.ui.dashboard import get_logs

        result = get_logs(100, "ERROR", "ALL")
        assert isinstance(result, str)

    def test_service_filter_returns_string(self) -> None:
        from src.ui.dashboard import get_logs

        result = get_logs(25, "INFO", "OLLAMA")
        assert isinstance(result, str)
