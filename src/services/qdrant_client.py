"""Qdrant Vector Database Client.

Handles semantic search and vector storage operations.
"""

import logging
from typing import Optional

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
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                }
                for result in results
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
