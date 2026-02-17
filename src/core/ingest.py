"""Document ingestion pipeline for Agent Zero.

This module handles PDF extraction, text chunking, embedding generation,
and indexing into both Qdrant (vector) and Meilisearch (keyword) databases.
"""

import hashlib
import logging
import os
import time
import uuid
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
from src.observability import track_document_ingestion

logger = logging.getLogger(__name__)


def calculate_document_hash(content: bytes) -> str:
    """Calculate SHA256 hash of document content for deduplication.
    
    Args:
        content: Raw document bytes
        
    Returns:
        Hexadecimal SHA256 hash string
    """
    return hashlib.sha256(content).hexdigest()


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

    def check_document_exists(self, document_hash: str) -> tuple[bool, Optional[str], int]:
        """Check if a document with this hash already exists.
        
        Args:
            document_hash: SHA256 hash of document content
            
        Returns:
            Tuple of (exists: bool, document_id: Optional[str], chunk_count: int)
        """
        try:
            from src.config import get_config
            config = get_config()
            
            # Query Meilisearch for documents with this hash
            # (Meilisearch is faster for metadata queries than Qdrant)
            results = self.meilisearch_client.search(
                index_uid=config.meilisearch.index_name,
                query="",  # Empty query to get all, filtered by hash
                limit=1,
            )
            
            # Check if any result has our hash in metadata
            for result in results:
                if result.get("document_hash") == document_hash:
                    doc_id = result.get("document_id")
                    # Count total chunks with this document_id
                    all_docs = self.meilisearch_client.search(
                        index_uid=config.meilisearch.index_name,
                        query="",
                        limit=1000,
                    )
                    chunk_count = sum(1 for d in all_docs if d.get("document_id") == doc_id)
                    return True, doc_id, chunk_count
            
            return False, None, 0
            
        except Exception as e:
            logger.error(f"Error checking for existing document: {e}", exc_info=True)
            return False, None, 0

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
            successful, qdrant_fails, meilisearch_fails = self._process_chunks(chunks, document_id)

            duration = time.time() - start_time
            
            # Determine overall success
            partial_failure = (qdrant_fails > 0 or meilisearch_fails > 0)
            
            if successful == 0:
                raise ValueError(f"Failed to ingest any chunks (Qdrant: {qdrant_fails}, Meilisearch: {meilisearch_fails})")
            
            if partial_failure:
                logger.warning(
                    f"Partially ingested {successful}/{len(chunks)} chunks from {file_path} in {duration:.2f}s "
                    f"(Qdrant failures: {qdrant_fails}, Meilisearch failures: {meilisearch_fails})"
                )
            else:
                logger.info(
                    f"Successfully ingested {len(chunks)} chunks from {file_path} in {duration:.2f}s"
                )

            # Track ingestion metrics
            status = 'failed' if partial_failure else 'success'
            track_document_ingestion(
                status=status,
                chunk_count=successful,
                duration_seconds=duration
            )

            return IngestionResult(
                success=(successful > 0),
                document_id=document_id,
                chunks_count=successful,
                duration_seconds=duration,
                error=f"Partial failures - Qdrant: {qdrant_fails}, Meilisearch: {meilisearch_fails}" if partial_failure else None,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to ingest {file_path}: {str(e)}", exc_info=True)
            
            # Track failed ingestion metrics
            track_document_ingestion(
                status='failed',
                chunk_count=0,
                duration_seconds=duration
            )
            
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
        skip_duplicates: bool = True,
    ) -> IngestionResult:
        """Ingest PDF from bytes (e.g., file upload).

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename for reference
            document_title: Optional custom document title
            chunk_size: Override default chunk size
            chunk_overlap: Override default chunk overlap
            skip_duplicates: If True, skip documents with matching hash

        Returns:
            IngestionResult with success status, document ID, and chunk count
        """
        start_time = time.time()
        document_id = str(uuid4())

        try:
            logger.info(f"Starting ingestion of PDF bytes: {filename}")

            if not pdf_bytes:
                raise ValueError("PDF bytes cannot be empty")

            # Calculate document hash for deduplication
            document_hash = calculate_document_hash(pdf_bytes)
            logger.debug(f"Document hash: {document_hash}")

            # Check for existing document
            if skip_duplicates:
                exists, existing_doc_id, existing_chunk_count = self.check_document_exists(document_hash)
                if exists:
                    duration = time.time() - start_time
                    logger.info(
                        f"Document {filename} already exists (hash: {document_hash[:16]}..., "
                        f"doc_id: {existing_doc_id}, {existing_chunk_count} chunks). Skipping ingestion."
                    )
                    return IngestionResult(
                        success=True,
                        document_id=existing_doc_id,
                        chunks_count=existing_chunk_count,
                        duration_seconds=duration,
                        document_hash=document_hash,
                        skipped_duplicate=True,
                        existing_document_id=existing_doc_id,
                    )

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

                # Add document hash to all chunk metadata
                for chunk in chunks:
                    chunk.metadata["document_hash"] = document_hash

                # Generate embeddings and store
                successful, qdrant_fails, meilisearch_fails = self._process_chunks(chunks, document_id, document_hash)
            finally:
                # Restore original settings
                self.chunk_size = original_chunk_size
                self.chunk_overlap = original_chunk_overlap

            duration = time.time() - start_time
            
            # Determine overall success
            partial_failure = (qdrant_fails > 0 or meilisearch_fails > 0)
            
            if successful == 0:
                raise ValueError(f"Failed to ingest any chunks (Qdrant: {qdrant_fails}, Meilisearch: {meilisearch_fails})")
            
            if partial_failure:
                logger.warning(
                    f"Partially ingested {successful}/{len(chunks)} chunks from {filename} in {duration:.2f}s "
                    f"(Qdrant failures: {qdrant_fails}, Meilisearch failures: {meilisearch_fails})"
                )
            else:
                logger.info(
                    f"Successfully ingested {len(chunks)} chunks from {filename} in {duration:.2f}s"
                )

            # Track ingestion metrics
            status = 'success' if successful > 0 and not partial_failure else 'failed'
            track_document_ingestion(
                status=status,
                chunk_count=successful,
                duration_seconds=duration
            )

            return IngestionResult(
                success=(successful > 0),
                document_id=document_id,
                chunks_count=successful,
                error=f"Partial failures - Qdrant: {qdrant_fails}, Meilisearch: {meilisearch_fails}" if partial_failure else None,
                duration_seconds=duration,
                document_hash=document_hash,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to ingest PDF bytes {filename}: {str(e)}", exc_info=True)
            
            # Track failed ingestion metrics
            track_document_ingestion(
                status='failed',
                chunk_count=0,
                duration_seconds=duration
            )
            
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
                successful, qdrant_fails, meilisearch_fails = self._process_chunks(chunks, document_id)
            finally:
                # Restore original settings
                self.chunk_size = original_chunk_size
                self.chunk_overlap = original_chunk_overlap

            duration = time.time() - start_time
            
            # Determine overall success
            partial_failure = (qdrant_fails > 0 or meilisearch_fails > 0)
            
            if successful == 0:
                raise ValueError(f"Failed to ingest any chunks (Qdrant: {qdrant_fails}, Meilisearch: {meilisearch_fails})")
            
            if partial_failure:
                logger.warning(
                    f"Partially ingested {successful}/{len(chunks)} chunks from {source_name} in {duration:.2f}s "
                    f"(Qdrant failures: {qdrant_fails}, Meilisearch failures: {meilisearch_fails})"
                )
            else:
                logger.info(
                    f"Successfully ingested {len(chunks)} chunks from {source_name} in {duration:.2f}s"
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
        """Generate unique chunk ID using UUID format for Qdrant compatibility.

        Args:
            source: Source filename
            chunk_index: Chunk sequential index

        Returns:
            UUID string compatible with Qdrant point IDs
        """
        # Generate deterministic UUID from source and index
        # Using UUID5 with DNS namespace for reproducibility
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        chunk_uuid = uuid.uuid5(namespace, f"{source}_{chunk_index}")
        return str(chunk_uuid)

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

    def _process_chunks(self, chunks: List[DocumentChunk], document_id: str, document_hash: Optional[str] = None) -> Tuple[int, int, int]:
        """Generate embeddings and store chunks in both databases.

        Args:
            chunks: List of document chunks to process
            document_id: Document identifier for tracking
            document_hash: Optional SHA256 hash of document for deduplication

        Returns:
            Tuple of (successful_count, qdrant_failures, meilisearch_failures)
        """
        from src.config import get_config
        config = get_config()
        
        successful_chunks = 0
        qdrant_failures = 0
        meilisearch_failures = 0
        
        for chunk in chunks:
            chunk_qdrant_success = False
            chunk_meilisearch_success = False
            
            try:
                # Generate embedding
                embedding = self.ollama_client.embed(chunk.content)
                chunk.embedding = embedding

                # Store in Qdrant (vector)
                try:
                    qdrant_success = self.qdrant_client.upsert_vectors(
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
                                    "document_hash": document_hash,
                                    "metadata": chunk.metadata,
                                },
                            }
                        ]
                    )
                    chunk_qdrant_success = qdrant_success
                    if not qdrant_success:
                        logger.warning(f"Qdrant upsert returned False for chunk {chunk.id}")
                        qdrant_failures += 1
                except Exception as e:
                    logger.error(f"Failed to store chunk {chunk.id} in Qdrant: {e}")
                    qdrant_failures += 1

                # Store in Meilisearch (keyword)
                try:
                    meilisearch_success = self.meilisearch_client.add_documents(
                        index_uid=config.meilisearch.index_name,
                        documents=[
                            {
                                "id": chunk.id,
                                "content": chunk.content,
                                "source": chunk.source,
                                "chunk_index": chunk.chunk_index,
                                "document_id": document_id,
                                "document_hash": document_hash,
                                "title": chunk.metadata.get("title", ""),
                            }
                        ]
                    )
                    chunk_meilisearch_success = meilisearch_success
                    if not meilisearch_success:
                        logger.warning(f"Meilisearch add returned False for chunk {chunk.id}")
                        meilisearch_failures += 1
                except Exception as e:
                    logger.error(f"Failed to store chunk {chunk.id} in Meilisearch: {e}")
                    meilisearch_failures += 1

                # Count as successful if at least one database succeeded
                if chunk_qdrant_success or chunk_meilisearch_success:
                    successful_chunks += 1
                    logger.debug(f"Processed chunk {chunk.id} (Qdrant: {chunk_qdrant_success}, Meilisearch: {chunk_meilisearch_success})")

            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.id}: {e}", exc_info=True)
                # Count as failure in both stores
                qdrant_failures += 1
                meilisearch_failures += 1
                continue
        
        logger.info(
            f"Chunk processing complete: {successful_chunks}/{len(chunks)} successful, "
            f"Qdrant failures: {qdrant_failures}, Meilisearch failures: {meilisearch_failures}"
        )
        return successful_chunks, qdrant_failures, meilisearch_failures

    def __del__(self) -> None:
        """Cleanup thread pool on deletion."""
        if hasattr(self, "_executor") and self._executor is not None:
            self._executor.shutdown(wait=True)
