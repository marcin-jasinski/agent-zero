"""Retrieval models for Agent Zero RAG pipeline.

This module defines data structures for retrieval results and relevance
scoring across semantic and keyword search.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class RetrievalResult:
    """Represents a single retrieved document chunk with relevance score.

    Attributes:
        id: Chunk identifier
        content: Chunk text content
        source: Original document source
        chunk_index: Index within the source document
        score: Relevance score (0.0-1.0)
        metadata: Additional metadata (title, page, etc.)
        search_type: Type of search that found this result ('semantic', 'keyword', 'hybrid')
    """

    id: str
    content: str
    source: str
    chunk_index: int
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    search_type: str = "hybrid"

    def __post_init__(self) -> None:
        """Validate result data after initialization."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")

    def __lt__(self, other: "RetrievalResult") -> bool:
        """Compare results by score for sorting (higher scores first)."""
        return self.score > other.score


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search combining semantic and keyword.

    Attributes:
        semantic_weight: Weight for semantic similarity (0.0-1.0)
        keyword_weight: Weight for keyword relevance (0.0-1.0)
        min_semantic_score: Minimum score for semantic results
        min_keyword_score: Minimum score for keyword results
        max_results: Maximum number of results to return
    """

    semantic_weight: float = 0.6
    keyword_weight: float = 0.4
    min_semantic_score: float = 0.3
    min_keyword_score: float = 0.1
    max_results: int = 10

    def __post_init__(self) -> None:
        """Validate configuration."""
        weights_sum = self.semantic_weight + self.keyword_weight
        if not (0.99 <= weights_sum <= 1.01):  # Allow for floating point rounding
            raise ValueError(f"Semantic + keyword weights must sum to 1.0, got {weights_sum}")
        if not (0.0 <= self.min_semantic_score <= 1.0):
            raise ValueError(f"min_semantic_score must be 0.0-1.0, got {self.min_semantic_score}")
        if not (0.0 <= self.min_keyword_score <= 1.0):
            raise ValueError(f"min_keyword_score must be 0.0-1.0, got {self.min_keyword_score}")
        if self.max_results <= 0:
            raise ValueError(f"max_results must be positive, got {self.max_results}")
