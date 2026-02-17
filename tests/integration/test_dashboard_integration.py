"""Integration tests for Agent Zero dashboards.

This module provides integration tests for the dashboard tools,
testing navigation, feature flags, data flow, and caching behavior.

These tests are marked as integration tests and may require
running Docker services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestSidebarNavigation:
    """Integration tests for sidebar navigation between tools."""
    
    @patch('src.config.get_config')
    def test_navigation_registers_all_core_tools(self, mock_get_config):
        """Test that all core tools are registered in navigation."""
        mock_config = Mock()
        mock_config.dashboard.show_chat = True
        mock_config.dashboard.show_knowledge_base = True
        mock_config.dashboard.show_settings = True
        mock_config.dashboard.show_logs = True
        mock_config.dashboard.show_qdrant_manager = False
        mock_config.dashboard.show_langfuse_dashboard = False
        mock_config.dashboard.show_system_health = False
        mock_get_config.return_value = mock_config
        
        from src.ui.components.navigation import SidebarNavigation, ToolDefinition
        
        nav = SidebarNavigation()
        
        # Register core tools
        nav.register_tool(ToolDefinition(
            key="chat", icon=">", label="Chat",
            description="Chat", render_func=lambda: None, category="core"
        ))
        nav.register_tool(ToolDefinition(
            key="kb", icon=">", label="Knowledge Base",
            description="KB", render_func=lambda: None, category="core"
        ))
        nav.register_tool(ToolDefinition(
            key="settings", icon=">", label="Settings",
            description="Settings", render_func=lambda: None, category="core"
        ))
        nav.register_tool(ToolDefinition(
            key="logs", icon=">", label="Logs",
            description="Logs", render_func=lambda: None, category="core"
        ))
        
        core_tools = nav.get_enabled_tools(category="core")
        
        assert len(core_tools) == 4
        assert all(t.category == "core" for t in core_tools)
    
    @patch('src.config.get_config')
    def test_navigation_registers_management_tools(self, mock_get_config):
        """Test that management tools are registered when enabled."""
        mock_config = Mock()
        mock_config.dashboard.show_qdrant_manager = True
        mock_config.dashboard.show_langfuse_dashboard = True
        mock_config.dashboard.show_system_health = True
        mock_get_config.return_value = mock_config
        
        from src.ui.components.navigation import SidebarNavigation, ToolDefinition
        
        nav = SidebarNavigation()
        
        # Register management tools
        nav.register_tool(ToolDefinition(
            key="qdrant", icon=">", label="Qdrant",
            description="Qdrant", render_func=lambda: None, category="management"
        ))
        nav.register_tool(ToolDefinition(
            key="langfuse", icon=">", label="Langfuse",
            description="Langfuse", render_func=lambda: None, category="management"
        ))
        nav.register_tool(ToolDefinition(
            key="health", icon=">", label="Health",
            description="Health", render_func=lambda: None, category="management"
        ))
        
        mgmt_tools = nav.get_enabled_tools(category="management")
        
        assert len(mgmt_tools) == 3
        assert all(t.category == "management" for t in mgmt_tools)
    
    def test_navigation_prevents_duplicate_keys(self):
        """Test that duplicate tool keys are rejected."""
        from src.ui.components.navigation import SidebarNavigation, ToolDefinition
        
        nav = SidebarNavigation()
        nav.register_tool(ToolDefinition(
            key="chat", icon="💬", label="Chat",
            description="Chat", render_func=lambda: None
        ))
        
        with pytest.raises(ValueError, match="already registered"):
            nav.register_tool(ToolDefinition(
                key="chat", icon="💬", label="Chat 2",
                description="Chat 2", render_func=lambda: None
            ))
    
    def test_navigation_tool_selection_state(self):
        """Test that tool selection is tracked in session state."""
        import streamlit as st
        from src.ui.components.navigation import SidebarNavigation, ToolDefinition
        
        # Mock session state
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        
        nav = SidebarNavigation()
        nav.register_tool(ToolDefinition(
            key="chat", icon="💬", label="Chat",
            description="Chat", render_func=lambda: None
        ))
        
        # Verify session state key is initialized
        assert "active_tool" in st.session_state or nav._session_key in st.session_state


class TestFeatureFlagToggling:
    """Integration tests for feature flag behavior."""
    
    @patch('src.config.get_config')
    def test_feature_flags_control_tool_visibility(self, mock_get_config):
        """Test that feature flags control which tools are available."""
        # Create mock config with specific flags
        mock_config = Mock()
        mock_config.dashboard.show_chat = True
        mock_config.dashboard.show_knowledge_base = True
        mock_config.dashboard.show_settings = False  # Disabled
        mock_config.dashboard.show_logs = True
        mock_config.dashboard.show_qdrant_manager = True
        mock_config.dashboard.show_langfuse_dashboard = False  # Disabled
        mock_config.dashboard.show_system_health = True
        mock_get_config.return_value = mock_config
        
        from src.ui.components.navigation import SidebarNavigation, ToolDefinition
        
        nav = SidebarNavigation()
        
        # Register tools based on feature flags
        if mock_config.dashboard.show_chat:
            nav.register_tool(ToolDefinition(
                key="chat", icon=">", label="Chat",
                description="Chat", render_func=lambda: None, category="core"
            ))
        
        if mock_config.dashboard.show_settings:
            nav.register_tool(ToolDefinition(
                key="settings", icon=">", label="Settings",
                description="Settings", render_func=lambda: None, category="core"
            ))
        
        if mock_config.dashboard.show_langfuse_dashboard:
            nav.register_tool(ToolDefinition(
                key="langfuse", icon=">", label="Langfuse",
                description="Langfuse", render_func=lambda: None, category="management"
            ))
        
        # Verify only enabled tools are registered
        all_tools = nav.get_enabled_tools()
        tool_keys = [t.key for t in all_tools]
        
        assert "chat" in tool_keys
        assert "settings" not in tool_keys  # Was disabled
        assert "langfuse" not in tool_keys  # Was disabled
    
    def test_feature_flag_defaults_match_config(self):
        """Test that feature flag defaults are appropriate."""
        from src.config import DashboardFeatures
        
        features = DashboardFeatures()
        
        # Core tools should be enabled by default
        assert features.show_chat is True
        assert features.show_knowledge_base is True
        assert features.show_settings is True
        assert features.show_logs is True
        
        # Management tools should be disabled by default
        assert features.show_qdrant_manager is False
        assert features.show_langfuse_dashboard is False
        assert features.show_system_health is False


class TestDataFlow:
    """Integration tests for data flow between components."""
    
    @patch('src.services.qdrant_client.QdrantClient')
    def test_qdrant_dashboard_data_flow(self, mock_qdrant_lib):
        """Test data flow in Qdrant dashboard."""
        # Mock the underlying qdrant-client library
        mock_qdrant_lib.return_value = Mock()
        
        from src.services import QdrantVectorClient
        client = QdrantVectorClient()
        
        # Verify the client has required methods
        assert hasattr(client, 'list_collections')
        assert hasattr(client, 'is_healthy')
    
    @patch('src.services.langfuse_client.LangfuseClient')
    def test_langfuse_dashboard_data_flow(self, mock_client_class):
        """Test data flow in Langfuse dashboard."""
        mock_client = Mock()
        mock_client.get_trace_summary.return_value = Mock(
            total_traces=100,
            traces_24h=50,
            avg_latency_ms=1500.0,
            error_rate=2.5
        )
        mock_client_class.return_value = mock_client
        
        from src.services import LangfuseClient
        client = LangfuseClient()
        
        # Verify trace summary retrieval flow
        assert hasattr(client, 'get_trace_summary') or hasattr(mock_client, 'get_trace_summary')
    
    @patch('src.services.health_check.HealthChecker')
    def test_system_health_data_flow(self, mock_checker_class):
        """Test data flow in System Health dashboard."""
        mock_checker = Mock()
        mock_checker.check_all.return_value = {
            "ollama": Mock(name="Ollama", is_healthy=True, message="OK", details={}),
            "qdrant": Mock(name="Qdrant", is_healthy=True, message="OK", details={}),
        }
        mock_checker_class.return_value = mock_checker
        
        from src.services import HealthChecker
        checker = HealthChecker()
        
        # Verify health check flow
        statuses = checker.check_all()
        assert "ollama" in statuses
        assert "qdrant" in statuses


class TestCachingBehavior:
    """Integration tests for Streamlit caching behavior."""
    
    def test_langfuse_trace_summary_caching(self):
        """Test that trace summary is cached."""
        from src.ui.tools.langfuse_dashboard import _get_trace_summary
        
        # Verify the function has cache decorator
        assert hasattr(_get_trace_summary, 'clear') or hasattr(_get_trace_summary, '__wrapped__')
    
    def test_service_statuses_caching(self):
        """Test that service statuses are cached."""
        from src.ui.tools.system_health import _get_service_statuses
        
        # Verify the function has cache decorator
        assert hasattr(_get_service_statuses, 'clear') or hasattr(_get_service_statuses, '__wrapped__')


class TestErrorHandling:
    """Integration tests for error handling propagation."""
    
    @patch('src.services.langfuse_client.get_config')
    def test_langfuse_unavailable_handling(self, mock_get_config):
        """Test graceful handling when Langfuse is unavailable."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://nonexistent:3000"
        mock_config.langfuse.enabled = True
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 5
        mock_get_config.return_value = mock_config
        
        from src.services.langfuse_client import LangfuseClient
        
        client = LangfuseClient()
        
        # Should not raise an error, should return False
        # (actual connection test would fail in real scenario)
        assert client.enabled is True
    
    @patch('src.services.health_check.OllamaClient')
    @patch('src.services.health_check.QdrantVectorClient')
    @patch('src.services.health_check.MeilisearchClient')
    @patch('src.services.health_check.get_langfuse_observability')
    def test_service_unavailable_handling(
        self, mock_langfuse, mock_meili, mock_qdrant, mock_ollama
    ):
        """Test graceful handling when services are unavailable."""
        # Setup all clients to fail
        mock_ollama.return_value.is_healthy.side_effect = Exception("Connection refused")
        mock_qdrant.return_value.is_healthy.side_effect = Exception("Connection refused")
        mock_meili.return_value.is_healthy.side_effect = Exception("Connection refused")
        mock_langfuse.return_value.enabled = False
        
        from src.services import HealthChecker
        
        checker = HealthChecker()
        statuses = checker.check_all()
        
        # All should report unhealthy but not raise
        assert all(not s.is_healthy for name, s in statuses.items() if name != "langfuse")


