"""Dashboard tools for Agent Zero (Phase 4b).

This package contains modular dashboard tools that can be conditionally
rendered based on feature flags.

Core Tools:
- chat: Main chat interface with agent
- knowledge_base: Document upload and indexing
- settings: Configuration management
- logs: System logs viewer

Management Tools (Phase 4b):
- qdrant_manager: Qdrant vector database management
- langfuse_dashboard: Langfuse observability dashboard
- promptfoo_dashboard: Prompt testing and versioning
- system_health: System health monitoring

Design Reference: DASHBOARD_DESIGN.md
"""

from src.ui.tools.chat import initialize_chat_session, render_chat_interface
from src.ui.tools.knowledge_base import (
    initialize_kb_session,
    render_knowledge_base,
)
from src.ui.tools.langfuse_dashboard import render_langfuse_dashboard
from src.ui.tools.logs import initialize_logs_session, render_logs
from src.ui.tools.promptfoo_dashboard import render_promptfoo_dashboard
from src.ui.tools.qdrant_dashboard import render_qdrant_dashboard
from src.ui.tools.settings import initialize_settings_session, render_settings
from src.ui.tools.system_health import render_system_health_dashboard

__all__ = [
    "initialize_chat_session",
    "render_chat_interface",
    "initialize_kb_session",
    "render_knowledge_base",
    "initialize_logs_session",
    "render_logs",
    "initialize_settings_session",
    "render_settings",
    "render_qdrant_dashboard",
    "render_langfuse_dashboard",
    "render_promptfoo_dashboard",
    "render_system_health_dashboard",
]
