"""Agent Zero (L.A.B.) — Gradio Chat Tab.

This module builds the "💬 Chat" tab of the unified Gradio UI.
It is called by src.ui.app and returns nothing — all components are
registered inside the active gr.Blocks() context.

Key functions exposed for testing (plain Python — no framework mocking needed):
  - initialize_agent(progress)  → (state_dict, status_md)
  - respond(message, history, state)  → generator[("", history)]
  - ingest_document(file, state, progress)  → status_md
"""

import logging
import queue
import threading
from pathlib import Path
from typing import Generator, Optional

import gradio as gr

from src.config import get_config
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
config = get_config()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def initialize_agent(progress: gr.Progress = gr.Progress()) -> tuple[dict, str]:
    """Connect to all required services and create an AgentOrchestrator.

    Uses gr.Progress() so Gradio renders a real progress bar while the
    user waits for the container startup sequence to complete.

    Args:
        progress: Gradio progress tracker injected automatically.

    Returns:
        Tuple of (session_state dict, status markdown string).
        On failure the state dict is empty and the status contains the error.
    """
    try:
        from src.core.agent import AgentOrchestrator
        from src.core.retrieval import RetrievalEngine
        from src.services.ollama_client import OllamaClient
        from src.services.qdrant_client import QdrantVectorClient
        from src.services.meilisearch_client import MeilisearchClient

        # ------------------------------------------------------------------
        # 1. Ollama
        # ------------------------------------------------------------------
        progress(0.0, desc="Connecting to Ollama…")
        ollama = OllamaClient()
        if not ollama.is_healthy():
            return {}, "❌ **Ollama is not reachable.**\n\nCheck that the Ollama container is running."

        # ------------------------------------------------------------------
        # 2. Qdrant
        # ------------------------------------------------------------------
        progress(0.33, desc="Connecting to Qdrant…")
        qdrant = QdrantVectorClient()
        if not qdrant.is_healthy():
            return {}, "❌ **Qdrant is not reachable.**\n\nCheck that the Qdrant container is running."

        # ------------------------------------------------------------------
        # 3. Meilisearch
        # ------------------------------------------------------------------
        progress(0.66, desc="Connecting to Meilisearch…")
        meilisearch = MeilisearchClient()
        if not meilisearch.is_healthy():
            return (
                {},
                "❌ **Meilisearch is not reachable.**\n\n"
                "Check that the Meilisearch container is running.",
            )

        # ------------------------------------------------------------------
        # 4. Build agent
        # ------------------------------------------------------------------
        progress(0.85, desc="Initializing agent…")
        retrieval = RetrievalEngine(ollama, qdrant, meilisearch)
        agent = AgentOrchestrator(ollama, retrieval)
        conversation_id = agent.start_conversation()

        progress(1.0, desc="Agent ready ✅")
        logger.info(f"Chat agent initialized — conversation_id={conversation_id}")

        state = {
            "agent": agent,
            "conversation_id": conversation_id,
            "ollama": ollama,
            "qdrant": qdrant,
            "meilisearch": meilisearch,
        }
        return state, "✅ **All services connected.**  Agent is ready."

    except Exception as exc:
        logger.error(f"Agent initialization failed: {exc}", exc_info=True)
        return {}, f"❌ **Initialization error:**\n\n```\n{exc}\n```"


# ---------------------------------------------------------------------------
# Chat response (streaming via queue)
# ---------------------------------------------------------------------------


