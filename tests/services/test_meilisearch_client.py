"""Unit tests for Meilisearch client."""

import pytest
from unittest.mock import Mock, patch

from src.services.meilisearch_client import MeilisearchClient


@pytest.fixture
def meilisearch_client():
    """Create a MeilisearchClient instance for testing."""
    with patch("src.services.meilisearch_client.get_config") as mock_config:
        mock_config.return_value.meilisearch.host = "meilisearch"
        mock_config.return_value.meilisearch.port = 7700
        mock_config.return_value.meilisearch.api_key = "test-key"
        with patch("src.services.meilisearch_client.meilisearch.Client"):
            return MeilisearchClient(
                host="meilisearch",
                port=7700,
                api_key="test-key",
            )


class TestMeilisearchClientInitialization:
    """Test MeilisearchClient initialization."""

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        with patch("src.services.meilisearch_client.get_config"):
            with patch("src.services.meilisearch_client.meilisearch.Client"):
                client = MeilisearchClient(
                    host="custom",
                    port=8000,
                    api_key="key",
                )
                assert client.host == "custom"
                assert client.port == 8000
                assert client.url == "http://custom:8000"

    def test_init_client_creation_failure(self):
        """Test handling of client creation failure."""
        with patch("src.services.meilisearch_client.get_config"):
            with patch("src.services.meilisearch_client.meilisearch.Client") as mock_client:
                mock_client.side_effect = Exception("Connection failed")

                with pytest.raises(Exception):
                    MeilisearchClient()


class TestMeilisearchClientHealthCheck:
    """Test Meilisearch health check."""

    def test_is_healthy_success(self, meilisearch_client):
        """Test successful health check."""
        meilisearch_client.client.health.return_value = {"status": "available"}

        assert meilisearch_client.is_healthy() is True

    def test_is_healthy_unavailable(self, meilisearch_client):
        """Test health check when unavailable."""
        meilisearch_client.client.health.return_value = {"status": "unavailable"}

        assert meilisearch_client.is_healthy() is False

    def test_is_healthy_error(self, meilisearch_client):
        """Test health check with error."""
        meilisearch_client.client.health.side_effect = Exception("Error")

        assert meilisearch_client.is_healthy() is False


class TestMeilisearchClientCreateIndex:
    """Test index creation."""

    def test_create_index_success(self, meilisearch_client):
        """Test successful index creation."""
        meilisearch_client.client.create_index.return_value = Mock()

        result = meilisearch_client.create_index("test_index")

        assert result is True
        meilisearch_client.client.create_index.assert_called_once()

    def test_create_index_custom_primary_key(self, meilisearch_client):
        """Test index creation with custom primary key."""
        meilisearch_client.client.create_index.return_value = Mock()

        meilisearch_client.create_index("test_index", primary_key="doc_id")

        call_args = meilisearch_client.client.create_index.call_args
        assert call_args[0][0] == "test_index"
        assert call_args[0][1]["primaryKey"] == "doc_id"

    def test_create_index_failure(self, meilisearch_client):
        """Test index creation failure."""
        meilisearch_client.client.create_index.side_effect = Exception("Creation failed")

        result = meilisearch_client.create_index("test_index")

        assert result is False


class TestMeilisearchClientAddDocuments:
    """Test adding documents to index."""

    def test_add_documents_success(self, meilisearch_client):
        """Test successful document addition."""
        mock_index = Mock()
        meilisearch_client.client.index.return_value = mock_index

        documents = [
            {"id": 1, "title": "Doc 1", "content": "Content 1"},
            {"id": 2, "title": "Doc 2", "content": "Content 2"},
        ]

        result = meilisearch_client.add_documents("test_index", documents)

        assert result is True
        mock_index.add_documents.assert_called_once()

    def test_add_documents_empty_list(self, meilisearch_client):
        """Test adding empty document list."""
        mock_index = Mock()
        meilisearch_client.client.index.return_value = mock_index

        result = meilisearch_client.add_documents("test_index", [])

        assert result is True

    def test_add_documents_custom_primary_key(self, meilisearch_client):
        """Test adding documents with custom primary key."""
        mock_index = Mock()
        meilisearch_client.client.index.return_value = mock_index

        documents = [{"doc_id": "a", "text": "Content"}]

        meilisearch_client.add_documents(
            "test_index",
            documents,
            primary_key="doc_id",
        )

        call_args = mock_index.add_documents.call_args
        assert call_args[1]["primary_key"] == "doc_id"

    def test_add_documents_failure(self, meilisearch_client):
        """Test document addition failure."""
        mock_index = Mock()
        mock_index.add_documents.side_effect = Exception("Add failed")
        meilisearch_client.client.index.return_value = mock_index

        documents = [{"id": 1, "text": "Doc"}]

        result = meilisearch_client.add_documents("test_index", documents)

        assert result is False

    def test_add_documents_index_not_found(self, meilisearch_client):
        """Test adding to non-existent index."""
        meilisearch_client.client.index.side_effect = Exception("Index not found")

        documents = [{"id": 1}]

        result = meilisearch_client.add_documents("nonexistent", documents)

        assert result is False


