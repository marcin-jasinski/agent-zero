"""Shared test fixtures and mocks for Agent Zero test suite.

This module provides:
- Mock service clients (Ollama, Qdrant, Meilisearch, Langfuse)
- Mock LLM Guard scanners
- Shared fixtures for common test scenarios
- Configuration mocks for different environments

Usage:
    fixtures are automatically available to all tests via pytest's
    fixture discovery mechanism.
"""

import sys
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


# Install llm-guard mocks BEFORE any test imports
def create_scanner_class(name):
    """Create a mock scanner class."""
    scanner_class = Mock()
    scanner_instance = Mock()
    scanner_instance.scan = Mock(return_value=("sanitized", True, 0.0))
    scanner_instance.__class__.__name__ = name
    scanner_class.return_value = scanner_instance
    return scanner_class


# Mock llm_guard module structure
mock_llm_guard = MagicMock()

# Mock input scanners
mock_input_scanners = MagicMock()
mock_input_scanners.PromptInjection = create_scanner_class("PromptInjection")
mock_input_scanners.Toxicity = create_scanner_class("Toxicity")
mock_input_scanners.TokenLimit = create_scanner_class("TokenLimit")
mock_input_scanners.Anonymize = create_scanner_class("Anonymize")

# Mock output scanners
mock_output_scanners = MagicMock()
mock_output_scanners.Bias = create_scanner_class("Bias")
mock_output_scanners.Deanonymize = create_scanner_class("Deanonymize")
mock_output_scanners.MaliciousURLs = create_scanner_class("MaliciousURLs")
mock_output_scanners.NoRefusal = create_scanner_class("NoRefusal")
mock_output_scanners.Relevance = create_scanner_class("Relevance")
mock_output_scanners.Sensitive = create_scanner_class("Sensitive")

# Mock vault
mock_vault_module = MagicMock()
mock_vault_module.Vault = Mock(return_value=Mock())

