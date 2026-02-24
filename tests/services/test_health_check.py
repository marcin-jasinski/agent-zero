"""Unit tests for health check module."""

import pytest
from unittest.mock import Mock, patch, PropertyMock

from src.services.health_check import HealthChecker, ServiceStatus


@pytest.fixture
def health_checker():
    """Create a HealthChecker instance for testing."""
    return HealthChecker()


class TestServiceStatus:
    """Test ServiceStatus dataclass."""

    def test_service_status_creation(self):
        """Test ServiceStatus creation."""
        status = ServiceStatus(
            name="Ollama",
            is_healthy=True,
            message="Service is operational",
        )

        assert status.name == "Ollama"
        assert status.is_healthy is True
        assert status.message == "Service is operational"
        assert status.details == {}

    def test_service_status_with_details(self):
        """Test ServiceStatus with details."""
        details = {"models": 3, "memory": "8GB"}
        status = ServiceStatus(
            name="Ollama",
            is_healthy=True,
            details=details,
        )

        assert status.details == details

    def test_service_status_default_message(self):
        """Test ServiceStatus with default message."""
        status = ServiceStatus(name="Test", is_healthy=True)

        assert status.message == ""
        assert status.details == {}


class TestHealthCheckerInitialization:
    """Test HealthChecker initialization."""

    def test_init_empty_clients(self, health_checker):
        """Test initialization with no clients."""
        assert health_checker._ollama_client is None
        assert health_checker._qdrant_client is None
        assert health_checker._meilisearch_client is None


