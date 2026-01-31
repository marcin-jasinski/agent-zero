"""Unit tests for navigation component (Phase 4b Step 17).

Tests the SidebarNavigation and ToolDefinition classes for proper
registration, rendering, and feature flag handling.

Design Reference: DASHBOARD_DESIGN.md § "Sidebar Navigation Structure"
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.navigation import SidebarNavigation, ToolDefinition


class TestToolDefinition:
    """Test suite for ToolDefinition dataclass."""
    
    def test_tool_definition_creation(self):
        """Test creating a valid ToolDefinition."""
        def mock_render():
            pass
        
        tool = ToolDefinition(
            key="test_tool",
            icon="🔧",
            label="Test Tool",
            description="A test tool",
            render_func=mock_render,
            enabled=True,
            category="core"
        )
        
        assert tool.key == "test_tool"
        assert tool.icon == "🔧"
        assert tool.label == "Test Tool"
        assert tool.description == "A test tool"
        assert tool.render_func == mock_render
        assert tool.enabled is True
        assert tool.category == "core"
    
    def test_tool_definition_empty_key_raises_error(self):
        """Test that empty key raises ValueError."""
        def mock_render():
            pass
        
        with pytest.raises(ValueError, match="Tool key cannot be empty"):
            ToolDefinition(
                key="",
                icon="🔧",
                label="Test",
                description="Test",
                render_func=mock_render
            )
    
    def test_tool_definition_non_callable_render_func_raises_error(self):
        """Test that non-callable render_func raises ValueError."""
        with pytest.raises(ValueError, match="render_func must be callable"):
            ToolDefinition(
                key="test",
                icon="🔧",
                label="Test",
                description="Test",
                render_func="not_callable"  # type: ignore
            )
    
    def test_tool_definition_default_values(self):
        """Test ToolDefinition with default values."""
        def mock_render():
            pass
        
        tool = ToolDefinition(
            key="test",
            icon="🔧",
            label="Test",
            description="Test",
            render_func=mock_render
        )
        
        # Check defaults
        assert tool.enabled is True
        assert tool.category == "core"


class TestSidebarNavigation:
    """Test suite for SidebarNavigation class."""
    
    @patch("src.ui.components.navigation.st")
    def test_navigation_initialization(self, mock_st):
        """Test SidebarNavigation initialization."""
        mock_st.session_state = {}
        
        nav = SidebarNavigation()
        
        assert nav.tools == []
        assert nav._session_key == "active_tool"
        assert "active_tool" in mock_st.session_state
    
    @patch("src.ui.components.navigation.st")
    def test_register_tool_success(self, mock_st):
        """Test successful tool registration."""
        mock_st.session_state = {}
        nav = SidebarNavigation()
        
        def mock_render():
            pass
        
        tool = ToolDefinition(
            key="chat",
            icon="💬",
            label="Chat",
            description="Chat interface",
            render_func=mock_render
        )
        
        nav.register_tool(tool)
        
        assert len(nav.tools) == 1
        assert nav.tools[0] == tool
    
    @patch("src.ui.components.navigation.st")
    def test_register_duplicate_key_raises_error(self, mock_st):
        """Test that registering duplicate key raises ValueError."""
        mock_st.session_state = {}
        nav = SidebarNavigation()
        
        def mock_render():
            pass
        
        tool1 = ToolDefinition(
            key="chat",
            icon="💬",
            label="Chat",
            description="Chat",
            render_func=mock_render
        )
        
        tool2 = ToolDefinition(
            key="chat",  # Duplicate
            icon="💬",
            label="Chat 2",
            description="Chat 2",
            render_func=mock_render
        )
        
        nav.register_tool(tool1)
        
        with pytest.raises(ValueError, match="Tool with key 'chat' already registered"):
            nav.register_tool(tool2)
    
    @patch("src.ui.components.navigation.st")
    def test_get_enabled_tools(self, mock_st):
        """Test getting enabled tools."""
        mock_st.session_state = {}
        nav = SidebarNavigation()
        
        def mock_render():
            pass
        
        # Register enabled and disabled tools
        nav.register_tool(ToolDefinition(
            key="chat",
            icon="💬",
            label="Chat",
            description="Chat",
            render_func=mock_render,
            enabled=True,
            category="core"
        ))
        
        nav.register_tool(ToolDefinition(
            key="qdrant",
            icon="🔍",
            label="Qdrant",
            description="Qdrant Manager",
            render_func=mock_render,
            enabled=False,  # Disabled
            category="management"
        ))
        
        nav.register_tool(ToolDefinition(
            key="health",
            icon="🏥",
            label="Health",
            description="Health Monitor",
            render_func=mock_render,
            enabled=True,
            category="management"
        ))
        
        # Get all enabled tools
        enabled_tools = nav.get_enabled_tools()
        assert len(enabled_tools) == 2
        assert all(t.enabled for t in enabled_tools)
        
        # Get enabled core tools only
        core_tools = nav.get_enabled_tools(category="core")
        assert len(core_tools) == 1
        assert core_tools[0].key == "chat"
        
        # Get enabled management tools only
        mgmt_tools = nav.get_enabled_tools(category="management")
        assert len(mgmt_tools) == 1
        assert mgmt_tools[0].key == "health"
    
    @patch("src.ui.components.navigation.st")
    def test_get_active_tool(self, mock_st):
        """Test getting active tool."""
        mock_st.session_state = {"active_tool": "chat"}
        nav = SidebarNavigation()
        
        def mock_render():
            pass
        
        chat_tool = ToolDefinition(
            key="chat",
            icon="💬",
            label="Chat",
            description="Chat",
            render_func=mock_render
        )
        
        nav.register_tool(chat_tool)
        
        active_tool = nav.get_active_tool()
        
        assert active_tool is not None
        assert active_tool.key == "chat"
    
    @patch("src.ui.components.navigation.st")
    def test_get_active_tool_not_found(self, mock_st):
        """Test getting active tool when key not found."""
        mock_st.session_state = {"active_tool": "nonexistent"}
        nav = SidebarNavigation()
        
        active_tool = nav.get_active_tool()
        
        assert active_tool is None
    
    @patch("src.ui.components.navigation.st")
    def test_render_active_tool_success(self, mock_st):
        """Test rendering active tool."""
        mock_render = Mock()
        mock_st.session_state = {"active_tool": "chat"}
        
        nav = SidebarNavigation()
        
        tool = ToolDefinition(
            key="chat",
            icon="💬",
            label="Chat",
            description="Chat",
            render_func=mock_render
        )
        
        nav.register_tool(tool)
        nav.render_active_tool()
        
        # Verify render function was called
        mock_render.assert_called_once()
    
    @patch("src.ui.components.navigation.st")
    def test_render_active_tool_no_tool_selected(self, mock_st):
        """Test rendering when no tool is selected."""
        mock_st.session_state = {"active_tool": None}
        mock_st.error = Mock()
        
        nav = SidebarNavigation()
        nav.render_active_tool()
        
        # Verify error message shown
        mock_st.error.assert_called_once()
    
    @patch("src.ui.components.navigation.st")
    def test_render_active_tool_error_handling(self, mock_st):
        """Test error handling when tool render fails."""
        def failing_render():
            raise RuntimeError("Render failed")
        
        mock_st.session_state = {"active_tool": "chat"}
        mock_st.error = Mock()
        
        nav = SidebarNavigation()
        
        tool = ToolDefinition(
            key="chat",
            icon="💬",
            label="Chat",
            description="Chat",
            render_func=failing_render
        )
        
        nav.register_tool(tool)
        nav.render_active_tool()
        
        # Verify error message shown
        mock_st.error.assert_called_once()
        assert "Error rendering Chat" in str(mock_st.error.call_args)