# Install mocks in sys.modules BEFORE any imports
sys.modules['llm_guard'] = mock_llm_guard
sys.modules['llm_guard.input_scanners'] = mock_input_scanners
sys.modules['llm_guard.output_scanners'] = mock_output_scanners
sys.modules['llm_guard.vault'] = mock_vault_module


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock application configuration."""
    config = Mock()
    config.app_name = "Agent Zero"
    config.app_version = "0.1.0"
    config.env = "development"
    config.debug = False
    config.host = "0.0.0.0"
    config.port = 8501
    config.log_level = "INFO"
    
    # Ollama config
    config.ollama = Mock()
    config.ollama.host = "http://localhost:11434"
    config.ollama.model = "ministral-3:3b"
    config.ollama.embed_model = "nomic-embed-text-v2-moe"
    config.ollama.timeout = 300
    
    # Qdrant config
    config.qdrant = Mock()
    config.qdrant.host = "localhost"
    config.qdrant.port = 6333
    config.qdrant.collection_name = "documents"
    config.qdrant.vector_size = 768
    
    # Meilisearch config
    config.meilisearch = Mock()
    config.meilisearch.host = "http://localhost:7700"
    config.meilisearch.index_name = "documents"
    
    # Langfuse config
    config.langfuse = Mock()
    config.langfuse.host = "http://localhost:3000"
    config.langfuse.enabled = True
    config.langfuse.public_key = ""
    config.langfuse.secret_key = ""
    config.langfuse.timeout = 30
    
    # Security config
    config.security = Mock()
    config.security.llm_guard_enabled = False
    
    # Dashboard features
    config.dashboard = Mock()
    config.dashboard.show_chat = True
    config.dashboard.show_knowledge_base = True
    config.dashboard.show_settings = True
    config.dashboard.show_logs = True
    config.dashboard.show_qdrant_manager = False
    config.dashboard.show_langfuse_dashboard = False
    config.dashboard.show_system_health = False
    
    return config


@pytest.fixture
def mock_production_config(mock_config):
    """Create a mock production configuration."""
    mock_config.env = "production"
    mock_config.debug = False
    mock_config.langfuse.enabled = True
    mock_config.security.llm_guard_enabled = True
    return mock_config


# ============================================================================
# Service Client Fixtures
# ============================================================================

@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = Mock()
    client.is_healthy.return_value = True
    client.list_models.return_value = ["ministral-3:3b", "nomic-embed-text-v2-moe"]
    client.generate_embeddings.return_value = [0.1] * 768  # 768-dim vector
    client.chat.return_value = {
        "message": {"content": "This is a test response."},
        "model": "ministral-3:3b",
    }
    return client


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = Mock()
    client.is_healthy.return_value = True
    client.list_collections.return_value = [
        {"name": "documents", "vector_count": 100, "vector_size": 768}
    ]
    client.search.return_value = [
        {"id": "1", "score": 0.95, "payload": {"content": "Test document"}},
        {"id": "2", "score": 0.85, "payload": {"content": "Another document"}},
    ]
    client.upsert_vectors.return_value = True
    return client


@pytest.fixture
def mock_meilisearch_client():
    """Create a mock Meilisearch client."""
    client = Mock()
    client.is_healthy.return_value = True
    client.list_indexes.return_value = ["documents"]
    client.search.return_value = {
        "hits": [
            {"id": "1", "content": "Test document"},
            {"id": "2", "content": "Another document"},
        ],
        "query": "test",
        "processingTimeMs": 5,
    }
    return client


@pytest.fixture
def mock_langfuse_client():
    """Create a mock Langfuse client."""
    client = Mock()
    client.enabled = True
    client.is_healthy.return_value = True
    client.get_trace_summary.return_value = Mock(
        total_traces=100,
        traces_24h=50,
        avg_latency_ms=1500.0,
        error_rate=2.5,
        time_range="24h"
    )
    client.get_recent_traces.return_value = [
        Mock(
            trace_id="trace-1",
            name="Chat Query",
            timestamp=datetime.now(),
            duration_ms=2100,
            status="success",
            input_tokens=245,
            output_tokens=89,
        )
    ]
    return client


# ============================================================================
# Health Check Fixtures
# ============================================================================

@pytest.fixture
def mock_health_checker(mock_ollama_client, mock_qdrant_client, mock_meilisearch_client):
    """Create a mock health checker with healthy services."""
    checker = Mock()
    
    ollama_status = Mock()
    ollama_status.name = "Ollama"
    ollama_status.is_healthy = True
    ollama_status.message = "LLM service operational"
    ollama_status.details = {"models": 2}
    
    qdrant_status = Mock()
    qdrant_status.name = "Qdrant"
    qdrant_status.is_healthy = True
    qdrant_status.message = "Vector DB operational"
    qdrant_status.details = {}
    
    meilisearch_status = Mock()
    meilisearch_status.name = "Meilisearch"
    meilisearch_status.is_healthy = True
    meilisearch_status.message = "Search engine operational"
    meilisearch_status.details = {}
    
    langfuse_status = Mock()
    langfuse_status.name = "Langfuse"
    langfuse_status.is_healthy = True
    langfuse_status.message = "Observability operational"
    langfuse_status.details = {"enabled": True}
    
    checker.check_all.return_value = {
        "ollama": ollama_status,
        "qdrant": qdrant_status,
        "meilisearch": meilisearch_status,
        "langfuse": langfuse_status,
    }
    checker.all_healthy = True
    
    return checker


@pytest.fixture
def mock_unhealthy_checker():
    """Create a mock health checker with some unhealthy services."""
    checker = Mock()
    
    ollama_status = Mock()
    ollama_status.name = "Ollama"
    ollama_status.is_healthy = False
    ollama_status.message = "Connection refused"
    ollama_status.details = {}
    
    qdrant_status = Mock()
    qdrant_status.name = "Qdrant"
    qdrant_status.is_healthy = True
    qdrant_status.message = "Vector DB operational"
    qdrant_status.details = {}
    
    checker.check_all.return_value = {
        "ollama": ollama_status,
        "qdrant": qdrant_status,
    }
    checker.all_healthy = False
    
    return checker


# ============================================================================
# Document/RAG Fixtures
# ============================================================================

@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return {
        "id": "doc-1",
        "content": "This is a sample document for testing the RAG pipeline.",
        "source": "test.pdf",
        "metadata": {
            "title": "Test Document",
            "author": "Test Author",
            "created_at": datetime.now().isoformat(),
        },
    }


@pytest.fixture
def sample_chunks():
    """Create sample document chunks for testing."""
    return [
        {
            "id": "chunk-1",
            "content": "This is the first chunk of the document.",
            "source": "test.pdf",
            "chunk_index": 0,
            "metadata": {"page": 1},
        },
        {
            "id": "chunk-2",
            "content": "This is the second chunk of the document.",
            "source": "test.pdf",
            "chunk_index": 1,
            "metadata": {"page": 1},
        },
    ]


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    return [
        [0.1, 0.2, 0.3] + [0.0] * 765,  # 768-dim vector
        [0.4, 0.5, 0.6] + [0.0] * 765,
    ]


# ============================================================================
# Streamlit Mocking
# ============================================================================

@pytest.fixture
def mock_streamlit():
    """Create a mock Streamlit module."""
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.cache_data = lambda ttl=None: lambda f: f  # Pass-through decorator
    return mock_st


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Docker services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security-related"
    )
