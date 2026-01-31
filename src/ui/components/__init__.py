"""UI Components for Agent Zero.

Contains reusable Streamlit components and navigation system.

Phase 4b: Components reorganized - tool modules moved to src/ui/tools/
"""

# Navigation component (Phase 4b)
from src.ui.components.navigation import SidebarNavigation, ToolDefinition

# Tool imports - re-export from tools package for backwards compatibility
from src.ui.tools import (
    initialize_chat_session,
    initialize_kb_session,
    initialize_logs_session,
    initialize_settings_session,
    render_chat_interface,
    render_knowledge_base,
    render_logs,
    render_settings,
)

__all__ = [
    # Navigation
    "SidebarNavigation",
    "ToolDefinition",
    # Tools (backwards compatibility)
    "render_chat_interface",
    "initialize_chat_session",
    "render_knowledge_base",
    "initialize_kb_session",
    "render_settings",
    "initialize_settings_session",
    "render_logs",
    "initialize_logs_session",
]
