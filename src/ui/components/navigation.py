"""Navigation component for Agent Zero dashboard (Phase 4b).

Provides dynamic sidebar navigation with feature flag support for conditional
tool rendering. Implements the ToolDefinition pattern for modular tool management.

Design Reference: DASHBOARD_DESIGN.md § "Sidebar Navigation Structure"
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st


logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a dashboard tool with metadata and rendering function.
    
    Attributes:
        key: Unique identifier for the tool (used in session state and routing)
        icon: Emoji icon for visual identification
        label: Display name shown in navigation
        description: Brief description of tool functionality
        render_func: Function that renders the tool's UI (takes no arguments)
        enabled: Whether the tool is currently available (controlled by feature flags)
        category: Tool category ("core" or "management")
    """
    
    key: str
    icon: str
    label: str
    description: str
    render_func: Callable[[], None]
    enabled: bool = True
    category: str = "core"
    
    def __post_init__(self) -> None:
        """Validate tool definition after initialization."""
        if not self.key:
            raise ValueError("Tool key cannot be empty")
        if not callable(self.render_func):
            raise ValueError(f"Tool {self.key}: render_func must be callable")


class SidebarNavigation:
    """Manages sidebar navigation for Agent Zero dashboard.
    
    Dynamically renders navigation based on:
    - Feature flags from DashboardFeatures configuration
    - Tool availability (enabled/disabled)
    - User permissions (future enhancement)
    
    Usage:
        ```python
        nav = SidebarNavigation()
        nav.register_tool(ToolDefinition(
            key="chat",
            icon=">",
            label="Chat",
            description="Chat with Agent Zero",
            render_func=render_chat_interface,
            enabled=config.dashboard.show_chat
        ))
        nav.render()
        ```
    """
    
    def __init__(self) -> None:
        """Initialize navigation component."""
        self.tools: list[ToolDefinition] = []
        self._session_key = "active_tool"
        
        # Initialize session state for active tool
        if self._session_key not in st.session_state:
            st.session_state[self._session_key] = None
        
        logger.debug("SidebarNavigation initialized")
    
    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool for navigation.
        
        Args:
            tool: ToolDefinition instance describing the tool
            
        Raises:
            ValueError: If tool with same key already registered
        """
        # Check for duplicate keys
        if any(t.key == tool.key for t in self.tools):
            raise ValueError(f"Tool with key '{tool.key}' already registered")
        
        self.tools.append(tool)
        logger.debug(f"Registered tool: {tool.key} ({tool.label})")
    
    def get_enabled_tools(self, category: Optional[str] = None) -> list[ToolDefinition]:
        """Get list of enabled tools, optionally filtered by category.
        
        Args:
            category: Optional category filter ("core" or "management")
            
        Returns:
            List of enabled ToolDefinition instances
        """
        tools = [t for t in self.tools if t.enabled]
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        return tools
    
    def render_sidebar(self) -> None:
        """Render navigation sidebar with tool selection.
        
        Displays:
        - Core tools section (always visible)
        - Management tools section (if any enabled)
        - Active tool indicator
        """
        with st.sidebar:
            st.title("Agent Zero")
            st.caption("L.A.B. - Local Agent Builder")
            st.divider()
            
            # Core Tools Section
            core_tools = self.get_enabled_tools(category="core")
            if core_tools:
                st.subheader("Core Tools")
                self._render_tool_buttons(core_tools)
                st.divider()
            
            # Management Tools Section
            mgmt_tools = self.get_enabled_tools(category="management")
            if mgmt_tools:
                st.subheader("Management Tools")
                self._render_tool_buttons(mgmt_tools)
                st.divider()
            
            # Set default active tool if none selected
            if st.session_state[self._session_key] is None and core_tools:
                st.session_state[self._session_key] = core_tools[0].key
                logger.debug(f"Default tool set to: {core_tools[0].key}")
    
    def _render_tool_buttons(self, tools: list[ToolDefinition]) -> None:
        """Render navigation buttons for a list of tools.
        
        Args:
            tools: List of ToolDefinition instances to render
        """
        for tool in tools:
            # Determine if button is active
            is_active = st.session_state[self._session_key] == tool.key
            
            # Render button with label only (no icon)
            button_label = tool.label
            button_type = "primary" if is_active else "secondary"
            
            if st.button(
                button_label,
                key=f"nav_btn_{tool.key}",
                use_container_width=True,
                type=button_type,
                help=tool.description
            ):
                st.session_state[self._session_key] = tool.key
                logger.info(f"User navigated to tool: {tool.key}")
                st.rerun()
    
    def get_active_tool(self) -> Optional[ToolDefinition]:
        """Get the currently active tool.
        
        Returns:
            ToolDefinition of active tool, or None if no tool is active
        """
        active_key = st.session_state.get(self._session_key)
        
        if not active_key:
            return None
        
        # Find tool by key
        for tool in self.tools:
            if tool.key == active_key:
                return tool
        
        logger.warning(f"Active tool key '{active_key}' not found in registered tools")
        return None
    
    def render_active_tool(self) -> None:
        """Render the currently active tool's content.
        
        If no tool is active or tool not found, displays an error message.
        """
        active_tool = self.get_active_tool()
        
        if not active_tool:
            st.error("No tool selected or tool not found")
            logger.error("No active tool to render")
            return
        
        # Render the tool using its render function
        try:
            logger.debug(f"Rendering tool: {active_tool.key}")
            active_tool.render_func()
        except Exception as e:
            logger.exception(f"Error rendering tool {active_tool.key}: {e}")
            st.error(f"Error rendering {active_tool.label}: {str(e)}")
    
    def render(self) -> None:
        """Main render method - displays sidebar and active tool content.
        
        Call this method once in your main application to render the entire
        navigation system.
        """
        # Render sidebar navigation
        self.render_sidebar()
        
        # Render active tool content in main area
        self.render_active_tool()