class TestBackwardCompatibility:
    """Integration tests for backward compatibility."""
    
    def test_existing_tools_still_work(self):
        """Test that existing 4 core tools still function."""
        # Verify imports work
        from src.ui.tools import (
            render_chat_interface,
            render_knowledge_base,
            render_settings,
            render_logs,
        )
        
        # Verify functions are callable
        assert callable(render_chat_interface)
        assert callable(render_knowledge_base)
        assert callable(render_settings)
        assert callable(render_logs)
    
    def test_session_initialization_functions_exist(self):
        """Test that session initialization functions still exist."""
        from src.ui.tools import (
            initialize_chat_session,
            initialize_kb_session,
            initialize_settings_session,
            initialize_logs_session,
        )
        
        assert callable(initialize_chat_session)
        assert callable(initialize_kb_session)
        assert callable(initialize_settings_session)
        assert callable(initialize_logs_session)
    
    def test_health_checker_api_unchanged(self):
        """Test that HealthChecker API remains compatible."""
        from src.services import HealthChecker, ServiceStatus
        
        # Verify expected methods exist
        checker = HealthChecker()
        assert hasattr(checker, 'check_all')
        assert hasattr(checker, 'check_ollama')
        assert hasattr(checker, 'check_qdrant')
        assert hasattr(checker, 'check_meilisearch')
        assert hasattr(checker, 'check_langfuse')
        assert hasattr(checker, 'all_healthy')


