"""Phase 6b performance checkpoint tests.

These tests validate that the Chainlit migration avoids legacy executor-style
workarounds in the UI layer and keeps async dispatch overhead low.
"""

import importlib
import time
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_MAIN_PATH = PROJECT_ROOT / "src" / "ui" / "main.py"
INGEST_PATH = PROJECT_ROOT / "src" / "core" / "ingest.py"


def _load_main_module() -> object:
    """Import and reload src.ui.main with mocked Chainlit fixture in place."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


def test_ui_main_has_no_run_in_executor_calls() -> None:
    """Ensure UI message path no longer uses explicit run_in_executor calls."""
    source = UI_MAIN_PATH.read_text(encoding="utf-8")
    assert "run_in_executor" not in source


def test_ingestor_has_no_dedicated_thread_pool() -> None:
    """Ensure ingestion no longer allocates a per-instance ThreadPoolExecutor."""
    source = INGEST_PATH.read_text(encoding="utf-8")
    assert "ThreadPoolExecutor" not in source
    assert "self._executor" not in source


@pytest.mark.asyncio
async def test_process_message_async_dispatch_overhead_is_low(mock_chainlit) -> None:
    """Benchmark async dispatch overhead for message processing wrapper."""
    main_module = _load_main_module()

    class FastAsyncAgent:
        async def process_message_async(
            self,
            conversation_id: str,
            message: str,
            use_retrieval: bool = True,
        ) -> str:
            return f"ok:{conversation_id}:{message}:{use_retrieval}"

    agent = FastAsyncAgent()
    iterations = 300

    start = time.perf_counter()
    for _ in range(iterations):
        response, error = await main_module._process_message_async(agent, "conv-1", "hello")
        assert error is None
        assert response.startswith("ok:")
    elapsed = time.perf_counter() - start

    avg_latency_ms = (elapsed / iterations) * 1000

    assert avg_latency_ms < 2.0
