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
import warnings

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

# Gradio 6 moved theme/css to launch(), but when mounting on FastAPI via
# gr.mount_gradio_app() there is no launch() call.  The params still work
# in gr.Blocks(); suppress the advisory warning for this use-case.
warnings.filterwarnings(
    "ignore",
    message="The parameters have been moved from the Blocks constructor",
    category=UserWarning,
    module="gradio",
)

# ---------------------------------------------------------------------------
# FastAPI lifespan — pre-warm Ollama models on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Start the app immediately, run warm-up in the background.

    Yields right away so FastAPI begins accepting requests (including the
    Docker HEALTHCHECK ``/health`` probe) before the slow model warm-up
    finishes.  The warm-up task runs concurrently and logs its result.
    """
    async def _background_startup() -> None:
        loop = asyncio.get_event_loop()
        try:
            logger.info("ApplicationStartup running in background…")
            await loop.run_in_executor(None, ApplicationStartup().run)
            logger.info("ApplicationStartup complete — models are warm and ready")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("ApplicationStartup failed: %s", exc, exc_info=True)

    asyncio.ensure_future(_background_startup())
    logger.info("FastAPI ready — startup warm-up running in background")
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
        # build_chat_ui returns (state, status_bar, msg_box, send_btn,
        # thinking_md, thinking_accordion)
        (
            _chat_state, _chat_status, _msg_box,
            _send_btn, _thinking_md, _thinking_accordion,
        ) = build_chat_ui()
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
