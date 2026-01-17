"""Unit tests for Qdrant vector database client."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.qdrant_client import QdrantVectorClient


@pytest.fixture
def qdrant_client():
    """Create a QdrantVectorClient instance for testing."""
    with patch("src.services.qdrant_client.get_config") as mock_config:
        mock_config.return_value.qdrant.host = "qdrant"
        mock_config.return_value.qdrant.port = 6333
        with patch("src.services.qdrant_client.QdrantClient"):
            return QdrantVectorClient(host="qdrant", port=6333)


class TestQdrantClientInitialization:
    """Test QdrantVectorClient initialization."""

    def test_init_with_custom_params(self):
        """Test initialization with custom host and port."""
        with patch("src.services.qdrant_client.get_config"):
            with patch("src.services.qdrant_client.QdrantClient"):
                client = QdrantVectorClient(host="custom_host", port=9999)
                assert client.host == "custom_host"
                assert client.port == 9999

    def test_init_uses_config_defaults(self):
        """Test initialization uses config defaults."""
        with patch("src.services.qdrant_client.get_config") as mock_config:
            mock_config.return_value.qdrant.host = "qdrant"
            mock_config.return_value.qdrant.port = 6333
            with patch("src.services.qdrant_client.QdrantClient"):
                client = QdrantVectorClient()
                assert client.host == "qdrant"
                assert client.port == 6333

    def test_init_client_creation_failure(self):
        """Test handling of client creation failure."""
        with patch("src.services.qdrant_client.get_config"):
            with patch("src.services.qdrant_client.QdrantClient") as mock_qdrant:
                mock_qdrant.side_effect = Exception("Connection failed")

                with pytest.raises(Exception):
                    QdrantVectorClient()


class TestQdrantClientHealthCheck:
    """Test Qdrant health check functionality."""

    def test_is_healthy_success(self, qdrant_client):
        """Test successful health check."""
        qdrant_client.client.get_collections.return_value = Mock()

        assert qdrant_client.is_healthy() is True

    def test_is_healthy_failure(self, qdrant_client):
        """Test failed health check."""
        qdrant_client.client.get_collections.side_effect = Exception("Connection error")

        assert qdrant_client.is_healthy() is False


class TestQdrantClientCreateCollection:
    """Test collection creation."""

    def test_create_collection_success(self, qdrant_client):
        """Test successful collection creation."""
        qdrant_client.client.create_collection.return_value = None

        result = qdrant_client.create_collection("test_collection", vector_size=768)

        assert result is True
        qdrant_client.client.create_collection.assert_called_once()

    def test_create_collection_with_force_recreate(self, qdrant_client):
        """Test collection creation with force recreate."""
        qdrant_client.client.delete_collection.return_value = None
        qdrant_client.client.create_collection.return_value = None

        result = qdrant_client.create_collection(
            "test_collection",
            vector_size=512,
            force_recreate=True,
        )

        assert result is True
        qdrant_client.client.delete_collection.assert_called_once_with("test_collection")
        qdrant_client.client.create_collection.assert_called_once()

    def test_create_collection_custom_vector_size(self, qdrant_client):
        """Test collection creation with custom vector size."""
        qdrant_client.client.create_collection.return_value = None

        qdrant_client.create_collection("test_col", vector_size=1024)

        # Verify vector size is passed correctly
        call_args = qdrant_client.client.create_collection.call_args
        assert call_args[1]["vectors_config"].size == 1024

    def test_create_collection_failure(self, qdrant_client):
        """Test collection creation failure."""
        qdrant_client.client.create_collection.side_effect = Exception("Creation failed")

        result = qdrant_client.create_collection("test_col")

        assert result is False

    def test_create_collection_already_exists(self, qdrant_client):
        """Test creation when collection already exists."""
        qdrant_client.client.create_collection.side_effect = Exception("Collection already exists")

        result = qdrant_client.create_collection("existing_col")

        assert result is False


class TestQdrantClientUpsertVectors:
    """Test vector upsertion."""

    def test_upsert_vectors_success(self, qdrant_client):
        """Test successful vector upsertion."""
        qdrant_client.client.upsert.return_value = None

        points = [
            {"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"text": "doc1"}},
            {"id": 2, "vector": [0.4, 0.5, 0.6], "payload": {"text": "doc2"}},
        ]

        result = qdrant_client.upsert_vectors("test_collection", points)

        assert result is True
        qdrant_client.client.upsert.assert_called_once()

    def test_upsert_vectors_empty_list(self, qdrant_client):
        """Test upsertion with empty point list."""
        qdrant_client.client.upsert.return_value = None

        result = qdrant_client.upsert_vectors("test_collection", [])

        assert result is True

    def test_upsert_vectors_no_payload(self, qdrant_client):
        """Test upsertion without payload."""
        qdrant_client.client.upsert.return_value = None

        points = [{"id": 1, "vector": [0.1, 0.2]}]

        result = qdrant_client.upsert_vectors("test_collection", points)

        assert result is True

    def test_upsert_vectors_failure(self, qdrant_client):
        """Test upsertion failure."""
        qdrant_client.client.upsert.side_effect = Exception("Upsert failed")

        points = [{"id": 1, "vector": [0.1], "payload": {}}]

        result = qdrant_client.upsert_vectors("test_collection", points)

        assert result is False

    def test_upsert_vectors_collection_not_found(self, qdrant_client):
        """Test upsertion to non-existent collection."""
        qdrant_client.client.upsert.side_effect = Exception("Collection not found")

        points = [{"id": 1, "vector": [0.1]}]

        result = qdrant_client.upsert_vectors("nonexistent", points)

        assert result is False


class TestQdrantClientSearch:
    """Test vector search."""

    def test_search_success(self, qdrant_client):
        """Test successful search."""
        mock_result1 = Mock(id=1, score=0.95, payload={"text": "doc1"})
        mock_result2 = Mock(id=2, score=0.85, payload={"text": "doc2"})
        qdrant_client.client.search.return_value = [mock_result1, mock_result2]

        results = qdrant_client.search(
            "test_collection",
            query_vector=[0.1, 0.2, 0.3],
            limit=5,
        )

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["score"] == 0.95
        assert results[1]["id"] == 2

    def test_search_empty_results(self, qdrant_client):
        """Test search with no results."""
        qdrant_client.client.search.return_value = []

        results = qdrant_client.search(
            "test_collection",
            query_vector=[0.1],
            limit=5,
        )

        assert results == []

    def test_search_with_score_threshold(self, qdrant_client):
        """Test search with score threshold."""
        mock_result = Mock(id=1, score=0.8, payload={})
        qdrant_client.client.search.return_value = [mock_result]

        qdrant_client.search(
            "test_collection",
            query_vector=[0.1],
            score_threshold=0.7,
        )

        # Verify threshold was passed
        call_args = qdrant_client.client.search.call_args
        assert call_args[1]["score_threshold"] == 0.7

    def test_search_custom_limit(self, qdrant_client):
        """Test search with custom limit."""
        qdrant_client.client.search.return_value = []

        qdrant_client.search(
            "test_collection",
            query_vector=[0.1],
            limit=100,
        )

        call_args = qdrant_client.client.search.call_args
        assert call_args[1]["limit"] == 100

    def test_search_failure(self, qdrant_client):
        """Test search failure."""
        qdrant_client.client.search.side_effect = Exception("Search failed")

        results = qdrant_client.search(
            "test_collection",
            query_vector=[0.1],
        )

        assert results == []

    def test_search_collection_not_found(self, qdrant_client):
        """Test search in non-existent collection."""
        qdrant_client.client.search.side_effect = Exception("Collection not found")

        results = qdrant_client.search(
            "nonexistent",
            query_vector=[0.1],
        )

        assert results == []


class TestQdrantClientDeleteCollection:
    """Test collection deletion."""

    def test_delete_collection_success(self, qdrant_client):
        """Test successful collection deletion."""
        qdrant_client.client.delete_collection.return_value = None

        result = qdrant_client.delete_collection("test_collection")

        assert result is True
        qdrant_client.client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_not_found(self, qdrant_client):
        """Test deleting non-existent collection."""
        qdrant_client.client.delete_collection.side_effect = Exception("Collection not found")

        result = qdrant_client.delete_collection("nonexistent")

        assert result is False

    def test_delete_collection_failure(self, qdrant_client):
        """Test deletion failure."""
        qdrant_client.client.delete_collection.side_effect = Exception("Delete failed")

        result = qdrant_client.delete_collection("test_collection")

        assert result is False


class TestQdrantClientGetCollectionInfo:
    """Test getting collection information."""

    def test_get_collection_info_success(self, qdrant_client):
        """Test successful retrieval of collection info."""
        mock_collection = Mock()
        mock_collection.points_count = 100
        mock_collection.vectors_count = 100
        qdrant_client.client.get_collection.return_value = mock_collection

        info = qdrant_client.get_collection_info("test_collection")

        assert info is not None
        assert info["points_count"] == 100

    def test_get_collection_info_not_found(self, qdrant_client):
        """Test getting info for non-existent collection."""
        qdrant_client.client.get_collection.side_effect = Exception("Collection not found")

        info = qdrant_client.get_collection_info("nonexistent")

        assert info is None

    def test_get_collection_info_failure(self, qdrant_client):
        """Test failure in getting info."""
        qdrant_client.client.get_collection.side_effect = Exception("Error")

        info = qdrant_client.get_collection_info("test_collection")

        assert info is None
