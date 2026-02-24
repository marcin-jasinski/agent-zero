"""Agent Zero (L.A.B.) — FastAPI + Gradio Application Entry Point.

This module is the single entry point for the A.P.I. (AI Playground Interface).
It mounts a Gradio Blocks application (with Chat and Admin tabs) onto a FastAPI
instance so that both the UI and the REST layer are served by one uvicorn process.

Entry point:
    uvicorn src.ui.app:api --host 0.0.0.0 --port 8501

Routes:
    /          → Gradio Blocks UI (tabbed: Chat + Admin)
    /health    → FastAPI health check (used by Docker healthcheck)
"""

import asyncio
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
import gradio as gr

from src.logging_config import setup_logging
from src.startup import ApplicationStartup
from src.ui.chat import build_chat_ui, initialize_agent
from src.ui.dashboard import build_admin_ui, get_health_report

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

setup_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI lifespan — pre-warm Ollama models on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run application startup sequence before serving requests.

    Executes ApplicationStartup (service health checks, model pull if needed,
    and model warm-up) in a thread executor so the async event loop is not
    blocked. Both LLM and embedding models are loaded into GPU VRAM here,
    eliminating the cold-load delay on the very first user message.
    """
    loop = asyncio.get_event_loop()
    logger.info("Running ApplicationStartup (model warm-up)…")
    await loop.run_in_executor(None, ApplicationStartup().run)
    logger.info("ApplicationStartup complete — models are warm and ready")
    yield

# ---------------------------------------------------------------------------
# FastAPI REST layer
# ---------------------------------------------------------------------------

api = FastAPI(
    title="Agent Zero API",
    description="Local Agent Builder (L.A.B.) — REST + UI",
    version="0.1.0",
    lifespan=lifespan,
)


@api.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness check used by Docker HEALTHCHECK and load balancers.

    Returns:
        dict: {"status": "ok"} when the process is running.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(
    title="Agent Zero (L.A.B.)",
    theme=gr.themes.Soft(),
    css="""
        /* Make the tab bar a bit more prominent */
        .tab-nav button { font-size: 1rem; padding: 0.5rem 1.25rem; }
    """,
) as gradio_app:
    gr.Markdown(
        "# 🤖 Agent Zero &nbsp;&nbsp;·&nbsp;&nbsp;"
        "<span style='font-size:0.9rem;color:#888'>Local Agent Builder (L.A.B.)</span>"
    )
    with gr.Tab("💬 Chat"):
        # build_chat_ui returns (state, status_bar, msg_box, send_btn) for load wiring
        _chat_state, _chat_status, _msg_box, _send_btn = build_chat_ui()
    with gr.Tab("🛡️ Admin") as _admin_tab:
        _health_out = build_admin_ui()

    # Wire agent initialization to Blocks.load so the progress bar fires on page load
    gradio_app.load(
        fn=initialize_agent,
        inputs=None,
        outputs=[_chat_state, _chat_status, _msg_box, _send_btn],
    )
    # Populate health report on initial page load (no user interaction needed)
    gradio_app.load(
        fn=get_health_report,
        inputs=None,
        outputs=[_health_out],
    )
    # Re-run health check whenever the user enters the Admin tab
    _admin_tab.select(fn=get_health_report, outputs=[_health_out])

# ---------------------------------------------------------------------------
# Mount Gradio onto FastAPI
# ---------------------------------------------------------------------------

api = gr.mount_gradio_app(api, gradio_app, path="/")

logger.info("Agent Zero app ready — FastAPI + Gradio mounted on /")
