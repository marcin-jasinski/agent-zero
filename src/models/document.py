"""Document models for Agent Zero RAG pipeline.

This module defines data structures for document chunks, metadata,
and ingestion results.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class DocumentChunk:
    """Represents a chunk of a document for indexing and retrieval.

    Attributes:
        id: Unique identifier for the chunk
        content: Text content of the chunk
        source: Original document source (filename or URL)
        chunk_index: Sequential index within the document
        metadata: Additional metadata (page number, section, etc.)
        embedding: Vector embedding of the chunk (optional, computed on demand)
        created_at: Timestamp when chunk was created
    """

    id: str
    content: str
    source: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate chunk data after initialization."""
        if not self.id or not self.id.strip():
            raise ValueError("Chunk ID cannot be empty")
        if not self.content or not self.content.strip():
            raise ValueError(f"Chunk {self.id} content cannot be empty")
        if not self.source or not self.source.strip():
            raise ValueError(f"Chunk {self.id} source cannot be empty")
        if self.chunk_index < 0:
            raise ValueError(f"Chunk {self.id} index cannot be negative")

    @property
    def token_count(self) -> int:
        """Estimate token count using rough approximation (4 chars ≈ 1 token)."""
        return max(1, len(self.content) // 4)


@dataclass
class DocumentMetadata:
    """Metadata for a complete document.

    Attributes:
        title: Document title
        author: Document author
        creation_date: Original creation date
        file_size: Size in bytes
        chunk_count: Number of chunks this document was split into
        total_tokens: Total tokens across all chunks
    """

    title: str
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    file_size: int = 0
    chunk_count: int = 0
    total_tokens: int = 0


@dataclass
class IngestionResult:
    """Result of document ingestion operation.

    Attributes:
        success: Whether ingestion succeeded
        document_id: Unique identifier for ingested document
        chunks_count: Number of chunks created
        error: Error message if failed
        duration_seconds: Time taken for ingestion
        document_hash: SHA256 hash of document content
        skipped_duplicate: Whether document was skipped as duplicate
        existing_document_id: ID of existing document if duplicate
    """

    success: bool
    document_id: str
    chunks_count: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    document_hash: Optional[str] = None
    skipped_duplicate: bool = False
    existing_document_id: Optional[str] = None
