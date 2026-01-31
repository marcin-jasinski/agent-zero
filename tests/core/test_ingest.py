"""Unit tests for document ingestion pipeline.

Tests the DocumentIngestor class covering text extraction, chunking,
embedding generation, and indexing operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from src.core.ingest import DocumentIngestor
from src.models.document import DocumentChunk, IngestionResult


class TestDocumentChunk:
    """Test DocumentChunk data model."""

    def test_valid_chunk_creation(self) -> None:
        """Test creating a valid document chunk."""
        chunk = DocumentChunk(
            id="chunk_1",
            content="Test content",
            source="test.pdf",
            chunk_index=0,
        )
        assert chunk.id == "chunk_1"
        assert chunk.content == "Test content"
        assert chunk.source == "test.pdf"
        assert chunk.chunk_index == 0

    def test_chunk_requires_non_empty_id(self) -> None:
        """Test that chunk ID cannot be empty."""
        with pytest.raises(ValueError, match="Chunk ID cannot be empty"):
            DocumentChunk(id="", content="content", source="test.pdf", chunk_index=0)

    def test_chunk_requires_non_empty_content(self) -> None:
        """Test that chunk content cannot be empty."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            DocumentChunk(id="chunk_1", content="", source="test.pdf", chunk_index=0)

    def test_chunk_requires_non_empty_source(self) -> None:
        """Test that chunk source cannot be empty."""
        with pytest.raises(ValueError, match="source cannot be empty"):
            DocumentChunk(id="chunk_1", content="content", source="", chunk_index=0)

    def test_chunk_requires_non_negative_index(self) -> None:
        """Test that chunk index cannot be negative."""
        with pytest.raises(ValueError, match="index cannot be negative"):
            DocumentChunk(id="chunk_1", content="content", source="test.pdf", chunk_index=-1)

    def test_chunk_token_count(self) -> None:
        """Test token count estimation."""
        chunk = DocumentChunk(
            id="chunk_1",
            content="a" * 400,  # 400 chars ≈ 100 tokens
            source="test.pdf",
            chunk_index=0,
        )
        assert chunk.token_count == 100


