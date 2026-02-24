"""Observability module for Agent Zero.

Provides centralized observability components including:
- Langfuse integration for LLM tracing
- Prometheus metrics collection
- Callback handlers for LangChain
- Custom metrics tracking

This module follows the "import what you need" pattern - components
are lazy-loaded to avoid circular dependencies and improve startup time.
"""

import logging
import sys

from src.observability.langfuse_callback import (
    LangfuseObservability,
    get_langfuse_observability,
)

logger = logging.getLogger(__name__)

# Metrics are imported on-demand to avoid dependency issues
# if prometheus-client is not installed
try:
    from src.observability.metrics import (
        start_metrics_server,
        track_retrieval,
        track_embedding_duration,
        track_llm_generation,
        track_llm_error,
        track_document_ingestion,
        update_collection_sizes,
        track_llm_guard_scan,
        track_request_latency,
        track_latency,
    )
    METRICS_AVAILABLE = True
except ImportError as e:
    # Print to stderr for immediate visibility (before logging is fully initialized)
    sys.stderr.write(f"Warning: Prometheus metrics unavailable: {e}\n")
    sys.stderr.flush()
    logger.warning("Metrics module unavailable: %s. Prometheus metrics disabled.", e)
    METRICS_AVAILABLE = False

    # Provide no-op fallbacks
    def start_metrics_server(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_retrieval(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_embedding_duration(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_llm_generation(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_llm_error(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_document_ingestion(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def update_collection_sizes(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_llm_guard_scan(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""

    def track_request_latency(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""
        return lambda f: f

    def track_latency(*_args, **_kwargs):
        """No-op fallback when Prometheus is unavailable."""
        return lambda f: f

__all__ = [
    "LangfuseObservability",
    "get_langfuse_observability",
    "start_metrics_server",
    "track_retrieval",
    "track_embedding_duration",
    "track_llm_generation",
    "track_llm_error",
    "track_document_ingestion",
    "update_collection_sizes",
    "track_llm_guard_scan",
    "track_request_latency",
    "track_latency",
    "METRICS_AVAILABLE",
]