class TestMeilisearchClientSearch:
    """Test searching."""

    def test_search_success(self, meilisearch_client):
        """Test successful search."""
        mock_index = Mock()
        mock_index.search.return_value = {
            "hits": [
                {"id": 1, "title": "Result 1"},
                {"id": 2, "title": "Result 2"},
            ]
        }
        meilisearch_client.client.index.return_value = mock_index

        results = meilisearch_client.search("test_index", "query")

        assert len(results) == 2
        assert results[0]["id"] == 1

    def test_search_empty_results(self, meilisearch_client):
        """Test search with no results."""
        mock_index = Mock()
        mock_index.search.return_value = {"hits": []}
        meilisearch_client.client.index.return_value = mock_index

        results = meilisearch_client.search("test_index", "nonexistent")

        assert results == []

    def test_search_custom_limit(self, meilisearch_client):
        """Test search with custom limit."""
        mock_index = Mock()
        mock_index.search.return_value = {"hits": []}
        meilisearch_client.client.index.return_value = mock_index

        meilisearch_client.search("test_index", "query", limit=20)

        call_args = mock_index.search.call_args
        assert call_args[0][1]["limit"] == 20

    def test_search_failure(self, meilisearch_client):
        """Test search failure."""
        mock_index = Mock()
        mock_index.search.side_effect = Exception("Search error")
        meilisearch_client.client.index.return_value = mock_index

        results = meilisearch_client.search("test_index", "query")

        assert results == []


class TestMeilisearchClientDeleteIndex:
    """Test index deletion."""

    def test_delete_index_success(self, meilisearch_client):
        """Test successful index deletion."""
        meilisearch_client.client.delete_index.return_value = None

        result = meilisearch_client.delete_index("test_index")

        assert result is True

    def test_delete_index_not_found(self, meilisearch_client):
        """Test deleting non-existent index."""
        meilisearch_client.client.delete_index.side_effect = Exception("Index not found")

        result = meilisearch_client.delete_index("nonexistent")

        assert result is False


class TestMeilisearchClientGetIndexStats:
    """Test getting index statistics."""

    def test_get_index_stats_success(self, meilisearch_client):
        """Test successful stats retrieval."""
        mock_index = Mock()
        mock_index.get_stats.return_value = {
            "numberOfDocuments": 100,
            "isIndexing": False,
        }
        meilisearch_client.client.index.return_value = mock_index

        stats = meilisearch_client.get_index_stats("test_index")

        assert stats["documents_count"] == 100
        assert stats["is_indexing"] is False

    def test_get_index_stats_success_object_response(self, meilisearch_client):
        """Test stats retrieval when SDK returns object with snake_case attrs."""
        mock_index = Mock()
        mock_stats = Mock(number_of_documents=50, is_indexing=True)
        mock_index.get_stats.return_value = mock_stats
        meilisearch_client.client.index.return_value = mock_index

        stats = meilisearch_client.get_index_stats("test_index")

        assert stats["documents_count"] == 50
        assert stats["is_indexing"] is True

    def test_get_index_stats_not_found(self, meilisearch_client):
        """Test stats for non-existent index."""
        meilisearch_client.client.index.side_effect = Exception("Index not found")

        stats = meilisearch_client.get_index_stats("nonexistent")

        assert stats is None

    def test_get_index_stats_error(self, meilisearch_client):
        """Test error in stats retrieval."""
        mock_index = Mock()
        mock_index.get_stats.side_effect = Exception("Error")
        meilisearch_client.client.index.return_value = mock_index

        stats = meilisearch_client.get_index_stats("test_index")

        assert stats is None


class TestMeilisearchClientListIndexes:
    """Test listing indexes."""

    def test_list_indexes_success(self, meilisearch_client):
        """Test successful index listing."""
        meilisearch_client.client.get_indexes.return_value = {
            "results": [
                {"uid": "index1"},
                {"uid": "index2"},
            ]
        }

        indexes = meilisearch_client.list_indexes()

        assert len(indexes) == 2
        assert "index1" in indexes
        assert "index2" in indexes

    def test_list_indexes_success_object_results(self, meilisearch_client):
        """Test successful index listing when SDK returns objects."""
        idx1 = Mock(uid="index1")
        idx2 = Mock(uid="index2")
        meilisearch_client.client.get_indexes.return_value = {"results": [idx1, idx2]}

        indexes = meilisearch_client.list_indexes()

        assert indexes == ["index1", "index2"]

    def test_list_indexes_empty(self, meilisearch_client):
        """Test listing when no indexes exist."""
        meilisearch_client.client.get_indexes.return_value = {"results": []}

        indexes = meilisearch_client.list_indexes()

        assert indexes == []

    def test_list_indexes_error(self, meilisearch_client):
        """Test error during listing."""
        meilisearch_client.client.get_indexes.side_effect = Exception("Error")

        indexes = meilisearch_client.list_indexes()

        assert indexes == []
