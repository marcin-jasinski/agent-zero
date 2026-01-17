"""Service Health Check Module.

Provides health check functionality for all external services.
"""

import logging
from dataclasses import dataclass
from typing import Dict

from src.services.meilisearch_client import MeilisearchClient
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantVectorClient

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Represents the health status of a service."""

    name: str
    is_healthy: bool
    message: str = ""
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class HealthChecker:
    """Health checker for all Agent Zero services."""

    def __init__(self):
        """Initialize health checker with service clients."""
        self._ollama_client = None
        self._qdrant_client = None
        self._meilisearch_client = None

    def _get_ollama_client(self) -> OllamaClient:
        """Get or create Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = OllamaClient()
        return self._ollama_client

    def _get_qdrant_client(self) -> QdrantVectorClient:
        """Get or create Qdrant client."""
        if self._qdrant_client is None:
            self._qdrant_client = QdrantVectorClient()
        return self._qdrant_client

    def _get_meilisearch_client(self) -> MeilisearchClient:
        """Get or create Meilisearch client."""
        if self._meilisearch_client is None:
            self._meilisearch_client = MeilisearchClient()
        return self._meilisearch_client

    def check_ollama(self) -> ServiceStatus:
        """Check Ollama LLM service health."""
        try:
            client = self._get_ollama_client()
            is_healthy = client.is_healthy()

            if is_healthy:
                models = client.list_models()
                return ServiceStatus(
                    name="Ollama",
                    is_healthy=True,
                    message="LLM inference service is operational",
                    details={"models_available": len(models), "default_model": "ministral-3:3b"},
                )
            else:
                return ServiceStatus(
                    name="Ollama",
                    is_healthy=False,
                    message="Service not responding to health check",
                )
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return ServiceStatus(
                name="Ollama",
                is_healthy=False,
                message=f"Connection error: {str(e)}",
            )

    def check_qdrant(self) -> ServiceStatus:
        """Check Qdrant vector database health."""
        try:
            client = self._get_qdrant_client()
            is_healthy = client.is_healthy()

            if is_healthy:
                return ServiceStatus(
                    name="Qdrant",
                    is_healthy=True,
                    message="Vector database is operational",
                    details={"vector_size": 768},
                )
            else:
                return ServiceStatus(
                    name="Qdrant",
                    is_healthy=False,
                    message="Service not responding to health check",
                )
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return ServiceStatus(
                name="Qdrant",
                is_healthy=False,
                message=f"Connection error: {str(e)}",
            )

    def check_meilisearch(self) -> ServiceStatus:
        """Check Meilisearch full-text search health."""
        try:
            client = self._get_meilisearch_client()
            is_healthy = client.is_healthy()

            if is_healthy:
                indexes = client.list_indexes()
                return ServiceStatus(
                    name="Meilisearch",
                    is_healthy=True,
                    message="Full-text search engine is operational",
                    details={"indexes": len(indexes)},
                )
            else:
                return ServiceStatus(
                    name="Meilisearch",
                    is_healthy=False,
                    message="Service not responding to health check",
                )
        except Exception as e:
            logger.error(f"Meilisearch health check failed: {e}")
            return ServiceStatus(
                name="Meilisearch",
                is_healthy=False,
                message=f"Connection error: {str(e)}",
            )

    def check_all(self) -> Dict[str, ServiceStatus]:
        """Check health of all services.

        Returns:
            Dictionary mapping service names to their status
        """
        logger.info("Performing health check on all services...")

        status_map = {
            "ollama": self.check_ollama(),
            "qdrant": self.check_qdrant(),
            "meilisearch": self.check_meilisearch(),
        }

        # Log overall health
        healthy_count = sum(1 for s in status_map.values() if s.is_healthy)
        total_count = len(status_map)

        logger.info(f"Health check complete: {healthy_count}/{total_count} services healthy")

        return status_map

    @property
    def all_healthy(self) -> bool:
        """Check if all services are healthy.

        Returns:
            True if all services are operational
        """
        status_map = self.check_all()
        return all(status.is_healthy for status in status_map.values())
