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


class TestQdrantClientListCollections:
    """Test list_collections method (Phase 4b Step 18)."""
    
    def test_list_collections_empty(self, qdrant_client):
        """Test listing collections when none exist."""
        mock_response = Mock()
        mock_response.collections = []
        qdrant_client.client.get_collections.return_value = mock_response
        
        collections = qdrant_client.list_collections()
        
        assert collections == []
    
    def test_list_collections_multiple(self, qdrant_client):
        """Test listing multiple collections."""
        # Mock collections response
        mock_coll1 = Mock()
        mock_coll1.name = "documents"
        mock_coll2 = Mock()
        mock_coll2.name = "images"
        
        mock_response = Mock()
        mock_response.collections = [mock_coll1, mock_coll2]
        qdrant_client.client.get_collections.return_value = mock_response
        
        # Mock individual collection details
        def mock_get_collection(name):
            mock_info = Mock()
            if name == "documents":
                mock_info.vectors_count = 1000
                mock_info.points_count = 1000
            elif name == "images":
                mock_info.vectors_count = 500
                mock_info.points_count = 500
            return mock_info
        
        qdrant_client.client.get_collection.side_effect = mock_get_collection
        
        collections = qdrant_client.list_collections()
        
        assert len(collections) == 2
        assert collections[0]["name"] == "documents"
        assert collections[0]["vectors_count"] == 1000
        assert collections[1]["name"] == "images"
        assert collections[1]["vectors_count"] == 500
    
    def test_list_collections_partial_failure(self, qdrant_client):
        """Test listing collections when some details fail."""
        mock_coll1 = Mock()
        mock_coll1.name = "working"
        mock_coll2 = Mock()
        mock_coll2.name = "broken"
        
        mock_response = Mock()
        mock_response.collections = [mock_coll1, mock_coll2]
        qdrant_client.client.get_collections.return_value = mock_response
        
        def mock_get_collection(name):
            if name == "working":
                mock_info = Mock()
                mock_info.vectors_count = 100
                mock_info.points_count = 100
                return mock_info
            else:
                raise Exception("Collection error")
        
        qdrant_client.client.get_collection.side_effect = mock_get_collection
        
        collections = qdrant_client.list_collections()
        
        assert len(collections) == 2
        assert collections[0]["vectors_count"] == 100
        assert collections[1]["vectors_count"] == 0  # Fallback for broken
    
    def test_list_collections_error(self, qdrant_client):
        """Test error handling in list_collections."""
        qdrant_client.client.get_collections.side_effect = Exception("Connection error")
        
        collections = qdrant_client.list_collections()
        
        assert collections == []


class TestQdrantClientGetCollectionStats:
    """Test get_collection_stats method (Phase 4b Step 18)."""
    
    def test_get_collection_stats_success(self, qdrant_client):
        """Test getting detailed collection statistics."""
        mock_collection = Mock()
        mock_collection.vectors_count = 8432
        mock_collection.points_count = 8432
        mock_collection.status = Mock()
        mock_collection.status.value = "green"
        
        # Mock vector config
        mock_vector_config = Mock()
        mock_vector_config.size = 768
        mock_vector_config.distance = Mock()
        mock_vector_config.distance.value = "Cosine"
        
        mock_config = Mock()
        mock_config.params = Mock()
        mock_config.params.vectors = mock_vector_config
        mock_collection.config = mock_config
        
        qdrant_client.client.get_collection.return_value = mock_collection
        
        stats = qdrant_client.get_collection_stats("documents")
        
        assert stats is not None
        assert stats["name"] == "documents"
        assert stats["vectors_count"] == 8432
        assert stats["vector_size"] == 768
        assert stats["distance_metric"] == "Cosine"
        assert stats["status"] == "green"
    
    def test_get_collection_stats_not_found(self, qdrant_client):
        """Test stats for non-existent collection."""
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        
        stats = qdrant_client.get_collection_stats("nonexistent")
        
        assert stats is None
    
    def test_get_collection_stats_dict_config(self, qdrant_client):
        """Test stats with dictionary vector config (multiple vectors)."""
        mock_collection = Mock()
        mock_collection.vectors_count = 100
        mock_collection.points_count = 100
        mock_collection.status = Mock()
        mock_collection.status.value = "green"
        
        # Mock dict-based vector config
        mock_vector_config_item = Mock()
        mock_vector_config_item.size = 512
        # distance should be a direct value, not nested Mock
        mock_vector_config_item.distance = "Euclid"
        
        mock_config = Mock()
        mock_config.params = Mock()
        mock_config.params.vectors = {"default": mock_vector_config_item}
        mock_collection.config = mock_config
        
        qdrant_client.client.get_collection.return_value = mock_collection
        
        stats = qdrant_client.get_collection_stats("test")
        
        assert stats is not None
        assert stats["vector_size"] == 512
        assert stats["distance_metric"] == "Euclid"


