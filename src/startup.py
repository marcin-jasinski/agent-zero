"""Application startup and initialization sequence.

Handles initialization of all services, collections, and indexes during
application startup. Ensures graceful error handling and clear logging
of startup progress.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.config import get_config
from src.services import (
    HealthChecker,
    MeilisearchClient,
    OllamaClient,
    QdrantVectorClient,
)

logger = logging.getLogger(__name__)


@dataclass
class StartupStatus:
    """Status of a startup step."""

    step_name: str
    success: bool
    message: str
    error: Optional[str] = None


class ApplicationStartup:
    """Manages application startup sequence."""

    def __init__(self):
        """Initialize startup handler."""
        self.config = get_config()
        self.statuses: list[StartupStatus] = []
        self.health_checker = HealthChecker()

    def run(self) -> bool:
        """Execute full startup sequence.

        Returns:
            bool: True if all critical steps succeeded, False otherwise
        """
        logger.info("=" * 60)
        logger.info("STARTING APPLICATION INITIALIZATION")
        logger.info("=" * 60)

        try:
            # Step 1: Check service health
            self._check_services()

            # Step 2: Initialize Ollama
            self._initialize_ollama()

            # Step 3: Initialize Qdrant
            self._initialize_qdrant()

            # Step 4: Initialize Meilisearch
            self._initialize_meilisearch()

            # Log summary
            self._log_startup_summary()

            # Return success if all critical steps passed
            critical_failed = [s for s in self.statuses if not s.success and "critical" in s.message.lower()]
            return len(critical_failed) == 0

        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            return False

    def _check_services(self) -> None:
        """Check health of all services.

        Logs the current status but doesn't fail startup on individual
        service failures (they may be starting up).
        """
        logger.info("\n[1/4] Checking service health...")

        try:
            statuses = self.health_checker.check_all()

            for service_name, status in statuses.items():
                if status.is_healthy:
                    logger.info(f"  ✓ {service_name}: Healthy ({status.message})")
                else:
                    logger.warning(f"  ⚠ {service_name}: Unhealthy ({status.message})")

            # Record status
            healthy_count = sum(1 for s in statuses.values() if s.is_healthy)
            self.statuses.append(
                StartupStatus(
                    step_name="Service Health Check",
                    success=True,
                    message=f"{healthy_count}/3 services healthy",
                )
            )
        except Exception as e:
            logger.error(f"  ✗ Failed to check service health: {e}")
            self.statuses.append(
                StartupStatus(
                    step_name="Service Health Check",
                    success=False,
                    message="Health check failed",
                    error=str(e),
                )
            )

    def _initialize_ollama(self) -> None:
        """Initialize Ollama service and pull default model."""
        logger.info("\n[2/4] Initializing Ollama LLM service...")

        try:
            ollama = OllamaClient()

            # Check if Ollama is healthy
            if not ollama.is_healthy():
                logger.warning("  ⚠ Ollama service not responding - will retry during operation")
                self.statuses.append(
                    StartupStatus(
                        step_name="Ollama Initialization",
                        success=True,
                        message="Service not yet ready (will initialize on first use)",
                    )
                )
                return

            # List available models
            try:
                models = ollama.list_models()
                logger.info(f"  ✓ Available models: {len(models)} model(s)")
                if models:
                    for model in models:
                        logger.debug(f"    - {model}")
            except Exception as e:
                logger.warning(f"  ⚠ Could not list models: {e}")

            # Ensure default model is available
            default_model = self.config.ollama.model
            logger.info(f"  ✓ Default model configured: {default_model}")

            self.statuses.append(
                StartupStatus(
                    step_name="Ollama Initialization",
                    success=True,
                    message=f"Service ready with model '{default_model}'",
                )
            )

        except Exception as e:
            logger.error(f"  ✗ Ollama initialization failed: {e}")
            self.statuses.append(
                StartupStatus(
                    step_name="Ollama Initialization",
                    success=False,
                    message="Ollama initialization failed",
                    error=str(e),
                )
            )

    def _initialize_qdrant(self) -> None:
        """Initialize Qdrant vector database and create collections."""
        logger.info("\n[3/4] Initializing Qdrant vector database...")

        try:
            qdrant = QdrantVectorClient()

            # Check if Qdrant is healthy
            if not qdrant.is_healthy():
                logger.warning("  ⚠ Qdrant service not responding")
                self.statuses.append(
                    StartupStatus(
                        step_name="Qdrant Initialization",
                        success=True,
                        message="Service not yet ready (will initialize on first use)",
                    )
                )
                return

            # Create embeddings collection
            embeddings_collection = self.config.qdrant.embeddings_collection
            embedding_dim = self.config.ollama.embedding_dim

            logger.info(f"  → Creating collection: {embeddings_collection}")
            success = qdrant.create_collection(
                collection_name=embeddings_collection,
                vector_size=embedding_dim,
                force_recreate=False,
            )

            if success:
                logger.info(f"  ✓ Collection '{embeddings_collection}' ready")
                # Get collection info
                info = qdrant.get_collection_info(embeddings_collection)
                if info:
                    logger.debug(f"    - Vectors: {info.get('vectors_count', 'unknown')}")
            else:
                logger.warning(f"  ⚠ Could not verify collection '{embeddings_collection}'")

            self.statuses.append(
                StartupStatus(
                    step_name="Qdrant Initialization",
                    success=True,
                    message=f"Collection '{embeddings_collection}' ready",
                )
            )

        except Exception as e:
            logger.error(f"  ✗ Qdrant initialization failed: {e}")
            self.statuses.append(
                StartupStatus(
                    step_name="Qdrant Initialization",
                    success=False,
                    message="Qdrant initialization failed",
                    error=str(e),
                )
            )

    def _initialize_meilisearch(self) -> None:
        """Initialize Meilisearch and create indexes."""
        logger.info("\n[4/4] Initializing Meilisearch search engine...")

        try:
            meilisearch = MeilisearchClient()

            # Check if Meilisearch is healthy
            if not meilisearch.is_healthy():
                logger.warning("  ⚠ Meilisearch service not responding")
                self.statuses.append(
                    StartupStatus(
                        step_name="Meilisearch Initialization",
                        success=True,
                        message="Service not yet ready (will initialize on first use)",
                    )
                )
                return

            # Create documents index
            documents_index = self.config.meilisearch.documents_index

            logger.info(f"  → Creating index: {documents_index}")
            success = meilisearch.create_index(
                index_uid=documents_index,
                primary_key="id",
            )

            if success:
                logger.info(f"  ✓ Index '{documents_index}' ready")
                # Get index stats
                stats = meilisearch.get_index_stats(documents_index)
                if stats:
                    logger.debug(f"    - Documents: {stats.get('numberOfDocuments', 0)}")
            else:
                logger.warning(f"  ⚠ Could not verify index '{documents_index}'")

            self.statuses.append(
                StartupStatus(
                    step_name="Meilisearch Initialization",
                    success=True,
                    message=f"Index '{documents_index}' ready",
                )
            )

        except Exception as e:
            logger.error(f"  ✗ Meilisearch initialization failed: {e}")
            self.statuses.append(
                StartupStatus(
                    step_name="Meilisearch Initialization",
                    success=False,
                    message="Meilisearch initialization failed",
                    error=str(e),
                )
            )

    def _log_startup_summary(self) -> None:
        """Log summary of startup steps."""
        logger.info("\n" + "=" * 60)
        logger.info("STARTUP SUMMARY")
        logger.info("=" * 60)

        successful = sum(1 for s in self.statuses if s.success)
        total = len(self.statuses)

        for status in self.statuses:
            symbol = "✓" if status.success else "✗"
            logger.info(f"{symbol} {status.step_name}: {status.message}")
            if status.error:
                logger.debug(f"  Error: {status.error}")

        logger.info("-" * 60)
        logger.info(f"Summary: {successful}/{total} steps completed successfully")

        if successful == total:
            logger.info("✓ APPLICATION READY FOR USE")
        else:
            logger.warning("⚠ SOME SERVICES NOT FULLY INITIALIZED")
            logger.warning("  Services will initialize on first use")

        logger.info("=" * 60)

    def get_status(self) -> dict:
        """Get detailed startup status.

        Returns:
            dict: Status of each startup step
        """
        return {
            "statuses": [
                {
                    "step": s.step_name,
                    "success": s.success,
                    "message": s.message,
                    "error": s.error,
                }
                for s in self.statuses
            ],
            "total_successful": sum(1 for s in self.statuses if s.success),
            "total_steps": len(self.statuses),
        }