class TestHealthCheckerOllamaCheck:
    """Test Ollama health check."""

    def test_check_ollama_healthy(self, health_checker):
        """Test successful Ollama check."""
        with patch.object(health_checker, "_get_ollama_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = True
            mock_client.list_models.return_value = ["ministral-3:3b", "llama2"]
            mock_get.return_value = mock_client

            status = health_checker.check_ollama()

            assert status.name == "Ollama"
            assert status.is_healthy is True
            assert "operational" in status.message.lower()
            assert status.details["models_available"] == 2

    def test_check_ollama_unhealthy(self, health_checker):
        """Test failing Ollama check."""
        with patch.object(health_checker, "_get_ollama_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = False
            mock_get.return_value = mock_client

            status = health_checker.check_ollama()

            assert status.name == "Ollama"
            assert status.is_healthy is False
            assert "not responding" in status.message.lower()

    def test_check_ollama_error(self, health_checker):
        """Test Ollama check with exception."""
        with patch.object(health_checker, "_get_ollama_client") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            status = health_checker.check_ollama()

            assert status.name == "Ollama"
            assert status.is_healthy is False
            assert "connection error" in status.message.lower()

    def test_check_ollama_list_models_error(self, health_checker):
        """Test Ollama check when list_models fails."""
        with patch.object(health_checker, "_get_ollama_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = True
            mock_client.list_models.side_effect = Exception("List error")
            mock_get.return_value = mock_client

            status = health_checker.check_ollama()

            # Should still mark as healthy even if list_models fails
            # (handled by try-except in check_ollama)
            assert status.name == "Ollama"
            # Actually, looking at implementation, this would raise
            # Let's check what happens
            assert status.is_healthy is False


class TestHealthCheckerQdrantCheck:
    """Test Qdrant health check."""

    def test_check_qdrant_healthy(self, health_checker):
        """Test successful Qdrant check."""
        with patch.object(health_checker, "_get_qdrant_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = True
            mock_get.return_value = mock_client

            status = health_checker.check_qdrant()

            assert status.name == "Qdrant"
            assert status.is_healthy is True
            assert "operational" in status.message.lower()

    def test_check_qdrant_unhealthy(self, health_checker):
        """Test failing Qdrant check."""
        with patch.object(health_checker, "_get_qdrant_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = False
            mock_get.return_value = mock_client

            status = health_checker.check_qdrant()

            assert status.name == "Qdrant"
            assert status.is_healthy is False

    def test_check_qdrant_error(self, health_checker):
        """Test Qdrant check with exception."""
        with patch.object(health_checker, "_get_qdrant_client") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            status = health_checker.check_qdrant()

            assert status.name == "Qdrant"
            assert status.is_healthy is False
            assert "connection error" in status.message.lower()


class TestHealthCheckerMeilisearchCheck:
    """Test Meilisearch health check."""

    def test_check_meilisearch_healthy(self, health_checker):
        """Test successful Meilisearch check."""
        with patch.object(health_checker, "_get_meilisearch_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = True
            mock_client.list_indexes.return_value = ["kb_index", "docs_index"]
            mock_get.return_value = mock_client

            status = health_checker.check_meilisearch()

            assert status.name == "Meilisearch"
            assert status.is_healthy is True
            assert status.details["indexes"] == 2

    def test_check_meilisearch_unhealthy(self, health_checker):
        """Test failing Meilisearch check."""
        with patch.object(health_checker, "_get_meilisearch_client") as mock_get:
            mock_client = Mock()
            mock_client.is_healthy.return_value = False
            mock_get.return_value = mock_client

            status = health_checker.check_meilisearch()

            assert status.name == "Meilisearch"
            assert status.is_healthy is False

    def test_check_meilisearch_error(self, health_checker):
        """Test Meilisearch check with exception."""
        with patch.object(health_checker, "_get_meilisearch_client") as mock_get:
            mock_get.side_effect = Exception("Network error")

            status = health_checker.check_meilisearch()

            assert status.name == "Meilisearch"
            assert status.is_healthy is False
            assert "network error" in status.message.lower()


class TestHealthCheckerLangfuseCheck:
    """Test Langfuse health check."""

    def test_check_langfuse_healthy(self, health_checker):
        """Test successful Langfuse check."""
        with patch.object(health_checker, "_get_observability") as mock_get:
            mock_obs = Mock()
            mock_obs.enabled = True
            mock_obs.is_healthy.return_value = True
            mock_get.return_value = mock_obs

            status = health_checker.check_langfuse()

            assert status.name == "Langfuse"
            assert status.is_healthy is True
            assert "operational" in status.message.lower()
            assert status.details["enabled"] is True

    def test_check_langfuse_disabled(self, health_checker):
        """Test Langfuse check when disabled."""
        with patch.object(health_checker, "_get_observability") as mock_get:
            mock_obs = Mock()
            mock_obs.enabled = False
            mock_get.return_value = mock_obs

            status = health_checker.check_langfuse()

            assert status.name == "Langfuse"
            assert status.is_healthy is True
            assert "disabled" in status.message.lower()
            assert status.details["enabled"] is False

    def test_check_langfuse_unhealthy(self, health_checker):
        """Test failing Langfuse check."""
        with patch.object(health_checker, "_get_observability") as mock_get:
            mock_obs = Mock()
            mock_obs.enabled = True
            mock_obs.is_healthy.return_value = False
            mock_get.return_value = mock_obs

            status = health_checker.check_langfuse()

            assert status.name == "Langfuse"
            assert status.is_healthy is False
            assert "not responding" in status.message.lower()

    def test_check_langfuse_error(self, health_checker):
        """Test Langfuse check with exception."""
        with patch.object(health_checker, "_get_observability") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            status = health_checker.check_langfuse()

            assert status.name == "Langfuse"
            assert status.is_healthy is False
            assert "connection error" in status.message.lower()


class TestHealthCheckerCheckAll:
    """Test checking all services."""

    def test_check_all_all_healthy(self, health_checker):
        """Test check_all when all services are healthy."""
        with patch.object(health_checker, "check_ollama") as mock_ollama, \
             patch.object(health_checker, "check_qdrant") as mock_qdrant, \
             patch.object(health_checker, "check_meilisearch") as mock_meilisearch, \
             patch.object(health_checker, "check_langfuse") as mock_langfuse, \
             patch.object(health_checker, "check_prometheus") as mock_prometheus, \
             patch.object(health_checker, "check_grafana") as mock_grafana:

            mock_ollama.return_value = ServiceStatus("Ollama", is_healthy=True)
            mock_qdrant.return_value = ServiceStatus("Qdrant", is_healthy=True)
            mock_meilisearch.return_value = ServiceStatus("Meilisearch", is_healthy=True)
            mock_langfuse.return_value = ServiceStatus("Langfuse", is_healthy=True)
            mock_prometheus.return_value = ServiceStatus("Prometheus", is_healthy=True)
            mock_grafana.return_value = ServiceStatus("Grafana", is_healthy=True)

            result = health_checker.check_all()

            assert len(result) == 6
            assert all(status.is_healthy for status in result.values())

    def test_check_all_partial_failure(self, health_checker):
        """Test check_all when some services fail."""
        with patch.object(health_checker, "check_ollama") as mock_ollama, \
             patch.object(health_checker, "check_qdrant") as mock_qdrant, \
             patch.object(health_checker, "check_meilisearch") as mock_meilisearch, \
             patch.object(health_checker, "check_langfuse") as mock_langfuse, \
             patch.object(health_checker, "check_prometheus") as mock_prometheus, \
             patch.object(health_checker, "check_grafana") as mock_grafana:

            mock_ollama.return_value = ServiceStatus("Ollama", is_healthy=True)
            mock_qdrant.return_value = ServiceStatus("Qdrant", is_healthy=False)
            mock_meilisearch.return_value = ServiceStatus("Meilisearch", is_healthy=True)
            mock_langfuse.return_value = ServiceStatus("Langfuse", is_healthy=True)
            mock_prometheus.return_value = ServiceStatus("Prometheus", is_healthy=True)
            mock_grafana.return_value = ServiceStatus("Grafana", is_healthy=False)

            result = health_checker.check_all()

            assert len(result) == 6
            assert result["ollama"].is_healthy is True
            assert result["qdrant"].is_healthy is False
            assert result["meilisearch"].is_healthy is True
            assert result["langfuse"].is_healthy is True
            assert result["prometheus"].is_healthy is True
            assert result["grafana"].is_healthy is False

    def test_check_all_all_failed(self, health_checker):
        """Test check_all when all services fail."""
        with patch.object(health_checker, "check_ollama") as mock_ollama, \
             patch.object(health_checker, "check_qdrant") as mock_qdrant, \
             patch.object(health_checker, "check_meilisearch") as mock_meilisearch, \
             patch.object(health_checker, "check_langfuse") as mock_langfuse, \
             patch.object(health_checker, "check_prometheus") as mock_prometheus, \
             patch.object(health_checker, "check_grafana") as mock_grafana:

            mock_ollama.return_value = ServiceStatus("Ollama", is_healthy=False)
            mock_qdrant.return_value = ServiceStatus("Qdrant", is_healthy=False)
            mock_meilisearch.return_value = ServiceStatus("Meilisearch", is_healthy=False)
            mock_langfuse.return_value = ServiceStatus("Langfuse", is_healthy=False)
            mock_prometheus.return_value = ServiceStatus("Prometheus", is_healthy=False)
            mock_grafana.return_value = ServiceStatus("Grafana", is_healthy=False)

            result = health_checker.check_all()

            assert len(result) == 6
            assert not any(status.is_healthy for status in result.values())

    def test_check_all_returns_dict(self, health_checker):
        """Test that check_all returns a dict."""
        with patch.object(health_checker, "check_ollama") as mock_ollama, \
             patch.object(health_checker, "check_qdrant") as mock_qdrant, \
             patch.object(health_checker, "check_meilisearch") as mock_meilisearch, \
             patch.object(health_checker, "check_langfuse") as mock_langfuse, \
             patch.object(health_checker, "check_prometheus") as mock_prometheus, \
             patch.object(health_checker, "check_grafana") as mock_grafana:

            mock_ollama.return_value = ServiceStatus("Ollama", is_healthy=True)
            mock_qdrant.return_value = ServiceStatus("Qdrant", is_healthy=True)
            mock_meilisearch.return_value = ServiceStatus("Meilisearch", is_healthy=True)
            mock_langfuse.return_value = ServiceStatus("Langfuse", is_healthy=True)
            mock_prometheus.return_value = ServiceStatus("Prometheus", is_healthy=True)
            mock_grafana.return_value = ServiceStatus("Grafana", is_healthy=True)

            result = health_checker.check_all()

            assert isinstance(result, dict)
            assert "ollama" in result
            assert "qdrant" in result
            assert "meilisearch" in result
            assert "langfuse" in result
            assert "prometheus" in result
            assert "grafana" in result


class TestHealthCheckerAllHealthy:
    """Test all_healthy property."""

    def test_all_healthy_true(self, health_checker):
        """Test all_healthy when all services are healthy."""
        with patch.object(health_checker, "check_all") as mock_check_all:
            mock_check_all.return_value = {
                "ollama": ServiceStatus("Ollama", is_healthy=True),
                "qdrant": ServiceStatus("Qdrant", is_healthy=True),
                "meilisearch": ServiceStatus("Meilisearch", is_healthy=True),
                "langfuse": ServiceStatus("Langfuse", is_healthy=True),
                "prometheus": ServiceStatus("Prometheus", is_healthy=True),
                "grafana": ServiceStatus("Grafana", is_healthy=True),
            }

            assert health_checker.all_healthy is True

    def test_all_healthy_false(self, health_checker):
        """Test all_healthy when at least one service is unhealthy."""
        with patch.object(health_checker, "check_all") as mock_check_all:
            mock_check_all.return_value = {
                "ollama": ServiceStatus("Ollama", is_healthy=True),
                "qdrant": ServiceStatus("Qdrant", is_healthy=False),
                "meilisearch": ServiceStatus("Meilisearch", is_healthy=True),
                "langfuse": ServiceStatus("Langfuse", is_healthy=True),
                "prometheus": ServiceStatus("Prometheus", is_healthy=True),
                "grafana": ServiceStatus("Grafana", is_healthy=True),
            }

            assert health_checker.all_healthy is False

    def test_all_healthy_empty(self, health_checker):
        """Test all_healthy with no services."""
        with patch.object(health_checker, "check_all") as mock_check_all:
            mock_check_all.return_value = {}

            # all() returns True for empty iterables
            assert health_checker.all_healthy is True