def respond(
    message: str,
    history: list[dict],
    state: dict,
) -> Generator[tuple[str, list[dict]], None, None]:
    """Handle a user message and stream the agent response.

    The underlying LLM call is made in a background thread so the Gradio
    UI thread remains free to yield updates. The generator yields a single
    "Thinking…" placeholder immediately, then replaces it with the full
    response once the model returns.

    Args:
        message: User text input.
        history: Current chat history in OpenAI messages format.
        state: Per-session state dict produced by initialize_agent().

    Yields:
        Tuple of (cleared_input_text, updated_history).
    """
    if not message or not message.strip():
        yield "", history
        return

    if not state or "agent" not in state:
        history = list(history)
        history.append({"role": "user", "content": message})
        history.append(
            {
                "role": "assistant",
                "content": "⚠️ Agent is not initialized. Please wait for startup to complete.",
            }
        )
        yield "", history
        return

    agent = state["agent"]
    conversation_id: str = state["conversation_id"]

    # Show thinking placeholder immediately so the user gets instant feedback
    history = list(history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": "⏳ Thinking…"})
    yield "", history

    # Run the blocking LLM call in a thread; collect response via queue
    chunk_queue: queue.Queue[Optional[str]] = queue.Queue()

    def _stream_cb(chunk: str) -> None:
        chunk_queue.put(chunk)

    def _run() -> None:
        try:
            agent.process_message(conversation_id, message, stream_callback=_stream_cb)
        except Exception as exc:
            logger.error(f"Message processing error: {exc}", exc_info=True)
            chunk_queue.put(f"\n\n❌ **Error:** {exc}")
        finally:
            chunk_queue.put(None)  # sentinel

    threading.Thread(target=_run, daemon=True).start()

    accumulated = ""
    while True:
        chunk = chunk_queue.get()
        if chunk is None:
            break
        accumulated += chunk
        history[-1]["content"] = accumulated
        yield "", history

    if not accumulated:
        history[-1]["content"] = "⚠️ No response was generated. Please try again."
        yield "", history


# ---------------------------------------------------------------------------
# Document ingestion
# ---------------------------------------------------------------------------


def ingest_document(
    file: object,  # gr.File upload object
    state: dict,
    progress: gr.Progress = gr.Progress(),
) -> str:
    """Ingest an uploaded document into the knowledge base.

    Args:
        file: Gradio file upload object with `.name` (temp path) attribute.
        state: Per-session state dict containing service clients.
        progress: Gradio progress tracker injected automatically.

    Returns:
        Status markdown string describing the result.
    """
    if file is None:
        return "⚠️ No file selected."

    if not state or "ollama" not in state:
        return "⚠️ Agent not initialized. Please wait for startup to complete."

    try:
        from src.core.ingest import DocumentIngestor

        file_path = Path(file.name)
        filename = file_path.name
        ext = file_path.suffix.lower()

        if ext not in {".pdf", ".txt", ".md"}:
            return f"❌ Unsupported file type `{ext}`. Supported: `.pdf`, `.txt`, `.md`"

        progress(0.0, desc=f"Reading {filename}…")

        ingestor = DocumentIngestor(
            ollama_client=state["ollama"],
            qdrant_client=state["qdrant"],
            meilisearch_client=state["meilisearch"],
        )

        if ext == ".pdf":
            progress(0.2, desc="Parsing PDF…")
            file_bytes = file_path.read_bytes()
            progress(0.4, desc="Chunking text…")
            result = ingestor.ingest_pdf_bytes(file_bytes, filename)
        else:
            progress(0.2, desc="Reading text…")
            text = file_path.read_text(encoding="utf-8", errors="replace")
            progress(0.4, desc="Chunking text…")
            result = ingestor.ingest_text(text, source_name=filename)

        progress(0.9, desc="Indexing…")
        progress(1.0, desc="Done ✅")

        if not result.success:
            return f"❌ **Ingestion failed:** {result.error}"

        if getattr(result, "skipped_duplicate", False):
            return (
                f"ℹ️ **{filename}** was already in the knowledge base "
                f"({result.chunks_count} chunks, doc_id `{result.document_id[:8]}…`)."
            )

        return (
            f"✅ **{filename}** indexed successfully.\n\n"
            f"- **Chunks**: {result.chunks_count}\n"
            f"- **Doc ID**: `{result.document_id[:8]}…`\n"
            f"- **Time**: {result.duration_seconds:.1f}s\n\n"
            f"You can now ask questions about this document."
        )

    except UnicodeDecodeError:
        return f"❌ Could not read `{filename}` as UTF-8 text. Please ensure the file is valid."
    except Exception as exc:
        logger.error(f"Document ingestion failed: {exc}", exc_info=True)
        return f"❌ **Ingestion error:** {exc}"


# ---------------------------------------------------------------------------
# UI builder (called from app.py inside gr.Blocks context)
# ---------------------------------------------------------------------------


def build_chat_ui() -> tuple[gr.State, gr.Markdown]:
    """Register all Chat tab components inside the active gr.Blocks context.

    Must be called inside an open ``with gr.Blocks() as …`` / ``with gr.Tab():``
    context.  Returns *(state, status_bar)* so the caller (app.py) can wire
    the ``blocks.load()`` event to ``initialize_agent``.

    Returns:
        Tuple of (session state component, status markdown component).
    """
    state = gr.State({})

    # Status bar — updated by initialize_agent on page load
    status_bar = gr.Markdown("⏳ Initializing agent, please wait…")

    # Main chat window
    chatbot = gr.Chatbot(
        value=[],
        type="messages",
        height=520,
        label="Agent Zero",
        avatar_images=(None, "https://raw.githubusercontent.com/gradio-app/gradio/main/guides/assets/logo.svg"),
        show_copy_button=True,
        bubble_full_width=False,
    )

    # Input row
    with gr.Row():
        msg_box = gr.Textbox(
            placeholder="Ask me anything…  (Enter to send)",
            scale=6,
            show_label=False,
            container=False,
            autofocus=True,
        )
        send_btn = gr.Button("Send ▶", variant="primary", scale=1, min_width=100)

    # File upload
    with gr.Accordion("📎 Upload document to Knowledge Base", open=False):
        upload = gr.File(
            file_types=[".pdf", ".txt", ".md"],
            label="Drop a PDF, TXT or MD file here",
        )
        upload_status = gr.Markdown("")

    # -----------------------------------------------------------------------
    # Wire up events
    # -----------------------------------------------------------------------

    # Submit message (Enter key or Send button)
    submit_args = dict(
        fn=respond,
        inputs=[msg_box, chatbot, state],
        outputs=[msg_box, chatbot],
    )
    msg_box.submit(**submit_args)
    send_btn.click(**submit_args)

    # File upload
    upload.upload(
        fn=ingest_document,
        inputs=[upload, state],
        outputs=[upload_status],
    )

    # Return components needed by app.py to wire the .load() event
    return state, status_bar
