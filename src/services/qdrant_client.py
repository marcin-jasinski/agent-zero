"""Qdrant Vector Database Client.

Handles semantic search and vector storage operations.
Phase 4b Step 18: Enhanced with dashboard management capabilities.
"""

import logging
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.config import get_config

logger = logging.getLogger(__name__)


class QdrantVectorClient:
    """Client for Qdrant vector database."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """Initialize Qdrant client.

        Args:
            host: Qdrant host (default: from config)
            port: Qdrant port (default: from config)
        """
        config = get_config()
        self.host = host or config.qdrant.host
        self.port = port or config.qdrant.port

        try:
            self.client = QdrantClient(host=self.host, port=self.port, timeout=30.0)
            logger.info(f"Qdrant client initialized: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    def is_healthy(self) -> bool:
        """Check if Qdrant service is healthy.

        Returns:
            True if service is responding, False otherwise
        """
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False

    def has_documents(self, collection_name: str) -> bool:
        """Return True if the collection exists and contains at least one vector.

        This is a cheap O(1) metadata call — no embedding generation is needed.
        Use this as a guard before running any retrieval to avoid wasting GPU
        time generating embeddings against an empty knowledge base.

        Args:
            collection_name: Name of the collection to check.

        Returns:
            True if the collection has ≥1 points, False otherwise.
        """
        try:
            info = self.client.get_collection(collection_name)
            count = info.points_count or 0
            return count > 0
        except Exception:
            # Collection does not exist or Qdrant is unreachable — treat as empty.
            return False

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 768,
        force_recreate: bool = False,
    ) -> bool:
        """Create a vector collection.

        Args:
            collection_name: Name of the collection
            vector_size: Size of vectors in this collection
            force_recreate: Delete and recreate if exists

        Returns:
            True if successful

        Raises:
            ValueError: If vector_size is invalid
        """
        # Validate inputs
        if not (0 < vector_size <= 2048):
            raise ValueError(f"vector_size must be between 1 and 2048, got {vector_size}")
        
        try:
            if force_recreate:
                self.client.delete_collection(collection_name)

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

            logger.info(f"Collection '{collection_name}' created")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    def upsert_vectors(
        self,
        collection_name: str,
        points: list[dict],
    ) -> bool:
        """Upsert vectors into a collection.

        Args:
            collection_name: Target collection name
            points: List of point dicts with 'id', 'vector', 'payload'

        Returns:
            True if successful
        """
        try:
            qdrant_points = [
                models.PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                )
                for point in points
            ]

            self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
            )

            logger.info(f"Upserted {len(points)} vectors into '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return False

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float = 0.5,
    ) -> list[dict]:
        """Search for similar vectors.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding vector
            limit: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of results with id, score, and payload
        """
        try:
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload,
                }
                for point in results.points
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection.

        Args:
            collection_name: Name of collection to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Collection '{collection_name}' deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[dict]:
        """Get information about a collection.

        Args:
            collection_name: Collection name

        Returns:
            Collection info dict or None if not found
        """
        try:
            collection = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "points_count": collection.points_count,
                "vectors_count": collection.vectors_count,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    def list_collections(self) -> list[dict[str, Any]]:
        """List all collections with metadata.
        
        Returns:
            List of collection dicts with name and basic stats
            
        Example:
            [
                {
                    "name": "documents",
                    "vectors_count": 8432,
                    "points_count": 8432
                }
            ]
        """
        try:
            collections_response = self.client.get_collections()
            collections = []
            
            for collection in collections_response.collections:
                try:
                    # Get detailed info for each collection
                    info = self.client.get_collection(collection.name)
                    collections.append({
                        "name": collection.name,
                        "vectors_count": info.vectors_count or 0,
                        "points_count": info.points_count or 0,
                    })
                except Exception as e:
                    logger.warning(f"Failed to get info for collection '{collection.name}': {e}")
                    collections.append({
                        "name": collection.name,
                        "vectors_count": 0,
                        "points_count": 0,
                    })
            
            logger.debug(f"Listed {len(collections)} collections")
            return collections
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def get_collection_stats(self, collection_name: str) -> Optional[dict[str, Any]]:
        """Get detailed statistics for a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict with detailed statistics or None if collection not found
            
        Example:
            {
                "name": "documents",
                "vectors_count": 8432,
                "points_count": 8432,
                "vector_size": 768,
                "distance_metric": "Cosine",
                "status": "green"
            }
        """
        try:
            collection = self.client.get_collection(collection_name)
            
            # Extract vector config
            vector_config = collection.config.params.vectors
            if isinstance(vector_config, dict):
                # Multiple vector configs
                vector_size = list(vector_config.values())[0].size if vector_config else 0
                distance = list(vector_config.values())[0].distance if vector_config else "Unknown"
            else:
                # Single vector config
                vector_size = vector_config.size
                distance = vector_config.distance.value if hasattr(vector_config.distance, 'value') else str(vector_config.distance)
            
            stats = {
                "name": collection_name,
                "vectors_count": collection.vectors_count or 0,
                "points_count": collection.points_count or 0,
                "vector_size": vector_size,
                "distance_metric": distance,
                "status": collection.status.value if hasattr(collection.status, 'value') else str(collection.status),
            }
            
            logger.debug(f"Retrieved stats for collection '{collection_name}'")
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats for '{collection_name}': {e}")
            return None

    def search_by_text(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        ollama_client: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """Search collection by text query (converts to embedding).
        
        Args:
            query: Text query to search for
            collection: Collection name to search in
            top_k: Number of results to return
            ollama_client: Ollama client for embedding generation (optional)
            
        Returns:
            List of search results with scores and payloads
            
        Example:
            [
                {
                    "id": "doc_123",
                    "score": 0.92,
                    "content": "Document text...",
                    "source": "file.pdf",
                    "chunk_index": 0
                }
            ]
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            # Get embedding from Ollama if client provided, otherwise import
            if ollama_client is None:
                from src.services.ollama_client import OllamaClient
                ollama_client = OllamaClient()
            
            # Generate embedding for query
            query_vector = ollama_client.embed(query)
            
            if not query_vector:
                logger.error("Failed to generate embedding for query")
                return []
            
            # Search using vector
            results = self.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=0.0,  # Return all results, sorted by score
            )
            
            # Enhance results with content from payload
            enhanced_results = []
            for result in results:
                enhanced_result = {
                    "id": result["id"],
                    "score": result["score"],
                    "content": result["payload"].get("content", ""),
                    "source": result["payload"].get("source", ""),
                    "chunk_index": result["payload"].get("chunk_index", 0),
                }
                enhanced_results.append(enhanced_result)
            
            logger.info(f"Text search returned {len(enhanced_results)} results from '{collection}'")
            return enhanced_results
        except Exception as e:
            logger.error(f"Text search failed: {e}", exc_info=True)
            return []

    def create_collection_ui(
        self,
        name: str,
        vector_size: int,
        distance: str = "Cosine",
    ) -> tuple[bool, str]:
        """Create a collection from UI with validation.
        
        Args:
            name: Collection name (alphanumeric, underscore, hyphen only)
            vector_size: Vector dimensionality (1-2048)
            distance: Distance metric ("Cosine", "Euclid", "Dot")
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate collection name
        if not name or not name.strip():
            return False, "Collection name cannot be empty"
        
        name = name.strip()
        if not all(c.isalnum() or c in ('_', '-') for c in name):
            return False, "Collection name can only contain letters, numbers, underscore, and hyphen"
        
        # Validate vector size
        if not (1 <= vector_size <= 2048):
            return False, f"Vector size must be between 1 and 2048 (got {vector_size})"
        
        # Validate distance metric
        valid_distances = {"Cosine", "Euclid", "Dot"}
        if distance not in valid_distances:
            return False, f"Distance must be one of {valid_distances} (got '{distance}')"
        
        # Map string to Qdrant enum
        distance_map = {
            "Cosine": models.Distance.COSINE,
            "Euclid": models.Distance.EUCLID,
            "Dot": models.Distance.DOT,
        }
        
        try:
            # Check if collection already exists
            try:
                self.client.get_collection(name)
                return False, f"Collection '{name}' already exists"
            except Exception:
                # Collection doesn't exist, proceed with creation
                pass
            
            # Create collection
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=distance_map[distance],
                ),
            )
            
            logger.info(f"Collection '{name}' created via UI (size={vector_size}, distance={distance})")
            return True, f"Collection '{name}' created successfully"
        except Exception as e:
            error_msg = f"Failed to create collection: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def delete_collection_ui(self, name: str) -> tuple[bool, str]:
        """Delete a collection with confirmation (for UI).
        
        Args:
            name: Collection name to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not name or not name.strip():
            return False, "Collection name cannot be empty"
        
        name = name.strip()
        
        try:
            # Check if collection exists
            try:
                self.client.get_collection(name)
            except Exception:
                return False, f"Collection '{name}' does not exist"
            
            # Delete collection
            success = self.delete_collection(name)
            
            if success:
                logger.info(f"Collection '{name}' deleted via UI")
                return True, f"Collection '{name}' deleted successfully"
            else:
                return False, f"Failed to delete collection '{name}'"
        except Exception as e:
            error_msg = f"Failed to delete collection: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

