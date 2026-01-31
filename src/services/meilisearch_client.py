"""Meilisearch Full-Text Search Client.

Handles keyword search and document indexing.
"""

import logging
from typing import Optional

import meilisearch

from src.config import get_config

logger = logging.getLogger(__name__)


class MeilisearchClient:
    """Client for Meilisearch full-text search engine."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, api_key: Optional[str] = None):
        """Initialize Meilisearch client.

        Args:
            host: Meilisearch host or full URL (default: from config)
            port: Meilisearch port (default: from config)
            api_key: API key for authentication (default: from config)
        """
        config = get_config()
        # If host is provided, use it; otherwise use config which already contains full URL
        if host:
            self.host = host
            self.port = port or 7700
        else:
            # Config already provides full URL (e.g., http://meilisearch:7700)
            self.url = config.meilisearch.host
            self.api_key = api_key or config.meilisearch.api_key
            try:
                self.client = meilisearch.Client(self.url, api_key=self.api_key)
                logger.info(f"Meilisearch client initialized: {self.url}")
            except Exception as e:
                logger.error(f"Failed to initialize Meilisearch client: {e}")
                raise
            return
            
        # If host was explicitly provided, construct URL
        self.port = port or config.meilisearch.port
        self.api_key = api_key or config.meilisearch.api_key
        self.url = f"http://{self.host}:{self.port}"

        try:
            self.client = meilisearch.Client(self.url, api_key=self.api_key)
            logger.info(f"Meilisearch client initialized: {self.url}")
        except Exception as e:
            logger.error(f"Failed to initialize Meilisearch client: {e}")
            raise

    def is_healthy(self) -> bool:
        """Check if Meilisearch service is healthy.

        Returns:
            True if service is responding, False otherwise
        """
        try:
            health = self.client.health()
            return health.get("status") == "available"
        except Exception as e:
            logger.warning(f"Meilisearch health check failed: {e}")
            return False

    def create_index(
        self,
        index_uid: str,
        primary_key: str = "id",
    ) -> bool:
        """Create a searchable index.

        Args:
            index_uid: Unique identifier for the index (alphanumeric, -, _)
            primary_key: Primary key field name

        Returns:
            True if successful

        Raises:
            ValueError: If index_uid is invalid
        """
        # Validate index_uid (Meilisearch naming rules)
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", index_uid):
            raise ValueError(
                f"index_uid must contain only alphanumeric characters, hyphens, "
                f"and underscores, got '{index_uid}'"
            )
        
        try:
            self.client.create_index(index_uid, {"primaryKey": primary_key})
            logger.info(f"Index '{index_uid}' created")
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False

    def add_documents(
        self,
        index_uid: str,
        documents: list[dict],
        primary_key: str = "id",
    ) -> bool:
        """Add documents to an index.

        Args:
            index_uid: Target index UID
            documents: List of document dicts with required fields
            primary_key: Primary key field name

        Returns:
            True if successful
        """
        try:
            index = self.client.index(index_uid)
            index.add_documents(documents, primary_key=primary_key)
            logger.info(f"Added {len(documents)} documents to index '{index_uid}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False

    def search(
        self,
        index_uid: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search documents in an index.

        Args:
            index_uid: Index UID to search
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        try:
            index = self.client.index(index_uid)
            results = index.search(query, {"limit": limit})
            return results.get("hits", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete_index(self, index_uid: str) -> bool:
        """Delete an index.

        Args:
            index_uid: Index UID to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete_index(index_uid)
            logger.info(f"Index '{index_uid}' deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False

    def get_index_stats(self, index_uid: str) -> Optional[dict]:
        """Get statistics about an index.

        Args:
            index_uid: Index UID

        Returns:
            Index stats dict or None
        """
        try:
            index = self.client.index(index_uid)
            stats = index.get_stats()
            return {
                "documents_count": getattr(stats, "number_of_documents", 0),
                "is_indexing": getattr(stats, "is_indexing", False),
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return None

    def list_indexes(self) -> list[str]:
        """List all indexes.

        Returns:
            List of index UIDs
        """
        try:
            indexes = self.client.get_indexes()
            return [idx.uid for idx in indexes.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            return []
