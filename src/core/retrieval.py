"""Document retrieval engine for Agent Zero.

This module implements hybrid search combining semantic similarity (Qdrant)
and keyword relevance (Meilisearch) for improved document retrieval.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from src.models.retrieval import RetrievalResult, HybridSearchConfig
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantVectorClient
from src.services.meilisearch_client import MeilisearchClient

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """Implements hybrid search across semantic and keyword indices.

    This engine retrieves relevant documents by:
    1. Converting query to embedding (Qdrant semantic search)
    2. Searching keyword index (Meilisearch full-text search)
    3. Merging and ranking results by combined score
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        qdrant_client: QdrantVectorClient,
        meilisearch_client: MeilisearchClient,
        config: Optional[HybridSearchConfig] = None,
    ) -> None:
        """Initialize the retrieval engine.

        Args:
            ollama_client: Client for generating query embeddings
            qdrant_client: QdrantVectorClient for vector similarity search
            meilisearch_client: Client for keyword search
            config: Hybrid search configuration (uses defaults if not provided)
        """
        self.ollama_client = ollama_client
        self.qdrant_client = qdrant_client
        self.meilisearch_client = meilisearch_client
        self.config = config or HybridSearchConfig()

    def retrieve_relevant_docs(
        self,
        query: str,
        top_k: int = 5,
        hybrid: bool = True,
    ) -> List[RetrievalResult]:
        """Retrieve most relevant documents for a query.

        Implements hybrid search: combines semantic similarity (vector) and
        keyword relevance (full-text) for improved retrieval quality.

        Args:
            query: User query string
            top_k: Number of top results to return
            hybrid: Whether to use hybrid search (True) or semantic only (False)

        Returns:
            List of RetrievalResult objects, sorted by combined relevance score

        Raises:
            ValueError: If query is empty or invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        try:
            if hybrid:
                return self._hybrid_search(query, top_k)
            else:
                return self._semantic_search(query, top_k)

        except Exception as e:
            logger.error(f"Retrieval error for query '{query}': {e}", exc_info=True)
            raise

    def _semantic_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Retrieve documents by semantic similarity only.

        Args:
            query: Query string
            top_k: Number of results to return

        Returns:
            List of RetrievalResult objects sorted by similarity score
        """
        import time
        try:
            from src.config import get_config
            config = get_config()
            
            # Generate embedding for query
            embed_start = time.time()
            query_embedding = self.ollama_client.embed(query)
            logger.info(f"[TIMING] Embedding generation took {time.time() - embed_start:.2f}s")

            # Search Qdrant
            search_start = time.time()
            search_results = self.qdrant_client.search(
                collection_name=config.qdrant.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=self.config.min_semantic_score,
            )
            logger.info(f"[TIMING] Qdrant search took {time.time() - search_start:.2f}s")

            results = []
            for result in search_results:
                payload = result.get("payload", {})
                results.append(
                    RetrievalResult(
                        id=result.get("id", ""),
                        content=payload.get("content", ""),
                        source=payload.get("source", ""),
                        chunk_index=payload.get("chunk_index", 0),
                        score=result.get("score", 0.0),
                        metadata=payload.get("metadata", {}),
                        search_type="semantic",
                    )
                )

            logger.debug(f"Semantic search found {len(results)} results for query '{query}'")
            return sorted(results)

        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            raise

    def _keyword_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Retrieve documents by keyword relevance only.

        Args:
            query: Query string
            top_k: Number of results to return

        Returns:
            List of RetrievalResult objects sorted by relevance score
        """
        try:
            from src.config import get_config
            config = get_config()
            
            # Search Meilisearch
            search_results = self.meilisearch_client.search(
                index_uid=config.meilisearch.index_name,
                query=query,
                limit=top_k,
            )

            results = []
            for result in search_results:
                # Normalize Meilisearch score (0-100) to 0-1
                normalized_score = (result.get("_rankingScore", 0) or 0) / 100.0

                if normalized_score >= self.config.min_keyword_score:
                    results.append(
                        RetrievalResult(
                            id=result.get("id", ""),
                            content=result.get("content", ""),
                            source=result.get("source", ""),
                            chunk_index=result.get("chunk_index", 0),
                            score=normalized_score,
                            metadata={"title": result.get("title", "")},
                            search_type="keyword",
                        )
                    )

            logger.debug(f"Keyword search found {len(results)} results for query '{query}'")
            return sorted(results)

        except Exception as e:
            logger.error(f"Keyword search failed: {e}", exc_info=True)
            raise

    def _hybrid_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Retrieve documents using hybrid search.

        Combines semantic (Qdrant) and keyword (Meilisearch) results using
        configured weights. Results are deduplicated and ranked by combined score.

        Args:
            query: Query string
            top_k: Number of results to return

        Returns:
            List of RetrievalResult objects sorted by combined relevance score
        """
        logger.info(f"Using HYBRID search for query: '{query[:100]}...'")
        try:
            # Run both searches in parallel
            logger.debug("Executing semantic search (Qdrant)...")
            semantic_results = self._semantic_search(query, top_k * 2)  # Get more for merging
            logger.info(f"Semantic search returned {len(semantic_results)} results")
            
            logger.debug("Executing keyword search (Meilisearch)...")
            keyword_results = self._keyword_search(query, top_k * 2)
            logger.info(f"Keyword search returned {len(keyword_results)} results")

            # Merge results by ID, combining scores
            merged: Dict[str, RetrievalResult] = {}

            # Add semantic results
            for result in semantic_results:
                merged[result.id] = result
                merged[result.id].score = (
                    result.score * self.config.semantic_weight
                )

            # Add/merge keyword results
            for result in keyword_results:
                if result.id in merged:
                    # Combine scores
                    merged[result.id].score += (
                        result.score * self.config.keyword_weight
                    )
                    merged[result.id].search_type = "hybrid"
                else:
                    result.score = result.score * self.config.keyword_weight
                    result.search_type = "hybrid"
                    merged[result.id] = result

            # Sort by combined score and limit
            final_results = sorted(merged.values())[:top_k]

            logger.debug(
                f"Hybrid search found {len(final_results)} results for query '{query}'"
            )
            return final_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            # Fallback to semantic search only
            logger.warning("Falling back to semantic search only")
            return self._semantic_search(query, top_k)

    def search_with_context(
        self,
        query: str,
        context_chunks: int = 1,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """Retrieve documents with surrounding context chunks.

        When a chunk is retrieved, optionally include surrounding chunks from
        the same document for better context.

        Args:
            query: Query string
            context_chunks: Number of surrounding chunks to include
            top_k: Number of main results to return

        Returns:
            List of RetrievalResult objects with context chunks included
        """
        if context_chunks < 0:
            raise ValueError("context_chunks cannot be negative")

        try:
            main_results = self.retrieve_relevant_docs(query, top_k=top_k)

            if context_chunks == 0:
                return main_results

            # Fetch context chunks for each result
            final_results = []
            for result in main_results:
                final_results.append(result)

                # Get next chunk (if exists)
                if context_chunks >= 1:
                    next_chunk = self._get_chunk_by_index(
                        result.source,
                        result.chunk_index + 1,
                    )
                    if next_chunk:
                        final_results.append(next_chunk)

                # Get previous chunk (if exists)
                if context_chunks >= 2:
                    prev_chunk = self._get_chunk_by_index(
                        result.source,
                        result.chunk_index - 1,
                    )
                    if prev_chunk:
                        final_results.append(prev_chunk)

            return final_results

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}", exc_info=True)
            return self.retrieve_relevant_docs(query, top_k=top_k)

    def _get_chunk_by_index(self, source: str, chunk_index: int) -> Optional[RetrievalResult]:
        """Retrieve a specific chunk by source and index.

        Args:
            source: Document source
            chunk_index: Chunk index within document

        Returns:
            RetrievalResult if found, None otherwise
        """
        if chunk_index < 0:
            return None

        try:
            from src.config import get_config
            config = get_config()
            
            # Note: Simple vector search doesn't support complex filtering.
            # In production, consider using Qdrant's scroll API or full-text search.
            # For now, we return None to indicate context chunks are not available
            # via this simplified search method.
            logger.debug(f"Context chunk lookup (source={source}, index={chunk_index}) not implemented")
            return None
            
        except Exception as e:
            logger.debug(f"Failed to retrieve context chunk: {e}")

        return None
