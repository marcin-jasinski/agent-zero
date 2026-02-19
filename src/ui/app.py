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

import logging

from fastapi import FastAPI
import gradio as gr

from src.logging_config import setup_logging
from src.ui.chat import build_chat_ui, initialize_agent
from src.ui.dashboard import build_admin_ui

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

setup_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI REST layer
# ---------------------------------------------------------------------------

api = FastAPI(
    title="Agent Zero API",
    description="Local Agent Builder (L.A.B.) — REST + UI",
    version="0.1.0",
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
        # build_chat_ui returns (state, status_bar) so we can wire the load event
        _chat_state, _chat_status = build_chat_ui()
    with gr.Tab("🛡️ Admin"):
        build_admin_ui()

    # Wire agent initialization to Blocks.load so the progress bar fires on page load
    gradio_app.load(
        fn=initialize_agent,
        inputs=None,
        outputs=[_chat_state, _chat_status],
    )

# ---------------------------------------------------------------------------
# Mount Gradio onto FastAPI
# ---------------------------------------------------------------------------

api = gr.mount_gradio_app(api, gradio_app, path="/")

logger.info("Agent Zero app ready — FastAPI + Gradio mounted on /")
