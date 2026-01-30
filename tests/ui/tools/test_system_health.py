"""Tests for System Health dashboard functionality.

This module provides unit tests for the system health dashboard,
testing service status display, resource metrics, and UI rendering.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import platform


class TestGetSystemInfo:
    """Tests for system info functionality."""
    
    @patch('platform.system', return_value="Linux")
    @patch('platform.version', return_value="5.4.0-generic")
    @patch('platform.machine', return_value="x86_64")
    @patch('platform.python_version', return_value="3.11.5")
    @patch('platform.node', return_value="test-host")
    def test_get_system_info(self, mock_node, mock_python, mock_machine, mock_version, mock_system):
        """Test getting system information."""
        from src.ui.tools.system_health import _get_system_info
        
        info = _get_system_info()
        
        assert info["platform"] == "Linux"
        assert info["platform_version"] == "5.4.0-generic"
        assert info["architecture"] == "x86_64"
        assert info["python_version"] == "3.11.5"
        assert info["hostname"] == "test-host"


class TestStatusHelpers:
    """Tests for status helper functions."""
    
    def test_get_status_icon_healthy(self):
        """Test status icon for healthy service."""
        from src.ui.tools.system_health import _get_status_icon
        
        assert _get_status_icon(True) == "🟢"
    
    def test_get_status_icon_unhealthy(self):
        """Test status icon for unhealthy service."""
        from src.ui.tools.system_health import _get_status_icon
        
        assert _get_status_icon(False) == "🔴"
    
    def test_get_status_color_healthy(self):
        """Test status color for healthy service."""
        from src.ui.tools.system_health import _get_status_color
        
        assert _get_status_color(True) == "green"
    
    def test_get_status_color_unhealthy(self):
        """Test status color for unhealthy service."""
        from src.ui.tools.system_health import _get_status_color
        
        assert _get_status_color(False) == "red"


class TestResourceMetricsWithoutPsutil:
    """Tests for resource metrics when psutil is not available."""
    
    def test_get_resource_metrics_returns_unavailable(self):
        """Test resource metrics returns unavailable when psutil not present."""
        with patch('src.ui.tools.system_health.PSUTIL_AVAILABLE', False):
            from src.ui.tools.system_health import _get_resource_metrics
            
            metrics = _get_resource_metrics()
            
            assert metrics["available"] is False
            assert metrics["cpu_percent"] == 0.0
            assert metrics["memory_percent"] == 0.0
            assert metrics["disk_percent"] == 0.0


class TestResourceMetricsWithPsutil:
    """Tests for resource metrics when psutil is available."""
    
    def test_get_resource_metrics_success(self):
        """Test resource metrics returns correct values when psutil is available."""
        import sys
        
        # Create a mock psutil module
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 45.5
        
        mock_memory = Mock()
        mock_memory.percent = 62.3
        mock_memory.total = 16 * 1024 ** 3  # 16 GB
        mock_memory.used = 10 * 1024 ** 3   # 10 GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.percent = 34.2
        mock_disk.total = 500 * 1024 ** 3   # 500 GB
        mock_disk.used = 171 * 1024 ** 3    # 171 GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        # Patch psutil in sys.modules and the availability flag
        with patch.dict(sys.modules, {'psutil': mock_psutil}):
            with patch('src.ui.tools.system_health.PSUTIL_AVAILABLE', True):
                # Import the module and inject the mock psutil
                import src.ui.tools.system_health as health_module
                original_psutil = getattr(health_module, 'psutil', None)
                health_module.psutil = mock_psutil
                
                try:
                    metrics = health_module._get_resource_metrics()
                    
                    assert metrics["available"] is True
                    assert metrics["cpu_percent"] == 45.5
                    assert metrics["memory_percent"] == 62.3
                    assert metrics["disk_percent"] == 34.2
                finally:
                    # Restore original
                    if original_psutil is not None:
                        health_module.psutil = original_psutil
    
    def test_get_resource_metrics_handles_error(self):
        """Test resource metrics handles errors gracefully."""
        import sys
        
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.side_effect = Exception("Permission denied")
        
        with patch.dict(sys.modules, {'psutil': mock_psutil}):
            with patch('src.ui.tools.system_health.PSUTIL_AVAILABLE', True):
                import src.ui.tools.system_health as health_module
                original_psutil = getattr(health_module, 'psutil', None)
                health_module.psutil = mock_psutil
                
                try:
                    metrics = health_module._get_resource_metrics()
                    
                    assert metrics["available"] is False
                finally:
                    if original_psutil is not None:
                        health_module.psutil = original_psutil


class TestServiceStatusRetrieval:
    """Tests for service status retrieval."""
    
    @patch('src.ui.tools.system_health.HealthChecker')
    def test_get_service_statuses_all_healthy(self, mock_checker_class):
        """Test getting service statuses when all are healthy."""
        mock_checker = Mock()
        mock_ollama_status = Mock()
        mock_ollama_status.name = "Ollama"
        mock_ollama_status.is_healthy = True
        mock_ollama_status.message = "Service operational"
        mock_ollama_status.details = {"models": 2}
        
        mock_qdrant_status = Mock()
        mock_qdrant_status.name = "Qdrant"
        mock_qdrant_status.is_healthy = True
        mock_qdrant_status.message = "Vector DB ready"
        mock_qdrant_status.details = {}
        
        mock_checker.check_all.return_value = {
            "ollama": mock_ollama_status,
            "qdrant": mock_qdrant_status,
        }
        mock_checker_class.return_value = mock_checker
        
        # Import and clear cache
        from src.ui.tools.system_health import _get_service_statuses
        if hasattr(_get_service_statuses, 'clear'):
            _get_service_statuses.clear()
        
        statuses = _get_service_statuses()
        
        assert len(statuses) == 2
        assert statuses["ollama"]["is_healthy"] is True
        assert statuses["qdrant"]["is_healthy"] is True
    
    @patch('src.ui.tools.system_health.HealthChecker')
    def test_get_service_statuses_with_unhealthy(self, mock_checker_class):
        """Test getting service statuses with unhealthy service."""
        mock_checker = Mock()
        mock_ollama_status = Mock()
        mock_ollama_status.name = "Ollama"
        mock_ollama_status.is_healthy = True
        mock_ollama_status.message = "Service operational"
        mock_ollama_status.details = {}
        
        mock_langfuse_status = Mock()
        mock_langfuse_status.name = "Langfuse"
        mock_langfuse_status.is_healthy = False
        mock_langfuse_status.message = "Connection failed"
        mock_langfuse_status.details = {"enabled": True}
        
        mock_checker.check_all.return_value = {
            "ollama": mock_ollama_status,
            "langfuse": mock_langfuse_status,
        }
        mock_checker_class.return_value = mock_checker
        
        from src.ui.tools.system_health import _get_service_statuses
        if hasattr(_get_service_statuses, 'clear'):
            _get_service_statuses.clear()
        
        statuses = _get_service_statuses()
        
        assert statuses["ollama"]["is_healthy"] is True
        assert statuses["langfuse"]["is_healthy"] is False
        assert statuses["langfuse"]["message"] == "Connection failed"


class TestHealthChecker:
    """Tests for health checker functionality in system health context."""
    
    def test_health_checker_initialization(self):
        """Test health checker can be created."""
        from src.services import HealthChecker
        
        # Should not raise an error (clients are lazy-loaded)
        checker = HealthChecker()
        assert checker is not None
    
    @patch('src.services.health_check.OllamaClient')
    @patch('src.services.health_check.QdrantVectorClient')
    @patch('src.services.health_check.MeilisearchClient')
    @patch('src.services.health_check.get_langfuse_observability')
    def test_check_all_returns_all_services(
        self, 
        mock_langfuse,
        mock_meili_class, 
        mock_qdrant_class, 
        mock_ollama_class
    ):
        """Test check_all returns status for all services."""
        # Setup mocks
        mock_ollama = Mock()
        mock_ollama.is_healthy.return_value = True
        mock_ollama.list_models.return_value = ["model1"]
        mock_ollama_class.return_value = mock_ollama
        
        mock_qdrant = Mock()
        mock_qdrant.is_healthy.return_value = True
        mock_qdrant_class.return_value = mock_qdrant
        
        mock_meili = Mock()
        mock_meili.is_healthy.return_value = True
        mock_meili.list_indexes.return_value = []
        mock_meili_class.return_value = mock_meili
        
        mock_obs = Mock()
        mock_obs.enabled = False
        mock_langfuse.return_value = mock_obs
        
        from src.services import HealthChecker
        
        checker = HealthChecker()
        statuses = checker.check_all()
        
        assert "ollama" in statuses
        assert "qdrant" in statuses
        assert "meilisearch" in statuses
        assert "langfuse" in statuses


class TestServiceStatusDataclass:
    """Tests for ServiceStatus dataclass."""
    
    def test_service_status_creation(self):
        """Test creating a ServiceStatus."""
        from src.services import ServiceStatus
        
        status = ServiceStatus(
            name="TestService",
            is_healthy=True,
            message="All good",
        )
        
        assert status.name == "TestService"
        assert status.is_healthy is True
        assert status.message == "All good"
        assert status.details == {}
    
    def test_service_status_with_details(self):
        """Test creating a ServiceStatus with details."""
        from src.services import ServiceStatus
        
        status = ServiceStatus(
            name="Ollama",
            is_healthy=True,
            message="Operational",
            details={"models_available": 3},
        )
        
        assert status.details == {"models_available": 3}
    
    def test_service_status_unhealthy(self):
        """Test creating an unhealthy ServiceStatus."""
        from src.services import ServiceStatus
        
        status = ServiceStatus(
            name="Qdrant",
            is_healthy=False,
            message="Connection refused",
        )
        
        assert status.is_healthy is False
        assert "refused" in status.message
