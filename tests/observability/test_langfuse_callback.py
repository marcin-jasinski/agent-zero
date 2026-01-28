"""Tests for Langfuse Observability Integration.

Tests the LangfuseObservability class and its tracking methods.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.observability.langfuse_callback import (
    LangfuseObservability,
    get_langfuse_observability,
)


class TestLangfuseObservability:
    """Test suite for LangfuseObservability class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.langfuse.enabled = True
        config.langfuse.public_key = "test_public_key"
        config.langfuse.secret_key = "test_secret_key"
        config.langfuse.host = "http://localhost:3000"
        return config

    @pytest.fixture
    def mock_langfuse_client(self):
        """Mock Langfuse client."""
        return MagicMock()

    @pytest.fixture
    def observability_enabled(self, mock_config, mock_langfuse_client):
        """Create observability instance with mocked dependencies."""
        with patch("src.observability.langfuse_callback.get_config", return_value=mock_config):
            with patch("src.observability.langfuse_callback.Langfuse", return_value=mock_langfuse_client):
                obs = LangfuseObservability()
                obs.client = mock_langfuse_client
                obs.enabled = True
                return obs

    @pytest.fixture
    def observability_disabled(self, mock_config):
        """Create observability instance with disabled config."""
        mock_config.langfuse.enabled = False
        with patch("src.observability.langfuse_callback.get_config", return_value=mock_config):
            obs = LangfuseObservability()
            return obs

    def test_initialization_enabled(self, mock_config, mock_langfuse_client):
        """Test successful initialization with Langfuse enabled."""
        with patch("src.observability.langfuse_callback.get_config", return_value=mock_config):
            with patch("src.observability.langfuse_callback.Langfuse", return_value=mock_langfuse_client):
                obs = LangfuseObservability()

                assert obs.enabled is True
                assert obs.client == mock_langfuse_client
                assert obs.config == mock_config

    def test_initialization_disabled(self, mock_config):
        """Test initialization with Langfuse disabled."""
        mock_config.langfuse.enabled = False

        with patch("src.observability.langfuse_callback.get_config", return_value=mock_config):
            obs = LangfuseObservability()

            assert obs.enabled is False
            assert obs.client is None

    def test_initialization_with_connection_error(self, mock_config):
        """Test graceful degradation when Langfuse connection fails."""
        with patch("src.observability.langfuse_callback.get_config", return_value=mock_config):
            with patch("src.observability.langfuse_callback.Langfuse", side_effect=Exception("Connection failed")):
                obs = LangfuseObservability()

                assert obs.enabled is False
                assert obs.client is None

    def test_track_retrieval_success(self, observability_enabled):
        """Test successful retrieval tracking."""
        observability_enabled.track_retrieval(
            conversation_id="conv_123",
            query="test query",
            results_count=5,
            retrieval_type="hybrid",
        )

        # Verify score was recorded
        observability_enabled.client.create_score.assert_called_once_with(
            name="retrieval_count",
            value=5,
            trace_id="conv_123",
        )

        # Note: Event logging is simplified and logged via logger, not create_event

    def test_track_retrieval_when_disabled(self, observability_disabled):
        """Test retrieval tracking is skipped when disabled."""
        observability_disabled.track_retrieval(
            conversation_id="conv_123",
            query="test query",
            results_count=5,
        )
        # Should not raise any errors and should not call client

    def test_track_retrieval_with_error(self, observability_enabled):
        """Test graceful handling of tracking errors."""
        observability_enabled.client.create_score.side_effect = Exception("Tracking error")

        # Should not raise exception
        observability_enabled.track_retrieval(
            conversation_id="conv_123",
            query="test query",
            results_count=5,
        )

    def test_track_llm_generation_success(self, observability_enabled):
        """Test successful LLM generation tracking."""
        mock_generation = MagicMock()
        observability_enabled.client.start_generation.return_value = mock_generation

        observability_enabled.track_llm_generation(
            conversation_id="conv_123",
            model="ministral-3:3b",
            prompt="Hello, how are you?",
            response="I'm doing well, thank you!",
            duration_ms=1500.5,
            metadata={"temperature": 0.7, "max_tokens": 512},
        )

        # Verify generation was recorded
        observability_enabled.client.start_generation.assert_called_once()
        call_args = observability_enabled.client.start_generation.call_args
        assert call_args[1]["name"] == "llm_generation"
        assert call_args[1]["trace_id"] == "conv_123"
        assert call_args[1]["model"] == "ministral-3:3b"
        assert "Hello, how are you?" in call_args[1]["input"]
        assert "I'm doing well" in call_args[1]["output"]
        mock_generation.end.assert_called_once()

    def test_track_llm_generation_truncates_long_text(self, observability_enabled):
        """Test that long prompts and responses are truncated."""
        mock_generation = MagicMock()
        observability_enabled.client.start_generation.return_value = mock_generation

        long_prompt = "A" * 2000
        long_response = "B" * 2000

        observability_enabled.track_llm_generation(
            conversation_id="conv_123",
            model="ministral-3:3b",
            prompt=long_prompt,
            response=long_response,
            duration_ms=1500.5,
        )

        call_args = observability_enabled.client.start_generation.call_args
        assert len(call_args[1]["input"]) == 1000
        assert len(call_args[1]["output"]) == 1000

    def test_track_llm_generation_when_disabled(self, observability_disabled):
        """Test LLM generation tracking is skipped when disabled."""
        observability_disabled.track_llm_generation(
            conversation_id="conv_123",
            model="ministral-3:3b",
            prompt="test",
            response="response",
            duration_ms=100,
        )
        # Should not raise any errors

    def test_track_agent_decision_success(self, observability_enabled):
        """Test successful agent decision tracking."""
        observability_enabled.track_agent_decision(
            conversation_id="conv_123",
            decision_type="tool_selection",
            tool_used="retrieve_documents",
            metadata={"confidence": 0.95},
        )

        # Note: Event logging is simplified and logged via logger, not create_event

    def test_track_agent_decision_without_tool(self, observability_enabled):
        """Test agent decision tracking without tool usage."""
        observability_enabled.track_agent_decision(
            conversation_id="conv_123",
            decision_type="rag_response",
        )

        # Note: Event logging is simplified and logged via logger, not create_event

    def test_track_agent_decision_when_disabled(self, observability_disabled):
        """Test agent decision tracking is skipped when disabled."""
        observability_disabled.track_agent_decision(
            conversation_id="conv_123",
            decision_type="tool_selection",
        )
        # Should not raise any errors

    def test_track_confidence_score_success(self, observability_enabled):
        """Test successful confidence score tracking."""
        observability_enabled.track_confidence_score(
            conversation_id="conv_123",
            confidence=0.85,
            reasoning="High similarity with retrieved documents",
        )

        # Verify score was recorded
        observability_enabled.client.create_score.assert_called_once_with(
            name="answer_confidence",
            value=0.85,
            trace_id="conv_123",
            comment="High similarity with retrieved documents",
        )

    def test_track_confidence_score_without_reasoning(self, observability_enabled):
        """Test confidence score tracking without reasoning."""
        observability_enabled.track_confidence_score(
            conversation_id="conv_123",
            confidence=0.75,
        )

        call_args = observability_enabled.client.create_score.call_args
        assert call_args[1]["comment"] is None

    def test_track_confidence_score_when_disabled(self, observability_disabled):
        """Test confidence score tracking is skipped when disabled."""
        observability_disabled.track_confidence_score(
            conversation_id="conv_123",
            confidence=0.85,
        )
        # Should not raise any errors

    def test_flush_success(self, observability_enabled):
        """Test successful flushing of traces."""
        observability_enabled.flush()
        observability_enabled.client.flush.assert_called_once()

    def test_flush_when_disabled(self, observability_disabled):
        """Test flush is skipped when disabled."""
        observability_disabled.flush()
        # Should not raise any errors

    def test_flush_with_error(self, observability_enabled):
        """Test graceful handling of flush errors."""
        observability_enabled.client.flush.side_effect = Exception("Flush error")

        # Should not raise exception
        observability_enabled.flush()

    def test_is_healthy_success(self, observability_enabled):
        """Test health check returns True when service is healthy."""
        # Reset mock call count from initialization
        observability_enabled.client.auth_check.reset_mock()
        observability_enabled.client.auth_check.return_value = True

        assert observability_enabled.is_healthy() is True
        observability_enabled.client.auth_check.assert_called_once()

    def test_is_healthy_when_disabled(self, observability_disabled):
        """Test health check returns False when disabled."""
        assert observability_disabled.is_healthy() is False

    def test_is_healthy_with_error(self, observability_enabled):
        """Test health check returns False when auth check fails."""
        observability_enabled.client.auth_check.side_effect = Exception("Auth failed")

        assert observability_enabled.is_healthy() is False

    def test_singleton_pattern(self, mock_config):
        """Test that get_langfuse_observability returns singleton instance."""
        with patch("src.observability.langfuse_callback.get_config", return_value=mock_config):
            with patch("src.observability.langfuse_callback.Langfuse"):
                # Reset singleton
                import src.observability.langfuse_callback as module
                module._observability_instance = None

                instance1 = get_langfuse_observability()
                instance2 = get_langfuse_observability()

                assert instance1 is instance2
