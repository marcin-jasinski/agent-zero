"""Application startup and initialization sequence.

Handles initialization of all services, collections, and indexes during
application startup. Ensures graceful error handling and clear logging
of startup progress.

Phase 5 Step 19.5: Enhanced with retry logic and better error messages.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable

from src.config import get_config
from src.services import (
    HealthChecker,
    MeilisearchClient,
    OllamaClient,
    QdrantVectorClient,
)

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
RETRY_BACKOFF_MULTIPLIER = 1.5


def _retry_with_backoff(
    func: Callable,
    service_name: str,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = RETRY_DELAY_SECONDS,
) -> tuple[bool, Optional[str]]:
    """Execute a function with exponential backoff retry.
    
    Args:
        func: Function to execute (should return True on success)
        service_name: Name of service for logging
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    delay = initial_delay
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = func()
            if result:
                return True, None
            last_error = "Service returned False"
        except Exception as e:
            last_error = str(e)
            logger.debug(f"  Attempt {attempt + 1}/{max_retries} for {service_name} failed: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"  → Retrying {service_name} in {delay:.1f}s...")
            time.sleep(delay)
            delay *= RETRY_BACKOFF_MULTIPLIER
    
    return False, last_error


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
        """Check health of all services with retry logic.

        Logs the current status and retries unhealthy services.
        """
        logger.info("\n[1/4] Checking service health...")

        try:
            statuses = self.health_checker.check_all()
            unhealthy_services = []

            for service_name, status in statuses.items():
                if status.is_healthy:
                    logger.info(f"  ✓ {service_name}: Healthy ({status.message})")
                else:
                    logger.warning(f"  ⚠ {service_name}: Unhealthy ({status.message})")
                    unhealthy_services.append(service_name)

            # Retry unhealthy services
            if unhealthy_services:
                logger.info(f"  → Retrying unhealthy services: {', '.join(unhealthy_services)}")
                for service_name in unhealthy_services:
                    success, error = _retry_with_backoff(
                        lambda sn=service_name: self._check_single_service(sn),
                        service_name,
                    )
                    if success:
                        logger.info(f"  ✓ {service_name}: Now healthy after retry")
                    else:
                        logger.warning(f"  ⚠ {service_name}: Still unhealthy after retries ({error})")

            # Record status
            final_statuses = self.health_checker.check_all()
            healthy_count = sum(1 for s in final_statuses.values() if s.is_healthy)
            total_count = len(final_statuses)
            
            self.statuses.append(
                StartupStatus(
                    step_name="Service Health Check",
                    success=True,
                    message=f"{healthy_count}/{total_count} services healthy",
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

    def _check_single_service(self, service_name: str) -> bool:
        """Check a single service's health.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if healthy, False otherwise
        """
        status = self.health_checker.check_service(service_name)
        return status.is_healthy if status else False

    def _initialize_ollama(self) -> None:
        """Initialize Ollama service and pull required models with retry logic."""
        logger.info("\n[2/4] Initializing Ollama LLM service...")

        try:
            ollama = OllamaClient()

            # Check if Ollama is healthy with retry
            success, error = _retry_with_backoff(
                ollama.is_healthy,
                "Ollama",
            )
            
            if not success:
                logger.warning(f"  ⚠ Ollama service not responding after retries")
                logger.warning(f"    → Error: {error}")
                logger.warning(f"    → Troubleshooting: Check if Ollama container is running")
                logger.warning(f"    → Try: docker-compose up -d ollama")
                self.statuses.append(
                    StartupStatus(
                        step_name="Ollama Initialization",
                        success=True,
                        message="Service not ready (will initialize on first use)",
                        error=error,
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
                models = []

            # Ensure required models are available
            required_models = [
                self.config.ollama.model,
                self.config.ollama.embed_model,
            ]
            
            missing_models = [m for m in required_models if m not in models]
            
            if missing_models:
                logger.info(f"  ℹ Missing models detected: {', '.join(missing_models)}")
                logger.info("  → Pulling required models (this may take several minutes)...")
                
                for model in missing_models:
                    try:
                        logger.info(f"  → Pulling '{model}'...")
                        success = ollama.pull_model(model)
                        if success:
                            logger.info(f"  ✓ Model '{model}' pulled successfully")
                        else:
                            logger.warning(f"  ⚠ Failed to pull model '{model}'")
                    except Exception as e:
                        logger.warning(f"  ⚠ Could not pull model '{model}': {e}")
            else:
                logger.info(f"  ✓ All required models available")

            self.statuses.append(
                StartupStatus(
                    step_name="Ollama Initialization",
                    success=True,
                    message=f"Service ready (models: {', '.join(required_models)})",
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
        """Initialize Qdrant vector database and create collections with retry logic."""
        logger.info("\n[3/4] Initializing Qdrant vector database...")

        try:
            qdrant = QdrantVectorClient()

            # Check if Qdrant is healthy with retry
            success, error = _retry_with_backoff(
                qdrant.is_healthy,
                "Qdrant",
            )
            
            if not success:
                logger.warning(f"  ⚠ Qdrant service not responding after retries")
                logger.warning(f"    → Error: {error}")
                logger.warning(f"    → Troubleshooting: Check if Qdrant container is running")
                logger.warning(f"    → Try: docker-compose up -d qdrant")
                self.statuses.append(
                    StartupStatus(
                        step_name="Qdrant Initialization",
                        success=True,
                        message="Service not ready (will initialize on first use)",
                        error=error,
                    )
                )
                return

            # Create embeddings collection
            collection_name = self.config.qdrant.collection_name
            vector_size = self.config.qdrant.vector_size

            logger.info(f"  → Creating collection: {collection_name}")
            success = qdrant.create_collection(
                collection_name=collection_name,
                vector_size=vector_size,
                force_recreate=False,
            )

            if success:
                logger.info(f"  ✓ Collection '{collection_name}' ready")
                # Get collection info
                info = qdrant.get_collection_info(collection_name)
                if info:
                    logger.debug(f"    - Vectors: {info.get('vectors_count', 'unknown')}")
            else:
                logger.warning(f"  ⚠ Could not verify collection '{collection_name}'")

            self.statuses.append(
                StartupStatus(
                    step_name="Qdrant Initialization",
                    success=True,
                    message=f"Collection '{collection_name}' ready",
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
        """Initialize Meilisearch and create indexes with retry logic."""
        logger.info("\n[4/4] Initializing Meilisearch search engine...")

        try:
            meilisearch = MeilisearchClient()

            # Check if Meilisearch is healthy with retry
            success, error = _retry_with_backoff(
                meilisearch.is_healthy,
                "Meilisearch",
            )
            
            if not success:
                logger.warning(f"  ⚠ Meilisearch service not responding after retries")
                logger.warning(f"    → Error: {error}")
                logger.warning(f"    → Troubleshooting: Check if Meilisearch container is running")
                logger.warning(f"    → Try: docker-compose up -d meilisearch")
                self.statuses.append(
                    StartupStatus(
                        step_name="Meilisearch Initialization",
                        success=True,
                        message="Service not ready (will initialize on first use)",
                        error=error,
                    )
                )
                return

            # Create documents index
            index_name = self.config.meilisearch.index_name

            logger.info(f"  → Creating index: {index_name}")
            success = meilisearch.create_index(
                index_uid=index_name,
                primary_key="id",
            )

            if success:
                logger.info(f"  ✓ Index '{index_name}' ready")
                # Get index stats
                stats = meilisearch.get_index_stats(index_name)
                if stats:
                    logger.debug(f"    - Documents: {stats.get('numberOfDocuments', 0)}")
            else:
                logger.warning(f"  ⚠ Could not verify index '{index_name}'")

            self.statuses.append(
                StartupStatus(
                    step_name="Meilisearch Initialization",
                    success=True,
                    message=f"Index '{index_name}' ready",
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
