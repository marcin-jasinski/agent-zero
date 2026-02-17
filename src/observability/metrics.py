"""Prometheus metrics instrumentation for Agent Zero.

This module provides centralized metrics collection using Prometheus client library.
Implements counters, histograms, gauges, and summaries for application observability.

Usage:
    from src.observability.metrics import (
        track_request,
        track_retrieval,
        track_llm_generation,
        start_metrics_server
    )
    
    # Start metrics server (typically in main.py)
    start_metrics_server(port=9091)
    
    # Track operations using decorators or direct calls
    @track_request_latency('chat')
    def process_chat(message: str) -> str:
        ...
"""

import logging
import time
from functools import wraps
from typing import Callable, Optional, Any

from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server

logger = logging.getLogger(__name__)


# =============================================================================
# Request Metrics
# =============================================================================

requests_total = Counter(
    'agent_zero_requests_total',
    'Total number of requests processed',
    ['endpoint', 'status']
)

request_duration_seconds = Histogram(
    'agent_zero_request_duration_seconds',
    'Request processing duration in seconds',
    ['endpoint'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))
)

active_requests = Gauge(
    'agent_zero_active_requests',
    'Number of requests currently being processed',
    ['endpoint']
)


# =============================================================================
# RAG Pipeline Metrics
# =============================================================================

retrieval_documents_count = Histogram(
    'agent_zero_retrieval_documents_count',
    'Number of documents retrieved per query',
    ['retrieval_type'],  # semantic, keyword, hybrid
    buckets=(0, 1, 2, 5, 10, 20, 50, 100, float('inf'))
)

retrieval_duration_seconds = Histogram(
    'agent_zero_retrieval_duration_seconds',
    'Document retrieval duration in seconds',
    ['retrieval_type'],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, float('inf'))
)

embedding_duration_seconds = Histogram(
    'agent_zero_embedding_duration_seconds',
    'Embedding generation duration in seconds',
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, float('inf'))
)

vector_search_duration_seconds = Histogram(
    'agent_zero_vector_search_duration_seconds',
    'Vector database search duration in seconds',
    ['database'],  # qdrant, meilisearch
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, float('inf'))
)


# =============================================================================
# LLM Metrics
# =============================================================================

llm_tokens_total = Counter(
    'agent_zero_llm_tokens_total',
    'Total number of tokens processed',
    ['type', 'model']  # type: input, output
)

llm_generation_duration_seconds = Histogram(
    'agent_zero_llm_generation_duration_seconds',
    'LLM generation duration in seconds',
    ['model'],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))
)

llm_errors_total = Counter(
    'agent_zero_llm_errors_total',
    'Total number of LLM errors',
    ['error_type']  # timeout, connection_error, rate_limit, etc.
)


# =============================================================================
# Document Ingestion Metrics
# =============================================================================

documents_ingested_total = Counter(
    'agent_zero_documents_ingested_total',
    'Total number of documents ingested',
    ['status']  # success, failed, skipped_duplicate
)

chunks_processed_total = Counter(
    'agent_zero_chunks_processed_total',
    'Total number of document chunks processed',
    ['status']  # success, failed
)

ingestion_duration_seconds = Histogram(
    'agent_zero_ingestion_duration_seconds',
    'Document ingestion duration in seconds',
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf'))
)


# =============================================================================
# Database Metrics
# =============================================================================

qdrant_collection_size = Gauge(
    'agent_zero_qdrant_collection_size',
    'Number of vectors in Qdrant collection',
    ['collection']
)

meilisearch_index_size = Gauge(
    'agent_zero_meilisearch_index_size',
    'Number of documents in Meilisearch index',
    ['index']
)


# =============================================================================
# Security Metrics
# =============================================================================

llm_guard_scans_total = Counter(
    'agent_zero_llm_guard_scans_total',
    'Total number of LLM Guard scans',
    ['type', 'result']  # type: input, output; result: safe, unsafe
)

llm_guard_threats_total = Counter(
    'agent_zero_llm_guard_threats_total',
    'Total number of detected threats',
    ['threat_level']  # low, medium, high, critical
)


# =============================================================================
# Decorators for Automatic Tracking
# =============================================================================

def track_request_latency(endpoint: str) -> Callable:
    """Decorator to track request latency and count.
    
    Args:
        endpoint: Endpoint name (e.g., 'chat', 'knowledge_base')
        
    Usage:
        @track_request_latency('chat')
        def process_chat_request(message: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            active_requests.labels(endpoint=endpoint).inc()
            
            start = time.time()
            status = 'success'
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start
                request_duration_seconds.labels(endpoint=endpoint).observe(duration)
                requests_total.labels(endpoint=endpoint, status=status).inc()
                active_requests.labels(endpoint=endpoint).dec()
        
        return wrapper
    return decorator


def track_latency(metric: Histogram, **labels: Any) -> Callable:
    """Generic decorator to track function execution time.
    
    Args:
        metric: Prometheus Histogram metric to observe
        **labels: Label values for the metric
        
    Usage:
        @track_latency(embedding_duration_seconds)
        def generate_embedding(text: str) -> list[float]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                metric.labels(**labels).observe(time.time() - start)
                return result
            except Exception:
                metric.labels(**labels).observe(time.time() - start)
                raise
        return wrapper
    return decorator


