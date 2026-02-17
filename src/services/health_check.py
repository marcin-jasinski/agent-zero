"""Service Health Check Module.

Provides health check functionality for all external services.
"""

import logging
from dataclasses import dataclass
from typing import Dict
import requests

from src.services.meilisearch_client import MeilisearchClient
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantVectorClient
from src.observability import get_langfuse_observability
from src.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


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
        self._observability = None

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

    def _get_observability(self):
        """Get or create Langfuse observability instance."""
        if self._observability is None:
            self._observability = get_langfuse_observability()
        return self._observability

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

    def check_langfuse(self) -> ServiceStatus:
        """Check Langfuse observability service health."""
        try:
            observability = self._get_observability()

            if not observability.enabled:
                return ServiceStatus(
                    name="Langfuse",
                    is_healthy=True,
                    message="Observability disabled (optional)",
                    details={"enabled": False},
                )

            is_healthy = observability.is_healthy()

            if is_healthy:
                return ServiceStatus(
                    name="Langfuse",
                    is_healthy=True,
                    message="Observability service is operational",
                    details={"enabled": True},
                )
            else:
                return ServiceStatus(
                    name="Langfuse",
                    is_healthy=False,
                    message="Service not responding to health check",
                    details={"enabled": True},
                )
        except Exception as e:
            logger.error(f"Langfuse health check failed: {e}")
            return ServiceStatus(
                name="Langfuse",
                is_healthy=False,
                message=f"Connection error: {str(e)}",
                details={"enabled": True},
            )

    def check_prometheus(self) -> ServiceStatus:
        """Check Prometheus metrics service health."""
        try:
            prometheus_url = "http://prometheus:9090"
            response = requests.get(f"{prometheus_url}/-/healthy", timeout=5)
            
            if response.status_code == 200:
                return ServiceStatus(
                    name="Prometheus",
                    is_healthy=True,
                    message="Metrics service is operational",
                    details={"url": prometheus_url},
                )
            else:
                return ServiceStatus(
                    name="Prometheus",
                    is_healthy=False,
                    message=f"Service returned status code {response.status_code}",
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus health check failed: {e}")
            return ServiceStatus(
                name="Prometheus",
                is_healthy=False,
                message=f"Connection error: {str(e)}",
            )

    def check_grafana(self) -> ServiceStatus:
        """Check Grafana visualization service health."""
        try:
            grafana_url = "http://grafana:3000"
            response = requests.get(f"{grafana_url}/api/health", timeout=5)
            
            if response.status_code == 200:
                health_data = response.json()
                return ServiceStatus(
                    name="Grafana",
                    is_healthy=True,
                    message="Visualization service is operational",
                    details={
                        "url": grafana_url,
                        "database": health_data.get("database", "unknown"),
                    },
                )
            else:
                return ServiceStatus(
                    name="Grafana",
                    is_healthy=False,
                    message=f"Service returned status code {response.status_code}",
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Grafana health check failed: {e}")
            return ServiceStatus(
                name="Grafana",
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
            "langfuse": self.check_langfuse(),
            "prometheus": self.check_prometheus(),
            "grafana": self.check_grafana(),
        }

        # Log overall health
        healthy_count = sum(1 for s in status_map.values() if s.is_healthy)
        total_count = len(status_map)

        logger.info(f"Health check complete: {healthy_count}/{total_count} services healthy")

        return status_map

    def check_service(self, service_name: str) -> ServiceStatus:
        """Check health of a specific service by name.
        
        Args:
            service_name: Name of the service to check (ollama, qdrant, meilisearch, langfuse, prometheus, grafana)
            
        Returns:
            ServiceStatus for the requested service, or None if service name is invalid
        """
        service_checks = {
            "ollama": self.check_ollama,
            "qdrant": self.check_qdrant,
            "meilisearch": self.check_meilisearch,
            "langfuse": self.check_langfuse,
            "prometheus": self.check_prometheus,
            "grafana": self.check_grafana,
        }
        
        check_func = service_checks.get(service_name.lower())
        if check_func:
            return check_func()
        
        logger.warning(f"Unknown service name: {service_name}")
        return None

    @property
    def all_healthy(self) -> bool:
        """Check if all services are healthy.

        Returns:
            True if all services are operational
        """
        status_map = self.check_all()
        return all(status.is_healthy for status in status_map.values())
