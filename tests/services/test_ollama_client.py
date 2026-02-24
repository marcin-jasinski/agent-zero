"""Unit tests for Ollama service client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, Timeout, ConnectionError

from src.services.ollama_client import OllamaClient


@pytest.fixture
def ollama_client():
    """Create an OllamaClient instance for testing."""
    with patch("src.services.ollama_client.get_config") as mock_config:
        mock_config.return_value.ollama.base_url = "http://localhost:11434"
        mock_config.return_value.ollama.embedding_model = "nomic-embed-text:latest"
        return OllamaClient(base_url="http://localhost:11434")


class TestOllamaClientInitialization:
    """Test OllamaClient initialization."""

    def test_init_with_custom_url(self):
        """Test initialization with custom URL."""
        with patch("src.services.ollama_client.get_config"):
            client = OllamaClient(base_url="http://custom:11434", timeout=60)
            assert client.base_url == "http://custom:11434"
            assert client.timeout == 60

    def test_init_uses_config_default(self):
        """Test initialization uses config defaults."""
        with patch("src.services.ollama_client.get_config") as mock_config:
            mock_config.return_value.ollama.base_url = "http://ollama:11434"
            client = OllamaClient()
            assert client.base_url == "http://ollama:11434"

    def test_session_retry_strategy(self, ollama_client):
        """Test that session has proper retry strategy."""
        assert ollama_client.session is not None
        # Verify adapters are mounted
        assert "http://" in ollama_client.session.adapters
        assert "https://" in ollama_client.session.adapters


class TestOllamaClientHealthCheck:
    """Test Ollama health check functionality."""

    def test_is_healthy_success(self, ollama_client):
        """Test successful health check."""
        with patch.object(ollama_client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert ollama_client.is_healthy() is True
            mock_get.assert_called_once()

    def test_is_healthy_failure(self, ollama_client):
        """Test failed health check."""
        with patch.object(ollama_client.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("Connection failed")

            assert ollama_client.is_healthy() is False

    def test_is_healthy_timeout(self, ollama_client):
        """Test health check timeout."""
        with patch.object(ollama_client.session, "get") as mock_get:
            mock_get.side_effect = Timeout("Request timed out")

            assert ollama_client.is_healthy() is False

    def test_is_healthy_http_error(self, ollama_client):
        """Test health check with HTTP error."""
        with patch.object(ollama_client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            assert ollama_client.is_healthy() is False


class TestOllamaClientListModels:
    """Test list models functionality."""

    def test_list_models_success(self, ollama_client):
        """Test successful model listing."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {
                "models": [
                    {"name": "ministral-3:3b"},
                    {"name": "llama2:latest"},
                ]
            }

            models = ollama_client.list_models()
            assert len(models) == 2
            assert "ministral-3:3b" in models
            assert "llama2:latest" in models

    def test_list_models_empty(self, ollama_client):
        """Test listing when no models available."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"models": []}

            models = ollama_client.list_models()
            assert models == []

    def test_list_models_error(self, ollama_client):
        """Test error handling in list_models."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.side_effect = RequestException("API error")

            models = ollama_client.list_models()
            assert models == []

    def test_list_models_malformed_response(self, ollama_client):
        """Test handling malformed response."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"invalid_key": []}

            models = ollama_client.list_models()
            assert models == []


class TestOllamaClientGenerate:
    """Test text generation functionality."""

    def test_generate_success(self, ollama_client):
        """Test successful text generation."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {
                "response": "Generated text response"
            }

            result = ollama_client.generate(
                model="ministral-3:3b",
                prompt="What is AI?",
            )

            assert result == "Generated text response"
            mock_request.assert_called_once()

    def test_generate_with_system_prompt(self, ollama_client):
        """Test generation with system prompt."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"response": "Reply"}

            ollama_client.generate(
                model="ministral-3:3b",
                prompt="Hello",
                system="You are helpful",
                temperature=0.5,
                top_p=0.8,
            )

            # Verify system prompt was passed
            call_args = mock_request.call_args
            assert call_args[1]["json"]["system"] == "You are helpful"
            assert call_args[1]["json"]["temperature"] == 0.5
            assert call_args[1]["json"]["top_p"] == 0.8

    def test_generate_with_max_tokens(self, ollama_client):
        """Test generation with max tokens limit."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"response": "Short response"}

            ollama_client.generate(
                model="ministral-3:3b",
                prompt="Hi",
                max_tokens=100,
            )

            call_args = mock_request.call_args
            assert call_args[1]["json"]["options"]["num_predict"] == 100

    def test_generate_empty_response(self, ollama_client):
        """Test handling empty response."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {}

            result = ollama_client.generate(
                model="ministral-3:3b",
                prompt="Test",
            )

            assert result == ""

    def test_generate_error(self, ollama_client):
        """Test error handling in generate."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.side_effect = RequestException("Model not found")

            with pytest.raises(RequestException):
                ollama_client.generate(
                    model="nonexistent:model",
                    prompt="Test",
                )


