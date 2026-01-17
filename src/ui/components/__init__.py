"""UI Components for Agent Zero.

Contains reusable Streamlit components for each main feature area.
"""

from src.ui.components.chat import initialize_chat_session, render_chat_interface
from src.ui.components.knowledge_base import initialize_kb_session, render_knowledge_base
from src.ui.components.logs import initialize_logs_session, render_logs
from src.ui.components.settings import initialize_settings_session, render_settings

__all__ = [
    "render_chat_interface",
    "initialize_chat_session",
    "render_knowledge_base",
    "initialize_kb_session",
    "render_settings",
    "initialize_settings_session",
    "render_logs",
    "initialize_logs_session",
]
