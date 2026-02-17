"""Chainlit document upload tests for Phase 6b Step 27."""

import importlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _load_main_module() -> object:
    """Import and reload `src.ui.main` to ensure mocked Chainlit is used."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


@pytest.mark.asyncio
async def test_process_file_upload_rejects_unsupported_extension(mock_chainlit) -> None:
    """Unsupported extension returns user-facing error message."""
    main_module = _load_main_module()
    file_obj = mock_chainlit["module"].File(name="malware.exe", content=b"x")

    await main_module.process_file_upload(file_obj)

    assert any("Unsupported file type" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_process_file_upload_handles_ingestor_initialization_error(mock_chainlit) -> None:
    """Upload flow stops with clear error when ingestor cannot be created."""
    main_module = _load_main_module()
    file_obj = mock_chainlit["module"].File(name="doc.txt", content=b"hello")

    with patch.object(main_module, "_get_or_create_ingestor", return_value=(None, "init failed")):
        await main_module.process_file_upload(file_obj)

    assert any("init failed" in msg.content for msg in mock_chainlit["messages"])


@pytest.mark.asyncio
async def test_process_file_upload_success(mock_chainlit) -> None:
    """Successful ingestion reports indexed document details."""
    main_module = _load_main_module()
    file_obj = mock_chainlit["module"].File(name="doc.md", content=b"# hello")

    result = SimpleNamespace(
        success=True,
        skipped_duplicate=False,
        document_id="doc-1",
        chunks_count=3,
        duration_seconds=1.2,
        error=None,
        existing_document_id=None,
    )

    with patch.object(main_module, "_get_or_create_ingestor", return_value=(object(), None)), patch.object(
        main_module,
        "_ingest_document_async",
        return_value=(result, None),
    ):
        await main_module.process_file_upload(file_obj)

    assert any("Document indexed successfully" in msg.content for msg in mock_chainlit["messages"])