class TestOllamaClientEmbed:
    """Test embedding generation."""

    def test_embed_success(self, ollama_client):
        """Test successful embedding generation."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_vector = [0.1, 0.2, 0.3, 0.4]
            mock_request.return_value = {
                "embeddings": [mock_vector]
            }

            result = ollama_client.embed(text="Test text")

            assert result == mock_vector

    def test_embed_uses_config_model(self, ollama_client):
        """Test that embed uses config model when not specified."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"embeddings": [[0.1, 0.2]]}

            ollama_client.embed(text="Test")

            call_args = mock_request.call_args
            # Should use config default model
            assert call_args[1]["json"]["model"] == "nomic-embed-text:latest"

    def test_embed_custom_model(self, ollama_client):
        """Test embedding with custom model."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"embeddings": [[0.1]]}

            ollama_client.embed(text="Test", model="custom-embed")

            call_args = mock_request.call_args
            assert call_args[1]["json"]["model"] == "custom-embed"

    def test_embed_empty_response(self, ollama_client):
        """Test handling empty embeddings response."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.return_value = {"embeddings": [[]]}

            result = ollama_client.embed(text="Test")

            assert result == []

    def test_embed_error(self, ollama_client):
        """Test error handling in embed."""
        with patch.object(ollama_client, "_make_request") as mock_request:
            mock_request.side_effect = RequestException("Embed error")

            with pytest.raises(RequestException):
                ollama_client.embed(text="Test")


class TestOllamaClientPullModel:
    """Test model pulling."""

    def test_pull_model_success(self, ollama_client):
        """Test successful model pull."""
        # Mock the session.post method since pull_model uses it directly (not _make_request)
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.iter_lines = Mock(return_value=[
            b'{"status": "pulling"}'.decode(),
            b'{"status": "success"}'.decode(),
        ])
        
        with patch.object(ollama_client.session, "post", return_value=mock_response):
            result = ollama_client.pull_model("ministral-3:3b")
            assert result is True

    def test_pull_model_failure(self, ollama_client):
        """Test failed model pull."""
        with patch.object(ollama_client.session, "post") as mock_post:
            mock_post.side_effect = RequestException("Model not available")

            result = ollama_client.pull_model("nonexistent:model")

            assert result is False

    def test_pull_model_network_error(self, ollama_client):
        """Test network error during pull."""
        with patch.object(ollama_client.session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("Network unavailable")

            result = ollama_client.pull_model("model:tag")

            assert result is False


class TestOllamaClientMakeRequest:
    """Test internal request handling."""

    def test_make_request_success(self, ollama_client):
        """Test successful request."""
        with patch.object(ollama_client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response

            result = ollama_client._make_request("post", "/api/generate")

            assert result == {"result": "success"}

    def test_make_request_http_error(self, ollama_client):
        """Test HTTP error in request."""
        with patch.object(ollama_client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = RequestException("404 Not Found")
            mock_request.return_value = mock_response

            with pytest.raises(RequestException):
                ollama_client._make_request("get", "/api/invalid")

    def test_make_request_json_decode_error(self, ollama_client):
        """Test JSON decode error."""
        with patch.object(ollama_client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_request.return_value = mock_response

            with pytest.raises(ValueError):
                ollama_client._make_request("get", "/api/tags")

    def test_make_request_timeout(self, ollama_client):
        """Test request timeout."""
        with patch.object(ollama_client.session, "request") as mock_request:
            mock_request.side_effect = Timeout("Request timeout")

            with pytest.raises(Timeout):
                ollama_client._make_request("get", "/api/tags")

    def test_make_request_url_construction(self, ollama_client):
        """Test URL is constructed correctly."""
        with patch.object(ollama_client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_request.return_value = mock_response

            ollama_client._make_request("get", "/api/tags")

            # Verify URL was constructed correctly
            call_args = mock_request.call_args
            assert "http://localhost:11434/api/tags" in call_args[0]