class TestDocumentIngestor:
    """Test DocumentIngestor class."""

    @pytest.fixture
    def mock_clients(self) -> tuple:
        """Create mock service clients."""
        ollama_mock = Mock()
        qdrant_mock = Mock()
        meilisearch_mock = Mock()
        return ollama_mock, qdrant_mock, meilisearch_mock

    @pytest.fixture
    def ingestor(self, mock_clients) -> DocumentIngestor:
        """Create DocumentIngestor with mocked clients."""
        ollama, qdrant, meilisearch = mock_clients
        return DocumentIngestor(ollama, qdrant, meilisearch)

    def test_ingestor_initialization(self, mock_clients) -> None:
        """Test ingestor initialization."""
        ollama, qdrant, meilisearch = mock_clients
        ingestor = DocumentIngestor(ollama, qdrant, meilisearch, chunk_size=1000, chunk_overlap=100)
        assert ingestor.chunk_size == 1000
        assert ingestor.chunk_overlap == 100

    def test_ingestor_invalid_chunk_size(self, mock_clients) -> None:
        """Test that invalid chunk size raises error."""
        ollama, qdrant, meilisearch = mock_clients
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            DocumentIngestor(ollama, qdrant, meilisearch, chunk_size=0)

    def test_ingestor_invalid_chunk_overlap(self, mock_clients) -> None:
        """Test that overlap >= size raises error."""
        ollama, qdrant, meilisearch = mock_clients
        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            DocumentIngestor(ollama, qdrant, meilisearch, chunk_size=500, chunk_overlap=500)

    def test_extract_text_from_pdf_bytes(self, ingestor) -> None:
        """Test extracting text from PDF bytes."""
        # This test requires actual PDF bytes or mocking
        with patch("src.core.ingest.PdfReader") as mock_pdf:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample PDF text"
            mock_pdf.return_value.pages = [mock_page]

            text = ingestor._extract_text_from_pdf_bytes(b"fake pdf data")
            assert "Sample PDF text" in text

    def test_chunk_document(self, ingestor) -> None:
        """Test document chunking."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = ingestor._chunk_document(text, "test.pdf", "Test Document")

        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.source == "test.pdf" for chunk in chunks)
        assert chunks[0].chunk_index == 0

    def test_chunk_document_empty_text(self, ingestor) -> None:
        """Test that empty text raises error."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            ingestor._chunk_document("", "test.pdf", "Title")

    def test_generate_chunk_id(self, ingestor) -> None:
        """Test chunk ID generation."""
        chunk_id = ingestor._generate_chunk_id("document.pdf", 5)
        assert chunk_id.startswith("document_5_")
        assert len(chunk_id) > len("document_5_")

    def test_estimate_page(self, ingestor) -> None:
        """Test page number estimation."""
        full_text = "a" * 10000
        chunk_text = full_text[3000:3100]
        page = ingestor._estimate_page(full_text, chunk_text)
        assert page >= 1

    def test_ingest_pdf_bytes_success(self, ingestor) -> None:
        """Test successful PDF ingestion from bytes."""
        ingestor.ollama_client.generate_embedding = Mock(return_value=[0.1] * 384)

        with patch("src.core.ingest.PdfReader") as mock_pdf:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content. More content."
            mock_pdf.return_value.pages = [mock_page]

            result = ingestor.ingest_pdf_bytes(b"fake pdf", "test.pdf")

            assert result.success
            assert result.chunks_count > 0
            assert result.error is None
            assert result.duration_seconds >= 0

    def test_ingest_pdf_bytes_empty(self, ingestor) -> None:
        """Test ingesting empty PDF bytes."""
        result = ingestor.ingest_pdf_bytes(b"", "test.pdf")
        assert not result.success
        assert "empty" in result.error.lower()

    def test_ingest_pdf_bytes_no_text(self, ingestor) -> None:
        """Test ingesting PDF with no extractable text."""
        with patch("src.core.ingest.PdfReader") as mock_pdf:
            mock_page = Mock()
            mock_page.extract_text.return_value = ""
            mock_pdf.return_value.pages = [mock_page]

            result = ingestor.ingest_pdf_bytes(b"fake pdf", "test.pdf")
            assert not result.success

    def test_process_chunks(self, ingestor) -> None:
        """Test chunk processing and storage."""
        chunks = [
            DocumentChunk(
                id="chunk_1",
                content="Content one",
                source="test.pdf",
                chunk_index=0,
            ),
            DocumentChunk(
                id="chunk_2",
                content="Content two",
                source="test.pdf",
                chunk_index=1,
            ),
        ]

        ingestor.ollama_client.embed = Mock(return_value=[0.1] * 384)

        ingestor._process_chunks(chunks, "doc_id")

        # Verify embeddings were generated (method is 'embed' not 'generate_embedding')
        assert ingestor.ollama_client.embed.call_count >= 2

        # Verify chunks were stored in Qdrant
        assert ingestor.qdrant_client.upsert_vectors.called

        # Verify chunks were indexed in Meilisearch (method is 'add_documents')
        assert ingestor.meilisearch_client.add_documents.called

    def test_ingest_result_creation(self) -> None:
        """Test IngestionResult creation."""
        result = IngestionResult(
            success=True,
            document_id="doc_1",
            chunks_count=5,
            duration_seconds=2.5,
        )
        assert result.success
        assert result.chunks_count == 5
        assert result.error is None

    def test_ingest_result_failure(self) -> None:
        """Test failed IngestionResult."""
        result = IngestionResult(
            success=False,
            document_id="doc_1",
            error="Processing failed",
        )
        assert not result.success
        assert result.error == "Processing failed"
