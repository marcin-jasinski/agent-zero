"""Ollama LLM Service Client.

Handles communication with Ollama for LLM inference and embeddings.
"""

import json
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from src.config import get_config

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama LLM service."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama service (e.g., http://ollama:11434)
            timeout: Request timeout in seconds

        Raises:
            ValueError: If base_url is empty or timeout is not positive
        """
        config = get_config()
        self.base_url = base_url or config.ollama.base_url
        
        # Validate inputs
        if not self.base_url or not self.base_url.strip():
            raise ValueError("base_url cannot be empty")
        if timeout <= 0:
            raise ValueError(f"timeout must be positive, got {timeout}")
        
        self.timeout = timeout

        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Ollama client initialized: {self.base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make HTTP request to Ollama.

        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request arguments

        Returns:
            dict: Response data as dictionary

        Raises:
            RequestException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def is_healthy(self) -> bool:
        """Check if Ollama service is healthy.

        Returns:
            True if service is responding, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def list_models(self) -> list[str]:
        """List available models in Ollama.

        Returns:
            List of model names
        """
        try:
            data = self._make_request("get", "/api/tags")
            models = [model["name"] for model in data.get("models", [])]
            logger.info(f"Available models: {models}")
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using Ollama.

        Args:
            model: Model name (e.g., 'ministral-3:3b')
            prompt: Input prompt
            system: System prompt/instructions
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "top_p": top_p,
            }

            if system:
                payload["system"] = system

            if max_tokens:
                payload["options"] = {"num_predict": max_tokens}

            data = self._make_request("post", "/api/generate", json=payload)
            return data.get("response", "")
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise

    def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """Generate embeddings for text.

        Args:
            text: Text to embed
            model: Embedding model name (uses config default if not specified)

        Returns:
            Embedding vector
        """
        config = get_config()
        model = model or config.ollama.embed_model

        try:
            payload = {
                "model": model,
                "input": text,
            }

            data = self._make_request("post", "/api/embed", json=payload)
            return data.get("embeddings", [[]])[0]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama library.

        Args:
            model: Model name to pull

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/pull"
            payload = {"name": model}
            
            # The /api/pull endpoint returns streaming responses
            # We need to handle the streaming format
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            
            # Read all streamed responses
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("status") == "success":
                            logger.info(f"Model '{model}' pulled successfully")
                    except json.JSONDecodeError:
                        # Ignore malformed JSON lines
                        pass
            
            return True
        except Exception as e:
            logger.error(f"Failed to pull model '{model}': {e}")
            return False