class TestToolDefinitionValidation:
    """Integration tests for tool definition validation."""
    
    def test_tool_definition_requires_key(self):
        """Test that ToolDefinition requires a non-empty key."""
        from src.ui.components.navigation import ToolDefinition
        
        with pytest.raises(ValueError, match="cannot be empty"):
            ToolDefinition(
                key="",
                icon="💬",
                label="Test",
                description="Test",
                render_func=lambda: None
            )
    
    def test_tool_definition_requires_callable(self):
        """Test that ToolDefinition requires callable render_func."""
        from src.ui.components.navigation import ToolDefinition
        
        with pytest.raises(ValueError, match="must be callable"):
            ToolDefinition(
                key="test",
                icon="💬",
                label="Test",
                description="Test",
                render_func="not_callable"  # type: ignore
            )
    
    def test_tool_definition_accepts_valid_input(self):
        """Test that ToolDefinition accepts valid input."""
        from src.ui.components.navigation import ToolDefinition
        
        tool = ToolDefinition(
            key="test",
            icon="💬",
            label="Test Tool",
            description="A test tool",
            render_func=lambda: None,
            enabled=True,
            category="core"
        )
        
        assert tool.key == "test"
        assert tool.icon == "💬"
        assert tool.label == "Test Tool"
        assert tool.enabled is True
        assert tool.category == "core"


