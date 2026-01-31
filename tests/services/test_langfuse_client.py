"""Tests for Langfuse API client.

This module provides comprehensive unit tests for the LangfuseClient,
testing trace retrieval, summary statistics, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

from src.services.langfuse_client import (
    LangfuseClient,
    TraceSummary,
    TraceInfo,
    TraceDetails,
)


class TestLangfuseClientInitialization:
    """Tests for LangfuseClient initialization."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_initialization_with_enabled_config(self, mock_get_config):
        """Test client initialization with Langfuse enabled."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        
        assert client.host == "http://langfuse:3000"
        assert client.public_key == "pk-test"
        assert client.secret_key == "sk-test"
        assert client.enabled is True
    
    @patch("src.services.langfuse_client.get_config")
    def test_initialization_with_disabled_config(self, mock_get_config):
        """Test client initialization with Langfuse disabled."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = False
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        
        assert client.enabled is False
    
    @patch("src.services.langfuse_client.get_config")
    def test_host_trailing_slash_removed(self, mock_get_config):
        """Test that trailing slash is removed from host."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000/"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        
        assert client.host == "http://langfuse:3000"


class TestLangfuseClientHealthCheck:
    """Tests for health check functionality."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_is_healthy_when_disabled(self, mock_get_config):
        """Test health check returns False when disabled."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = False
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        
        assert client.is_healthy() is False
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_is_healthy_when_service_responds(self, mock_get, mock_get_config):
        """Test health check returns True when service responds."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        mock_response = Mock()
        mock_response.ok = True
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        
        assert client.is_healthy() is True
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_is_healthy_handles_connection_error(self, mock_get, mock_get_config):
        """Test health check handles connection errors gracefully."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        client = LangfuseClient()
        
        assert client.is_healthy() is False


class TestTraceSummary:
    """Tests for get_trace_summary functionality."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_get_trace_summary_when_disabled(self, mock_get_config):
        """Test trace summary returns empty when disabled."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = False
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        summary = client.get_trace_summary("24h")
        
        assert summary.total_traces == 0
        assert summary.traces_24h == 0
        assert summary.time_range == "24h"
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_trace_summary_with_traces(self, mock_get, mock_get_config):
        """Test trace summary calculation with actual traces."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        now = datetime.utcnow()
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "trace-1",
                    "timestamp": now.isoformat() + "Z",
                    "latency": 1500,
                    "status": "success",
                },
                {
                    "id": "trace-2",
                    "timestamp": now.isoformat() + "Z",
                    "latency": 2000,
                    "status": "success",
                },
                {
                    "id": "trace-3",
                    "timestamp": now.isoformat() + "Z",
                    "latency": 1000,
                    "status": "error",
                },
            ]
        }
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        summary = client.get_trace_summary("24h")
        
        assert summary.total_traces == 3
        assert summary.traces_24h == 3
        assert summary.avg_latency_ms == 1500.0  # (1500 + 2000 + 1000) / 3
        assert summary.error_rate == pytest.approx(33.33, rel=0.1)  # 1/3 errors
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_trace_summary_with_empty_response(self, mock_get, mock_get_config):
        """Test trace summary with no traces."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        summary = client.get_trace_summary("7d")
        
        assert summary.total_traces == 0
        assert summary.avg_latency_ms == 0.0
        assert summary.error_rate == 0.0
        assert summary.time_range == "7d"
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_trace_summary_handles_api_error(self, mock_get, mock_get_config):
        """Test trace summary handles API errors gracefully."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        summary = client.get_trace_summary("24h")
        
        assert summary.total_traces == 0


class TestRecentTraces:
    """Tests for get_recent_traces functionality."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_get_recent_traces_when_disabled(self, mock_get_config):
        """Test recent traces returns empty list when disabled."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = False
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        traces = client.get_recent_traces(limit=20)
        
        assert traces == []
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_recent_traces_returns_trace_info(self, mock_get, mock_get_config):
        """Test recent traces returns TraceInfo objects."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        now = datetime.utcnow()
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "trace-1",
                    "name": "Chat Query",
                    "timestamp": now.isoformat() + "Z",
                    "latency": 2100,
                    "status": "success",
                    "inputTokens": 245,
                    "outputTokens": 89,
                    "metadata": {"model": "gpt-4"},
                }
            ]
        }
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        traces = client.get_recent_traces(limit=20)
        
        assert len(traces) == 1
        assert isinstance(traces[0], TraceInfo)
        assert traces[0].trace_id == "trace-1"
        assert traces[0].name == "Chat Query"
        assert traces[0].duration_ms == 2100
        assert traces[0].status == "success"
        assert traces[0].input_tokens == 245
        assert traces[0].output_tokens == 89
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_recent_traces_with_status_filter_success(self, mock_get, mock_get_config):
        """Test recent traces filters by success status."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        now = datetime.utcnow()
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "name": "t1", "timestamp": now.isoformat() + "Z", "status": "success"},
                {"id": "2", "name": "t2", "timestamp": now.isoformat() + "Z", "status": "error"},
                {"id": "3", "name": "t3", "timestamp": now.isoformat() + "Z", "status": "success"},
            ]
        }
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        traces = client.get_recent_traces(limit=20, status_filter="success")
        
        assert len(traces) == 2
        assert all(t.status == "success" for t in traces)
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_recent_traces_with_status_filter_error(self, mock_get, mock_get_config):
        """Test recent traces filters by error status."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        now = datetime.utcnow()
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "name": "t1", "timestamp": now.isoformat() + "Z", "status": "success"},
                {"id": "2", "name": "t2", "timestamp": now.isoformat() + "Z", "status": "error"},
            ]
        }
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        traces = client.get_recent_traces(limit=20, status_filter="error")
        
        assert len(traces) == 1
        assert traces[0].status == "error"
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_recent_traces_clamps_limit(self, mock_get, mock_get_config):
        """Test recent traces clamps limit to valid range."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        
        # Test with limit > 100
        client.get_recent_traces(limit=200)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 100
        
        # Test with limit < 1
        mock_get.reset_mock()
        client.get_recent_traces(limit=0)
        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 1


