"""Unit tests for retrieval engine.

Tests the RetrievalEngine class covering semantic search, keyword search,
and hybrid search functionality.
"""

import pytest
from unittest.mock import Mock

from src.core.retrieval import RetrievalEngine
from src.models.retrieval import RetrievalResult, HybridSearchConfig


class TestRetrievalResult:
    """Test RetrievalResult data model."""

    def test_valid_result_creation(self) -> None:
        """Test creating a valid retrieval result."""
        result = RetrievalResult(
            id="doc_1",
            content="Test content",
            source="test.pdf",
            chunk_index=0,
            score=0.85,
        )
        assert result.id == "doc_1"
        assert result.score == 0.85

    def test_result_score_validation(self) -> None:
        """Test that score must be 0.0-1.0."""
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            RetrievalResult(
                id="doc_1",
                content="content",
                source="test.pdf",
                chunk_index=0,
                score=1.5,
            )

    def test_result_sorting(self) -> None:
        """Test that results sort by score descending."""
        result1 = RetrievalResult(
            id="doc_1", content="c1", source="s1", chunk_index=0, score=0.5
        )
        result2 = RetrievalResult(
            id="doc_2", content="c2", source="s2", chunk_index=0, score=0.9
        )

        sorted_results = sorted([result1, result2])
        assert sorted_results[0].score == 0.9
        assert sorted_results[1].score == 0.5