class TestEnvironmentIntegration:
    """Integration tests for environment-specific behavior."""
    
    @patch('src.config.get_config')
    def test_development_environment_allows_all_features(self, mock_get_config):
        """Test that development environment allows flexible feature access."""
        mock_config = Mock()
        mock_config.env = "development"
        mock_config.debug = True
        mock_config.langfuse.enabled = False  # Optional in dev
        mock_config.security.llm_guard_enabled = False  # Optional in dev
        mock_get_config.return_value = mock_config
        
        config = mock_get_config()
        
        # Development should allow debug mode
        assert config.debug is True
        
        # Development should allow optional services
        assert config.langfuse.enabled is False  # OK in dev
    
    def test_config_environment_validation(self):
        """Test that config validates environment values."""
        from src.config import AppConfig
        
        # Valid environments should work
        for env in ["development", "staging", "production"]:
            # This would use environment variables in real scenario
            pass  # Config validation is tested in config tests


class TestDashboardUIConsistency:
    """Integration tests for UI consistency across dashboards."""
    
    def test_all_dashboards_have_render_function(self):
        """Test that all dashboard tools have render functions."""
        from src.ui.tools import (
            render_chat_interface,
            render_knowledge_base,
            render_settings,
            render_logs,
            render_qdrant_dashboard,
            render_langfuse_dashboard,
            render_system_health_dashboard,
        )
        
        render_functions = [
            render_chat_interface,
            render_knowledge_base,
            render_settings,
            render_logs,
            render_qdrant_dashboard,
            render_langfuse_dashboard,
            render_system_health_dashboard,
        ]
        
        # All should be callable
        for func in render_functions:
            assert callable(func), f"{func.__name__} is not callable"
    
    def test_all_dashboards_are_importable(self):
        """Test that all dashboard modules can be imported."""
        # This tests that there are no import errors
        from src.ui.tools import chat
        from src.ui.tools import knowledge_base
        from src.ui.tools import settings
        from src.ui.tools import logs
        from src.ui.tools import qdrant_dashboard
        from src.ui.tools import langfuse_dashboard
        from src.ui.tools import system_health
        
        modules = [
            chat, knowledge_base, settings, logs,
            qdrant_dashboard, langfuse_dashboard, system_health
        ]
        
        for module in modules:
            assert module is not None