class TestTraceDetails:
    """Tests for get_trace_details functionality."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_get_trace_details_when_disabled(self, mock_get_config):
        """Test trace details returns None when disabled."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = False
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        details = client.get_trace_details("trace-123")
        
        assert details is None
    
    @patch("src.services.langfuse_client.get_config")
    def test_get_trace_details_with_empty_trace_id(self, mock_get_config):
        """Test trace details returns None for empty trace_id."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        details = client.get_trace_details("")
        
        assert details is None
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_trace_details_returns_details(self, mock_get, mock_get_config):
        """Test trace details returns TraceDetails object."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        now = datetime.utcnow()
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "trace-123",
            "name": "Chat Query",
            "timestamp": now.isoformat() + "Z",
            "latency": 2500,
            "status": "success",
            "inputTokens": 100,
            "outputTokens": 50,
            "metadata": {"user": "test"},
            "observations": [
                {
                    "id": "span-1",
                    "name": "LLM Call",
                    "type": "generation",
                    "latency": 2000,
                    "model": "gpt-4",
                }
            ],
        }
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        details = client.get_trace_details("trace-123")
        
        assert details is not None
        assert isinstance(details, TraceDetails)
        assert details.trace.trace_id == "trace-123"
        assert details.trace.name == "Chat Query"
        assert details.token_usage["input"] == 100
        assert details.token_usage["output"] == 50
        assert details.token_usage["total"] == 150
        assert len(details.spans) == 1
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_trace_details_not_found(self, mock_get, mock_get_config):
        """Test trace details returns None for non-existent trace."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        details = client.get_trace_details("nonexistent-trace")
        
        assert details is None
    
    @patch("src.services.langfuse_client.get_config")
    @patch("requests.Session.get")
    def test_get_trace_details_with_error_status(self, mock_get, mock_get_config):
        """Test trace details extracts error message for failed traces."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = "pk-test"
        mock_config.langfuse.secret_key = "sk-test"
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        now = datetime.utcnow()
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "trace-error",
            "name": "Failed Query",
            "timestamp": now.isoformat() + "Z",
            "status": "error",
            "error": "Connection timeout",
            "observations": [],
        }
        mock_get.return_value = mock_response
        
        client = LangfuseClient()
        details = client.get_trace_details("trace-error")
        
        assert details is not None
        assert details.trace.status == "error"
        assert details.error_message == "Connection timeout"


class TestTimestampParsing:
    """Tests for timestamp parsing functionality."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_parse_timestamp_with_z_suffix(self, mock_get_config):
        """Test parsing timestamp with Z suffix."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        result = client._parse_timestamp("2024-01-15T10:30:00Z")
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    @patch("src.services.langfuse_client.get_config")
    def test_parse_timestamp_with_none(self, mock_get_config):
        """Test parsing None timestamp returns current time."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        before = datetime.utcnow()
        result = client._parse_timestamp(None)
        after = datetime.utcnow()
        
        assert before <= result <= after
    
    @patch("src.services.langfuse_client.get_config")
    def test_parse_timestamp_with_invalid_format(self, mock_get_config):
        """Test parsing invalid timestamp returns current time."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        result = client._parse_timestamp("not-a-date")
        
        assert isinstance(result, datetime)


class TestGetFullDashboardUrl:
    """Tests for get_full_dashboard_url functionality."""
    
    @patch("src.services.langfuse_client.get_config")
    def test_get_full_dashboard_url(self, mock_get_config):
        """Test getting full dashboard URL."""
        mock_config = Mock()
        mock_config.langfuse.host = "http://langfuse:3000"
        mock_config.langfuse.public_key = ""
        mock_config.langfuse.secret_key = ""
        mock_config.langfuse.timeout = 30
        mock_config.langfuse.enabled = True
        mock_get_config.return_value = mock_config
        
        client = LangfuseClient()
        url = client.get_full_dashboard_url()
        
        assert url == "http://langfuse:3000"