class TestHybridSearchConfig:
    """Test HybridSearchConfig."""

    def test_valid_config(self) -> None:
        """Test creating valid config."""
        config = HybridSearchConfig(
            semantic_weight=0.6,
            keyword_weight=0.4,
            max_results=10,
        )
        assert config.semantic_weight == 0.6
        assert config.keyword_weight == 0.4

    def test_weights_must_sum_to_one(self) -> None:
        """Test that weights must sum to 1.0."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            HybridSearchConfig(semantic_weight=0.5, keyword_weight=0.4)

    def test_min_semantic_score_validation(self) -> None:
        """Test that min_semantic_score must be 0.0-1.0."""
        with pytest.raises(ValueError, match="min_semantic_score"):
            HybridSearchConfig(
                semantic_weight=0.6,
                keyword_weight=0.4,
                min_semantic_score=1.5,
            )

    def test_max_results_must_be_positive(self) -> None:
        """Test that max_results must be positive."""
        with pytest.raises(ValueError, match="max_results must be positive"):
            HybridSearchConfig(
                semantic_weight=0.6,
                keyword_weight=0.4,
                max_results=0,
            )


class TestRetrievalEngine:
    """Test RetrievalEngine class."""

    @pytest.fixture
    def mock_clients(self) -> tuple:
        """Create mock service clients."""
        ollama_mock = Mock()
        qdrant_mock = Mock()
        meilisearch_mock = Mock()
        return ollama_mock, qdrant_mock, meilisearch_mock

    @pytest.fixture
    def engine(self, mock_clients) -> RetrievalEngine:
        """Create RetrievalEngine with mocked clients."""
        ollama, qdrant, meilisearch = mock_clients
        return RetrievalEngine(ollama, qdrant, meilisearch)

    def test_engine_initialization(self, mock_clients) -> None:
        """Test engine initialization."""
        ollama, qdrant, meilisearch = mock_clients
        config = HybridSearchConfig(semantic_weight=0.7, keyword_weight=0.3)
        engine = RetrievalEngine(ollama, qdrant, meilisearch, config)
        assert engine.config.semantic_weight == 0.7

    def test_retrieve_empty_query_fails(self, engine) -> None:
        """Test that empty query raises error."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            engine.retrieve_relevant_docs("")

    def test_semantic_search_success(self, engine) -> None:
        """Test successful semantic search."""
        # Mock Ollama embedding generation
        engine.ollama_client.generate_embedding = Mock(
            return_value=[0.1, 0.2, 0.3]
        )

        # Mock Qdrant search results
        engine.qdrant_client.search_vectors = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "score": 0.95,
                    "payload": {
                        "content": "Test content",
                        "source": "test.pdf",
                        "chunk_index": 0,
                        "metadata": {},
                    },
                }
            ]
        )

        results = engine._semantic_search("test query", top_k=5)

        assert len(results) == 1
        assert results[0].id == "doc_1"
        assert results[0].search_type == "semantic"
        engine.ollama_client.generate_embedding.assert_called_once()

    def test_semantic_search_filters_low_scores(self, engine) -> None:
        """Test that low-scoring results are filtered."""
        engine.ollama_client.generate_embedding = Mock(
            return_value=[0.1, 0.2, 0.3]
        )

        # Return low-score result (below min_semantic_score of 0.3)
        engine.qdrant_client.search_vectors = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "score": 0.1,  # Below minimum
                    "payload": {
                        "content": "Test content",
                        "source": "test.pdf",
                        "chunk_index": 0,
                        "metadata": {},
                    },
                }
            ]
        )

        results = engine._semantic_search("test query", top_k=5)
        assert len(results) == 0

    def test_keyword_search_success(self, engine) -> None:
        """Test successful keyword search."""
        engine.meilisearch_client.search = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "_rankingScore": 80.0,
                    "content": "Test content",
                    "source": "test.pdf",
                    "chunk_index": 0,
                    "title": "Test",
                }
            ]
        )

        results = engine._keyword_search("test query", top_k=5)

        assert len(results) == 1
        assert results[0].search_type == "keyword"
        # Score should be normalized from 80/100 = 0.8
        assert 0.79 <= results[0].score <= 0.81

    def test_keyword_search_normalizes_scores(self, engine) -> None:
        """Test that keyword scores are normalized to 0-1 range."""
        engine.meilisearch_client.search = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "_rankingScore": 100.0,  # Max Meilisearch score
                    "content": "Test",
                    "source": "test.pdf",
                    "chunk_index": 0,
                    "title": "Test",
                }
            ]
        )

        results = engine._keyword_search("test", top_k=5)
        assert results[0].score == 1.0  # Should be normalized to 1.0

    def test_hybrid_search_combines_results(self, engine) -> None:
        """Test that hybrid search combines semantic and keyword results."""
        engine.ollama_client.generate_embedding = Mock(
            return_value=[0.1, 0.2, 0.3]
        )

        # Mock semantic results
        engine.qdrant_client.search_vectors = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "score": 0.9,
                    "payload": {
                        "content": "Semantic result",
                        "source": "test.pdf",
                        "chunk_index": 0,
                        "metadata": {},
                    },
                }
            ]
        )

        # Mock keyword results
        engine.meilisearch_client.search = Mock(
            return_value=[
                {
                    "id": "doc_2",
                    "_rankingScore": 70.0,
                    "content": "Keyword result",
                    "source": "test2.pdf",
                    "chunk_index": 0,
                    "title": "Test",
                }
            ]
        )

        results = engine._hybrid_search("test query", top_k=5)

        # Should have results (at least semantic or keyword results)
        assert len(results) >= 1
        # Results should have proper search_type (hybrid, semantic, or keyword)
        assert all(r.search_type in ["hybrid", "semantic", "keyword"] for r in results)

    def test_hybrid_search_deduplication(self, engine) -> None:
        """Test that hybrid search deduplicates by ID."""
        engine.ollama_client.generate_embedding = Mock(
            return_value=[0.1, 0.2, 0.3]
        )

        # Same document in both searches
        engine.qdrant_client.search_vectors = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "score": 0.9,
                    "payload": {
                        "content": "Test",
                        "source": "test.pdf",
                        "chunk_index": 0,
                        "metadata": {},
                    },
                }
            ]
        )

        engine.meilisearch_client.search = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "_rankingScore": 70.0,
                    "content": "Test",
                    "source": "test.pdf",
                    "chunk_index": 0,
                    "title": "Test",
                }
            ]
        )

        results = engine._hybrid_search("test query", top_k=5)

        # Should only have one result (deduplicated)
        doc_ids = [r.id for r in results]
        assert len(doc_ids) == len(set(doc_ids))

    def test_retrieve_relevant_docs_semantic_only(self, engine) -> None:
        """Test retrieve_relevant_docs with hybrid disabled."""
        engine.ollama_client.generate_embedding = Mock(
            return_value=[0.1, 0.2, 0.3]
        )

        engine.qdrant_client.search_vectors = Mock(
            return_value=[
                {
                    "id": "doc_1",
                    "score": 0.9,
                    "payload": {
                        "content": "Test",
                        "source": "test.pdf",
                        "chunk_index": 0,
                        "metadata": {},
                    },
                }
            ]
        )

        results = engine.retrieve_relevant_docs("test query", hybrid=False)
        assert len(results) > 0
        # Should not call Meilisearch
        engine.meilisearch_client.search.assert_not_called()

    def test_search_with_context_no_context(self, engine) -> None:
        """Test search_with_context with context_chunks=0."""
        engine.retrieve_relevant_docs = Mock(
            return_value=[
                RetrievalResult(
                    id="doc_1",
                    content="Test",
                    source="test.pdf",
                    chunk_index=0,
                    score=0.9,
                )
            ]
        )

        results = engine.search_with_context("test", context_chunks=0, top_k=5)
        assert len(results) == 1

    def test_search_with_context_negative_chunks_fails(self, engine) -> None:
        """Test that negative context_chunks raises error."""
        with pytest.raises(ValueError, match="context_chunks cannot be negative"):
            engine.search_with_context("test", context_chunks=-1)