# =============================================================================
# Helper Functions
# =============================================================================

def track_retrieval(
    retrieval_type: str,
    document_count: int,
    duration_seconds: float
) -> None:
    """Track document retrieval metrics.
    
    Args:
        retrieval_type: Type of retrieval ('semantic', 'keyword', 'hybrid')
        document_count: Number of documents retrieved
        duration_seconds: Retrieval duration in seconds
    """
    retrieval_documents_count.labels(retrieval_type=retrieval_type).observe(document_count)
    retrieval_duration_seconds.labels(retrieval_type=retrieval_type).observe(duration_seconds)


def track_embedding_duration(duration_seconds: float) -> None:
    """Track embedding generation duration.
    
    Args:
        duration_seconds: Embedding generation duration in seconds
    """
    embedding_duration_seconds.observe(duration_seconds)


def track_llm_generation(
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_seconds: float
) -> None:
    """Track LLM generation metrics.
    
    Args:
        model: Model name (e.g., 'ministral-3:3b')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        duration_seconds: Generation duration in seconds
    """
    llm_tokens_total.labels(type='input', model=model).inc(input_tokens)
    llm_tokens_total.labels(type='output', model=model).inc(output_tokens)
    llm_generation_duration_seconds.labels(model=model).observe(duration_seconds)


def track_llm_error(error_type: str) -> None:
    """Track LLM error.
    
    Args:
        error_type: Error type ('timeout', 'connection_error', 'rate_limit', etc.)
    """
    llm_errors_total.labels(error_type=error_type).inc()


def track_document_ingestion(
    status: str,
    chunk_count: int,
    duration_seconds: float
) -> None:
    """Track document ingestion metrics.
    
    Args:
        status: Ingestion status ('success', 'failed', 'skipped_duplicate')
        chunk_count: Number of chunks processed
        duration_seconds: Ingestion duration in seconds
    """
    documents_ingested_total.labels(status=status).inc()
    if status == 'success':
        chunks_processed_total.labels(status='success').inc(chunk_count)
    ingestion_duration_seconds.observe(duration_seconds)


def update_collection_sizes(
    qdrant_collection: str,
    qdrant_size: int,
    meilisearch_index: str,
    meilisearch_size: int
) -> None:
    """Update database collection size gauges.
    
    Args:
        qdrant_collection: Qdrant collection name
        qdrant_size: Number of vectors in collection
        meilisearch_index: Meilisearch index name
        meilisearch_size: Number of documents in index
    """
    qdrant_collection_size.labels(collection=qdrant_collection).set(qdrant_size)
    meilisearch_index_size.labels(index=meilisearch_index).set(meilisearch_size)


def track_llm_guard_scan(scan_type: str, is_safe: bool, threat_level: Optional[str] = None) -> None:
    """Track LLM Guard security scan.
    
    Args:
        scan_type: Scan type ('input', 'output')
        is_safe: Whether the scan passed
        threat_level: Threat level if not safe ('low', 'medium', 'high', 'critical')
    """
    result = 'safe' if is_safe else 'unsafe'
    llm_guard_scans_total.labels(type=scan_type, result=result).inc()
    
    if not is_safe and threat_level:
        llm_guard_threats_total.labels(threat_level=threat_level).inc()


# =============================================================================
# Metrics Server
# =============================================================================

def start_metrics_server(port: int = 9091, registry: Optional[Any] = None) -> None:
    """Start Prometheus metrics HTTP server.
    
    This should be called once at application startup to expose metrics
    on the specified port for Prometheus scraping.
    
    Args:
        port: Port to expose metrics on (default: 9091)
        registry: Optional custom Prometheus registry (defaults to global REGISTRY)
        
    Note:
        Default port 9091 is chosen to avoid conflicts with Streamlit (8501)
        and other services. Configure Prometheus to scrape this port.
    """
    try:
        # If no registry specified, let start_http_server use the default REGISTRY
        if registry is None:
            start_http_server(port=port)
        else:
            start_http_server(port=port, registry=registry)
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Metrics available at: http://localhost:{port}/metrics")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(f"Metrics server already running on port {port}")
        else:
            logger.error(f"Failed to start metrics server: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}", exc_info=True)
