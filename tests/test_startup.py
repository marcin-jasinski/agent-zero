"""Tests for application startup sequence.

Tests the startup module's initialization logic, error handling,
and service integration.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.startup import ApplicationStartup, StartupStatus


class TestStartupStatus:
    """Test StartupStatus dataclass."""

    def test_startup_status_creation(self):
        """Test creating a StartupStatus instance."""
        status = StartupStatus(
            step_name="Test Step",
            success=True,
            message="Test message",
        )

        assert status.step_name == "Test Step"
        assert status.success is True
        assert status.message == "Test message"
        assert status.error is None

    def test_startup_status_with_error(self):
        """Test StartupStatus with error."""
        status = StartupStatus(
            step_name="Failed Step",
            success=False,
            message="Failed message",
            error="Test error",
        )

        assert status.success is False
        assert status.error == "Test error"


class TestApplicationStartupInitialization:
    """Test ApplicationStartup initialization."""

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_initialization(self, mock_health_checker, mock_config):
        """Test ApplicationStartup initialization."""
        startup = ApplicationStartup()

        assert startup.config is not None
        assert startup.statuses == []
        assert startup.health_checker is not None

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_initialization_with_config(self, mock_health_checker, mock_config):
        """Test initialization accesses config."""
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        startup = ApplicationStartup()

        mock_config.assert_called_once()
        assert startup.config == mock_config_instance


class TestHealthCheckStep:
    """Test service health check step."""

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_check_services_all_healthy(self, mock_health_checker, mock_config):
        """Test health check when all services are healthy."""
        startup = ApplicationStartup()
        startup.health_checker.check_all = MagicMock(
            return_value={
                "Ollama": MagicMock(is_healthy=True, message="Running"),
                "Qdrant": MagicMock(is_healthy=True, message="Running"),
                "Meilisearch": MagicMock(is_healthy=True, message="Running"),
            }
        )

        startup._check_services()

        assert len(startup.statuses) == 1
        assert startup.statuses[0].step_name == "Service Health Check"
        assert startup.statuses[0].success is True

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_check_services_partial_healthy(self, mock_health_checker, mock_config):
        """Test health check when some services are unhealthy."""
        startup = ApplicationStartup()
        startup.health_checker.check_all = MagicMock(
            return_value={
                "Ollama": MagicMock(is_healthy=True, message="Running"),
                "Qdrant": MagicMock(is_healthy=False, message="Connection refused"),
                "Meilisearch": MagicMock(is_healthy=True, message="Running"),
            }
        )

        startup._check_services()

        assert startup.statuses[0].success is True  # Health check itself succeeds
        assert "2/3" in startup.statuses[0].message

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_check_services_exception(self, mock_health_checker, mock_config):
        """Test health check with exception."""
        startup = ApplicationStartup()
        startup.health_checker.check_all = MagicMock(
            side_effect=Exception("Connection error")
        )

        startup._check_services()

        assert startup.statuses[0].success is False
        assert startup.statuses[0].error is not None


class TestOllamaInitialization:
    """Test Ollama initialization step."""

    @patch("src.startup.get_config")
    @patch("src.startup.OllamaClient")
    @patch("src.startup.HealthChecker")
    def test_ollama_initialization_success(self, mock_health_checker, mock_ollama_client, mock_config):
        """Test successful Ollama initialization."""
        startup = ApplicationStartup()
        # Mock config with proper string values for model names
        startup.config.ollama = MagicMock()
        startup.config.ollama.model = "mistral"
        startup.config.ollama.embed_model = "nomic-embed-text"

        mock_ollama = MagicMock()
        mock_ollama.is_healthy = MagicMock(return_value=True)
        mock_ollama.list_models = MagicMock(return_value=["mistral", "nomic-embed-text", "llama2"])
        mock_ollama_client.return_value = mock_ollama

        startup._initialize_ollama()

        assert len(startup.statuses) >= 1
        assert any(s.step_name == "Ollama Initialization" for s in startup.statuses)
        ollama_status = [s for s in startup.statuses if s.step_name == "Ollama Initialization"][0]
        assert ollama_status.success is True

    @patch("src.startup.get_config")
    @patch("src.startup.OllamaClient")
    @patch("src.startup.HealthChecker")
    def test_ollama_not_healthy(self, mock_health_checker, mock_ollama_client, mock_config):
        """Test Ollama initialization when service not healthy."""
        startup = ApplicationStartup()
        startup.config.ollama = MagicMock(model="mistral")

        mock_ollama = MagicMock()
        mock_ollama.is_healthy = MagicMock(return_value=False)
        mock_ollama_client.return_value = mock_ollama

        startup._initialize_ollama()

        assert len(startup.statuses) >= 1
        ollama_status = [s for s in startup.statuses if s.step_name == "Ollama Initialization"][0]
        assert ollama_status.success is True  # Graceful degradation
        assert "not ready" in ollama_status.message  # Updated to match new message format

    @patch("src.startup.get_config")
    @patch("src.startup.OllamaClient")
    @patch("src.startup.HealthChecker")
    def test_ollama_initialization_exception(self, mock_health_checker, mock_ollama_client, mock_config):
        """Test Ollama initialization with exception."""
        startup = ApplicationStartup()
        mock_ollama_client.side_effect = Exception("Connection failed")

        startup._initialize_ollama()

        ollama_status = [s for s in startup.statuses if s.step_name == "Ollama Initialization"][0]
        assert ollama_status.success is False
        assert ollama_status.error is not None


class TestQdrantInitialization:
    """Test Qdrant initialization step."""

    @patch("src.startup.get_config")
    @patch("src.startup.QdrantVectorClient")
    @patch("src.startup.HealthChecker")
    def test_qdrant_initialization_success(self, mock_health_checker, mock_qdrant_client, mock_config):
        """Test successful Qdrant initialization."""
        startup = ApplicationStartup()
        startup.config.qdrant = MagicMock(embeddings_collection="embeddings")
        startup.config.ollama = MagicMock(embedding_dim=384)

        mock_qdrant = MagicMock()
        mock_qdrant.is_healthy = MagicMock(return_value=True)
        mock_qdrant.create_collection = MagicMock(return_value=True)
        mock_qdrant.get_collection_info = MagicMock(return_value={"vectors_count": 0})
        mock_qdrant_client.return_value = mock_qdrant

        startup._initialize_qdrant()

        assert len(startup.statuses) >= 1
        qdrant_status = [s for s in startup.statuses if s.step_name == "Qdrant Initialization"][0]
        assert qdrant_status.success is True
        mock_qdrant.create_collection.assert_called_once()

    @patch("src.startup.get_config")
    @patch("src.startup.QdrantVectorClient")
    @patch("src.startup.HealthChecker")
    def test_qdrant_not_healthy(self, mock_health_checker, mock_qdrant_client, mock_config):
        """Test Qdrant initialization when service not healthy."""
        startup = ApplicationStartup()
        startup.config.qdrant = MagicMock(embeddings_collection="embeddings")
        startup.config.ollama = MagicMock(embedding_dim=384)

        mock_qdrant = MagicMock()
        mock_qdrant.is_healthy = MagicMock(return_value=False)
        mock_qdrant_client.return_value = mock_qdrant

        startup._initialize_qdrant()

        qdrant_status = [s for s in startup.statuses if s.step_name == "Qdrant Initialization"][0]
        assert qdrant_status.success is True  # Graceful degradation
        mock_qdrant.create_collection.assert_not_called()

    @patch("src.startup.get_config")
    @patch("src.startup.QdrantVectorClient")
    @patch("src.startup.HealthChecker")
    def test_qdrant_creation_failed(self, mock_health_checker, mock_qdrant_client, mock_config):
        """Test Qdrant collection creation failure."""
        startup = ApplicationStartup()
        startup.config.qdrant = MagicMock(embeddings_collection="embeddings")
        startup.config.ollama = MagicMock(embedding_dim=384)

        mock_qdrant = MagicMock()
        mock_qdrant.is_healthy = MagicMock(return_value=True)
        mock_qdrant.create_collection = MagicMock(return_value=False)
        mock_qdrant_client.return_value = mock_qdrant

        startup._initialize_qdrant()

        qdrant_status = [s for s in startup.statuses if s.step_name == "Qdrant Initialization"][0]
        assert qdrant_status.success is True  # Still succeed (graceful)


class TestMeilisearchInitialization:
    """Test Meilisearch initialization step."""

    @patch("src.startup.get_config")
    @patch("src.startup.MeilisearchClient")
    @patch("src.startup.HealthChecker")
    def test_meilisearch_initialization_success(self, mock_health_checker, mock_meilisearch_client, mock_config):
        """Test successful Meilisearch initialization."""
        startup = ApplicationStartup()
        startup.config.meilisearch = MagicMock(documents_index="documents")

        mock_meilisearch = MagicMock()
        mock_meilisearch.is_healthy = MagicMock(return_value=True)
        mock_meilisearch.create_index = MagicMock(return_value=True)
        mock_meilisearch.get_index_stats = MagicMock(return_value={"numberOfDocuments": 0})
        mock_meilisearch_client.return_value = mock_meilisearch

        startup._initialize_meilisearch()

        meilisearch_status = [s for s in startup.statuses if s.step_name == "Meilisearch Initialization"][0]
        assert meilisearch_status.success is True
        mock_meilisearch.create_index.assert_called_once()

    @patch("src.startup.get_config")
    @patch("src.startup.MeilisearchClient")
    @patch("src.startup.HealthChecker")
    def test_meilisearch_not_healthy(self, mock_health_checker, mock_meilisearch_client, mock_config):
        """Test Meilisearch initialization when service not healthy."""
        startup = ApplicationStartup()
        startup.config.meilisearch = MagicMock(documents_index="documents")

        mock_meilisearch = MagicMock()
        mock_meilisearch.is_healthy = MagicMock(return_value=False)
        mock_meilisearch_client.return_value = mock_meilisearch

        startup._initialize_meilisearch()

        meilisearch_status = [s for s in startup.statuses if s.step_name == "Meilisearch Initialization"][0]
        assert meilisearch_status.success is True  # Graceful degradation
        mock_meilisearch.create_index.assert_not_called()


class TestApplicationStartupRun:
    """Test full startup sequence."""

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    @patch("src.startup.OllamaClient")
    @patch("src.startup.QdrantVectorClient")
    @patch("src.startup.MeilisearchClient")
    def test_run_all_successful(
        self,
        mock_meilisearch_client,
        mock_qdrant_client,
        mock_ollama_client,
        mock_health_checker,
        mock_config,
    ):
        """Test successful full startup."""
        startup = ApplicationStartup()

        # Setup mocks with proper string values for model/collection names
        startup.config.ollama = MagicMock()
        startup.config.ollama.model = "mistral"
        startup.config.ollama.embed_model = "nomic-embed-text"
        startup.config.ollama.embedding_dim = 384
        
        startup.config.qdrant = MagicMock()
        startup.config.qdrant.embeddings_collection = "embeddings"
        startup.config.qdrant.collection_name = "embeddings"
        
        startup.config.meilisearch = MagicMock()
        startup.config.meilisearch.documents_index = "documents"
        startup.config.meilisearch.index_name = "documents"

        startup.health_checker.check_all = MagicMock(
            return_value={
                "Ollama": MagicMock(is_healthy=True, message="Running"),
                "Qdrant": MagicMock(is_healthy=True, message="Running"),
                "Meilisearch": MagicMock(is_healthy=True, message="Running"),
            }
        )

        mock_ollama = MagicMock()
        mock_ollama.is_healthy = MagicMock(return_value=True)
        mock_ollama.list_models = MagicMock(return_value=["mistral", "nomic-embed-text"])
        mock_ollama_client.return_value = mock_ollama

        mock_qdrant = MagicMock()
        mock_qdrant.is_healthy = MagicMock(return_value=True)
        mock_qdrant.create_collection = MagicMock(return_value=True)
        mock_qdrant.get_collection_info = MagicMock(return_value={})
        mock_qdrant_client.return_value = mock_qdrant

        mock_meilisearch = MagicMock()
        mock_meilisearch.is_healthy = MagicMock(return_value=True)
        mock_meilisearch.create_index = MagicMock(return_value=True)
        mock_meilisearch.get_index_stats = MagicMock(return_value={})
        mock_meilisearch_client.return_value = mock_meilisearch

        result = startup.run()

        assert result is True
        assert len(startup.statuses) == 4
        assert all(s.success for s in startup.statuses)

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_run_with_exception(self, mock_health_checker, mock_config):
        """Test startup with unexpected exception."""
        startup = ApplicationStartup()
        startup._check_services = MagicMock(side_effect=Exception("Unexpected error"))

        result = startup.run()

        assert result is False

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    @patch("src.startup.OllamaClient")
    @patch("src.startup.QdrantVectorClient")
    @patch("src.startup.MeilisearchClient")
    def test_run_partial_failure(
        self,
        mock_meilisearch_client,
        mock_qdrant_client,
        mock_ollama_client,
        mock_health_checker,
        mock_config,
    ):
        """Test startup with partial failure (graceful degradation)."""
        startup = ApplicationStartup()

        startup.config.ollama = MagicMock(model="mistral", embedding_dim=384)
        startup.config.qdrant = MagicMock(embeddings_collection="embeddings")
        startup.config.meilisearch = MagicMock(documents_index="documents")

        startup.health_checker.check_all = MagicMock(
            return_value={
                "Ollama": MagicMock(is_healthy=False, message="Not responding"),
                "Qdrant": MagicMock(is_healthy=True, message="Running"),
                "Meilisearch": MagicMock(is_healthy=True, message="Running"),
            }
        )

        mock_ollama = MagicMock()
        mock_ollama.is_healthy = MagicMock(return_value=False)
        mock_ollama_client.return_value = mock_ollama

        mock_qdrant = MagicMock()
        mock_qdrant.is_healthy = MagicMock(return_value=True)
        mock_qdrant.create_collection = MagicMock(return_value=True)
        mock_qdrant.get_collection_info = MagicMock(return_value={})
        mock_qdrant_client.return_value = mock_qdrant

        mock_meilisearch = MagicMock()
        mock_meilisearch.is_healthy = MagicMock(return_value=True)
        mock_meilisearch.create_index = MagicMock(return_value=True)
        mock_meilisearch.get_index_stats = MagicMock(return_value={})
        mock_meilisearch_client.return_value = mock_meilisearch

        result = startup.run()

        # Still succeeds with graceful degradation
        assert result is True


class TestStartupStatusRetrieval:
    """Test getting startup status."""

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_get_status_empty(self, mock_health_checker, mock_config):
        """Test get_status with no steps executed."""
        startup = ApplicationStartup()

        status = startup.get_status()

        assert status["total_steps"] == 0
        assert status["total_successful"] == 0
        assert status["statuses"] == []

    @patch("src.startup.get_config")
    @patch("src.startup.HealthChecker")
    def test_get_status_after_checks(self, mock_health_checker, mock_config):
        """Test get_status after health checks."""
        startup = ApplicationStartup()
        startup.health_checker.check_all = MagicMock(
            return_value={
                "Ollama": MagicMock(is_healthy=True, message="Running"),
                "Qdrant": MagicMock(is_healthy=True, message="Running"),
                "Meilisearch": MagicMock(is_healthy=True, message="Running"),
            }
        )

        startup._check_services()

        status = startup.get_status()

        assert status["total_steps"] == 1
        assert status["total_successful"] == 1
        assert len(status["statuses"]) == 1
        assert status["statuses"][0]["step"] == "Service Health Check"
        assert status["statuses"][0]["success"] is True