class TestQdrantClientSearchByText:
    """Test search_by_text method (Phase 4b Step 18)."""
    
    def test_search_by_text_empty_query_raises_error(self, qdrant_client):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            qdrant_client.search_by_text("", "documents", top_k=5)
    
    def test_search_by_text_success(self, qdrant_client):
        """Test successful text search."""
        # Mock Ollama client
        mock_ollama = Mock()
        mock_ollama.embed.return_value = [0.1] * 768
        
        # Mock search results
        qdrant_client.search = Mock(return_value=[
            {
                "id": "doc_1",
                "score": 0.92,
                "payload": {
                    "content": "Test content",
                    "source": "test.pdf",
                    "chunk_index": 0,
                }
            }
        ])
        
        results = qdrant_client.search_by_text(
            query="test query",
            collection="documents",
            top_k=5,
            ollama_client=mock_ollama,
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "doc_1"
        assert results[0]["score"] == 0.92
        assert results[0]["content"] == "Test content"
        assert results[0]["source"] == "test.pdf"
        mock_ollama.embed.assert_called_once_with("test query")
    
    def test_search_by_text_no_embedding(self, qdrant_client):
        """Test search when embedding generation fails."""
        mock_ollama = Mock()
        mock_ollama.embed.return_value = None
        
        results = qdrant_client.search_by_text(
            query="test",
            collection="documents",
            top_k=5,
            ollama_client=mock_ollama,
        )
        
        assert results == []
    
    def test_search_by_text_without_ollama_client(self, qdrant_client):
        """Test search creates Ollama client if not provided."""
        with patch("src.services.ollama_client.OllamaClient") as mock_ollama_class:
            mock_ollama = Mock()
            mock_ollama.embed.return_value = [0.1] * 768
            mock_ollama_class.return_value = mock_ollama
            
            qdrant_client.search = Mock(return_value=[])
            
            results = qdrant_client.search_by_text(
                query="test",
                collection="documents",
                top_k=5,
            )
            
            mock_ollama_class.assert_called_once()
            mock_ollama.embed.assert_called_once()
    
    def test_search_by_text_error_handling(self, qdrant_client):
        """Test error handling in text search."""
        mock_ollama = Mock()
        mock_ollama.embed.side_effect = Exception("Embedding failed")
        
        results = qdrant_client.search_by_text(
            query="test",
            collection="documents",
            top_k=5,
            ollama_client=mock_ollama,
        )
        
        assert results == []


class TestQdrantClientCreateCollectionUI:
    """Test create_collection_ui method (Phase 4b Step 18)."""
    
    def test_create_collection_ui_success(self, qdrant_client):
        """Test successful collection creation from UI."""
        # Mock collection doesn't exist
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        qdrant_client.client.create_collection = Mock()
        
        success, message = qdrant_client.create_collection_ui(
            name="test_collection",
            vector_size=768,
            distance="Cosine",
        )
        
        assert success is True
        assert "created successfully" in message
        qdrant_client.client.create_collection.assert_called_once()
    
    def test_create_collection_ui_empty_name(self, qdrant_client):
        """Test validation of empty collection name."""
        success, message = qdrant_client.create_collection_ui(
            name="",
            vector_size=768,
            distance="Cosine",
        )
        
        assert success is False
        assert "cannot be empty" in message
    
    def test_create_collection_ui_invalid_name(self, qdrant_client):
        """Test validation of invalid collection name."""
        success, message = qdrant_client.create_collection_ui(
            name="test@collection!",
            vector_size=768,
            distance="Cosine",
        )
        
        assert success is False
        assert "letters, numbers, underscore, and hyphen" in message
    
    def test_create_collection_ui_invalid_vector_size(self, qdrant_client):
        """Test validation of invalid vector size."""
        success, message = qdrant_client.create_collection_ui(
            name="test",
            vector_size=3000,  # Too large
            distance="Cosine",
        )
        
        assert success is False
        assert "between 1 and 2048" in message
    
    def test_create_collection_ui_invalid_distance(self, qdrant_client):
        """Test validation of invalid distance metric."""
        success, message = qdrant_client.create_collection_ui(
            name="test",
            vector_size=768,
            distance="Invalid",
        )
        
        assert success is False
        assert "must be one of" in message
    
    def test_create_collection_ui_already_exists(self, qdrant_client):
        """Test creating collection that already exists."""
        # Mock collection exists
        qdrant_client.client.get_collection.return_value = Mock()
        
        success, message = qdrant_client.create_collection_ui(
            name="existing",
            vector_size=768,
            distance="Cosine",
        )
        
        assert success is False
        assert "already exists" in message


class TestQdrantClientDeleteCollectionUI:
    """Test delete_collection_ui method (Phase 4b Step 18)."""
    
    def test_delete_collection_ui_success(self, qdrant_client):
        """Test successful collection deletion from UI."""
        # Mock collection exists
        qdrant_client.client.get_collection.return_value = Mock()
        qdrant_client.delete_collection = Mock(return_value=True)
        
        success, message = qdrant_client.delete_collection_ui("test_collection")
        
        assert success is True
        assert "deleted successfully" in message
        qdrant_client.delete_collection.assert_called_once_with("test_collection")
    
    def test_delete_collection_ui_empty_name(self, qdrant_client):
        """Test deletion with empty name."""
        success, message = qdrant_client.delete_collection_ui("")
        
        assert success is False
        assert "cannot be empty" in message
    
    def test_delete_collection_ui_not_found(self, qdrant_client):
        """Test deletion of non-existent collection."""
        qdrant_client.client.get_collection.side_effect = Exception("Not found")
        
        success, message = qdrant_client.delete_collection_ui("nonexistent")
        
        assert success is False
        assert "does not exist" in message
    
    def test_delete_collection_ui_delete_failed(self, qdrant_client):
        """Test when deletion operation fails."""
        qdrant_client.client.get_collection.return_value = Mock()
        qdrant_client.delete_collection = Mock(return_value=False)
        
        success, message = qdrant_client.delete_collection_ui("test")
        
        assert success is False
        assert "Failed to delete" in message

