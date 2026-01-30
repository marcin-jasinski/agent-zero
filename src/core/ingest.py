"""Document ingestion pipeline for Agent Zero.

This module handles PDF extraction, text chunking, embedding generation,
and indexing into both Qdrant (vector) and Meilisearch (keyword) databases.
"""

import hashlib
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

from pypdf import PdfReader

from src.models.document import DocumentChunk, IngestionResult
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantVectorClient
from src.services.meilisearch_client import MeilisearchClient

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Handles document ingestion: extraction, chunking, embedding, and indexing.

    This class orchestrates the complete pipeline for ingesting documents
    into the knowledge base with semantic (Qdrant) and keyword (Meilisearch) indexing.
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        qdrant_client: QdrantVectorClient,
        meilisearch_client: MeilisearchClient,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        """Initialize the document ingestor.

        Args:
            ollama_client: Client for generating embeddings
            qdrant_client: Client for vector database operations
            meilisearch_client: Client for full-text search indexing
            chunk_size: Number of tokens per chunk (default: 500)
            chunk_overlap: Token overlap between chunks (default: 50)

        Raises:
            ValueError: If chunk_size or chunk_overlap are invalid
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.ollama_client = ollama_client
        self.qdrant_client = qdrant_client
        self.meilisearch_client = meilisearch_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._executor: Optional[ThreadPoolExecutor] = ThreadPoolExecutor(max_workers=2)

    def ingest_pdf(
        self, file_path: str, document_title: Optional[str] = None
    ) -> IngestionResult:
        """Ingest a PDF file into the knowledge base.

        This method orchestrates the complete pipeline:
        1. Extract text from PDF
        2. Split into overlapping chunks
        3. Generate embeddings for each chunk
        4. Store in Qdrant (vector) and Meilisearch (keyword)

        Args:
            file_path: Path to the PDF file
            document_title: Optional custom document title (defaults to filename)

        Returns:
            IngestionResult with success status, document ID, and chunk count
        """
        start_time = time.time()
        document_id = str(uuid4())

        try:
            logger.info(f"Starting ingestion of PDF: {file_path}")

            # Validate file
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            if not file_path.suffix.lower() == ".pdf":
                raise ValueError(f"File must be PDF, got: {file_path.suffix}")

            # Extract text
            text = self._extract_text_from_pdf(str(file_path))
            if not text.strip():
                raise ValueError("PDF contains no extractable text")

            # Split into chunks
            chunks = self._chunk_document(text, str(file_path), document_title or file_path.stem)

            if not chunks:
                raise ValueError("No chunks created from document")

            # Generate embeddings and store
            self._process_chunks(chunks, document_id)

            duration = time.time() - start_time
            logger.info(
                f"Successfully ingested {len(chunks)} chunks from {file_path} "
                f"in {duration:.2f}s"
            )

            return IngestionResult(
                success=True,
                document_id=document_id,
                chunks_count=len(chunks),
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to ingest {file_path}: {str(e)}", exc_info=True)
            return IngestionResult(
                success=False,
                document_id=document_id,
                error=str(e),
                duration_seconds=duration,
            )

    def ingest_pdf_bytes(
        self, 
        pdf_bytes: bytes, 
        filename: str, 
        document_title: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> IngestionResult:
        """Ingest PDF from bytes (e.g., file upload).

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename for reference
            document_title: Optional custom document title
            chunk_size: Override default chunk size
            chunk_overlap: Override default chunk overlap

        Returns:
            IngestionResult with success status, document ID, and chunk count
        """
        start_time = time.time()
        document_id = str(uuid4())

        try:
            logger.info(f"Starting ingestion of PDF bytes: {filename}")

            if not pdf_bytes:
                raise ValueError("PDF bytes cannot be empty")

            # Extract text from bytes
            text = self._extract_text_from_pdf_bytes(pdf_bytes)
            if not text.strip():
                raise ValueError("PDF contains no extractable text")

            # Use custom chunk settings if provided
            original_chunk_size = self.chunk_size
            original_chunk_overlap = self.chunk_overlap
            
            if chunk_size is not None:
                self.chunk_size = chunk_size
            if chunk_overlap is not None:
                self.chunk_overlap = chunk_overlap

            try:
                # Split into chunks
                chunks = self._chunk_document(text, filename, document_title or Path(filename).stem)

                if not chunks:
                    raise ValueError("No chunks created from document")

                # Generate embeddings and store
                self._process_chunks(chunks, document_id)
            finally:
                # Restore original settings
                self.chunk_size = original_chunk_size
                self.chunk_overlap = original_chunk_overlap

            duration = time.time() - start_time
            logger.info(
                f"Successfully ingested {len(chunks)} chunks from {filename} "
                f"in {duration:.2f}s"
            )

            return IngestionResult(
                success=True,
                document_id=document_id,
                chunks_count=len(chunks),
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to ingest PDF bytes {filename}: {str(e)}", exc_info=True)
            return IngestionResult(
                success=False,
                document_id=document_id,
                error=str(e),
                duration_seconds=duration,
            )

    def ingest_text(
        self, 
        text: str, 
        source_name: str, 
        document_title: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> IngestionResult:
        """Ingest plain text or markdown content.

        Args:
            text: Raw text content to ingest
            source_name: Source identifier (e.g., filename)
            document_title: Optional custom document title
            chunk_size: Override default chunk size
            chunk_overlap: Override default chunk overlap

        Returns:
            IngestionResult with success status, document ID, and chunk count
        """
        start_time = time.time()
        document_id = str(uuid4())

        try:
            logger.info(f"Starting ingestion of text: {source_name}")

            if not text or not text.strip():
                raise ValueError("Text content cannot be empty")

            # Use custom chunk settings if provided
            original_chunk_size = self.chunk_size
            original_chunk_overlap = self.chunk_overlap
            
            if chunk_size is not None:
                self.chunk_size = chunk_size
            if chunk_overlap is not None:
                self.chunk_overlap = chunk_overlap

            try:
                # Split into chunks
                chunks = self._chunk_document(text, source_name, document_title or source_name)

                if not chunks:
                    raise ValueError("No chunks created from text")

                # Generate embeddings and store
                self._process_chunks(chunks, document_id)
            finally:
                # Restore original settings
                self.chunk_size = original_chunk_size
                self.chunk_overlap = original_chunk_overlap

            duration = time.time() - start_time
            logger.info(
                f"Successfully ingested {len(chunks)} chunks from {source_name} "
                f"in {duration:.2f}s"
            )

            return IngestionResult(
                success=True,
                document_id=document_id,
                chunks_count=len(chunks),
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to ingest text {source_name}: {str(e)}", exc_info=True)
            return IngestionResult(
                success=False,
                document_id=document_id,
                error=str(e),
                duration_seconds=duration,
            )

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            Exception: If PDF reading fails
        """
        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"[Page {page_num}]\n{text}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}", exc_info=True)
            raise

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text content from PDF bytes.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Extracted text content

        Raises:
            Exception: If PDF reading fails
        """
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            text_parts = []

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"[Page {page_num}]\n{text}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Failed to read PDF bytes: {e}", exc_info=True)
            raise

    def _chunk_document(
        self, text: str, source: str, title: str
    ) -> List[DocumentChunk]:
        """Split document text into overlapping chunks.

        Uses a simple token-based approach where approximately 4 characters = 1 token.

        Args:
            text: Document text to chunk
            source: Source identifier (filename)
            title: Document title for metadata

        Returns:
            List of DocumentChunk objects

        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        chunks = []
        # Rough token estimation: 4 chars ≈ 1 token
        char_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4

        sentences = text.split(". ")
        current_chunk = ""
        chunk_index = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Add period back if not at end
            if not sentence.endswith("."):
                sentence += "."

            # If adding this sentence would exceed size, save current chunk
            if len(current_chunk) + len(sentence) > char_size and current_chunk:
                chunk_text = current_chunk.strip()
                if chunk_text:
                    chunk = DocumentChunk(
                        id=self._generate_chunk_id(source, chunk_index),
                        content=chunk_text,
                        source=source,
                        chunk_index=chunk_index,
                        metadata={"title": title, "page": self._estimate_page(text, chunk_text)},
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Keep overlap for context
                    words = current_chunk.split()
                    overlap_words = int(len(words) * (self.chunk_overlap / self.chunk_size))
                    current_chunk = " ".join(words[-overlap_words:]) + " " if overlap_words > 0 else ""

            current_chunk += sentence + " "

        # Add final chunk
        if current_chunk.strip():
            chunk = DocumentChunk(
                id=self._generate_chunk_id(source, chunk_index),
                content=current_chunk.strip(),
                source=source,
                chunk_index=chunk_index,
                metadata={"title": title, "page": self._estimate_page(text, current_chunk)},
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from document {source}")
        return chunks

    def _generate_chunk_id(self, source: str, chunk_index: int) -> str:
        """Generate unique chunk ID from source and index.

        Args:
            source: Source filename
            chunk_index: Chunk sequential index

        Returns:
            Unique chunk identifier
        """
        hash_suffix = hashlib.md5(f"{source}_{chunk_index}".encode()).hexdigest()[:8]
        return f"{Path(source).stem}_{chunk_index}_{hash_suffix}"

    def _estimate_page(self, full_text: str, chunk_text: str) -> int:
        """Estimate page number where chunk appears.

        Args:
            full_text: Complete document text
            chunk_text: Chunk text to locate

        Returns:
            Estimated page number (1-indexed)
        """
        pos = full_text.find(chunk_text)
        if pos == -1:
            return 1
        # Rough estimate: pages ≈ position / 3000 chars per page
        return max(1, (pos // 3000) + 1)

    def _process_chunks(self, chunks: List[DocumentChunk], document_id: str) -> None:
        """Generate embeddings and store chunks in both databases.

        Args:
            chunks: List of document chunks to process
            document_id: Document identifier for tracking
        """
        from src.config import get_config
        config = get_config()
        
        for chunk in chunks:
            try:
                # Generate embedding
                embedding = self.ollama_client.embed(chunk.content)
                chunk.embedding = embedding

                # Store in Qdrant (vector)
                self.qdrant_client.upsert_vectors(
                    collection_name=config.qdrant.collection_name,
                    points=[
                        {
                            "id": chunk.id,
                            "vector": embedding,
                            "payload": {
                                "content": chunk.content,
                                "source": chunk.source,
                                "chunk_index": chunk.chunk_index,
                                "document_id": document_id,
                                "metadata": chunk.metadata,
                            },
                        }
                    ]
                )

                # Store in Meilisearch (keyword)
                self.meilisearch_client.add_documents(
                    index_uid=config.meilisearch.index_name,
                    documents=[
                        {
                            "id": chunk.id,
                            "content": chunk.content,
                            "source": chunk.source,
                            "chunk_index": chunk.chunk_index,
                            "document_id": document_id,
                            "title": chunk.metadata.get("title", ""),
                        }
                    ]
                )

                logger.debug(f"Processed chunk {chunk.id}")

            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.id}: {e}", exc_info=True)
                # Continue with other chunks rather than failing completely
                continue

    def __del__(self) -> None:
        """Cleanup thread pool on deletion."""
        if hasattr(self, "_executor") and self._executor is not None:
            self._executor.shutdown(wait=True)
