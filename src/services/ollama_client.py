"""Ollama LLM Service Client.

Handles communication with Ollama for LLM inference and embeddings.
"""

import json
import logging
import re
from typing import Callable, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from src.config import get_config

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama LLM service."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 120):
        """Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama service (e.g., http://ollama:11434)
            timeout: Request timeout in seconds (default 120s for LLM generation)

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
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Generate text using Ollama.

        When *on_token* is provided the request is made with ``stream=True``
        and each token chunk is forwarded to the callback as it arrives,
        enabling real-time streaming in the UI.  The full response string is
        still returned for downstream processing.

        Args:
            model: Model name (e.g., 'qwen3:4b')
            prompt: Input prompt
            system: System prompt/instructions
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter (0-1)
            max_tokens: Maximum tokens to generate
            on_token: Optional callback invoked with each streamed token chunk.
                      When provided, streaming mode is enabled automatically.

        Returns:
            Generated text (full response, regardless of streaming mode)
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": on_token is not None,
                "temperature": temperature,
                "top_p": top_p,
            }

            if system:
                payload["system"] = system

            if max_tokens:
                payload["options"] = {"num_predict": max_tokens}

            if on_token is None:
                # Non-streaming path — single JSON response
                data = self._make_request("post", "/api/generate", json=payload)
                return self._strip_thinking_tags(data.get("response", ""))

            # Streaming path — Ollama returns NDJSON, one chunk per line
            url = f"{self.base_url}/api/generate"
            response = self.session.post(
                url, json=payload, timeout=self.timeout, stream=True
            )
            response.raise_for_status()

            accumulated = []
            in_think_block = False  # Suppress <think>...</think> from UI callback
            think_buffer = ""      # Buffer partial tag detection

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response", "")
                if token:
                    accumulated.append(token)
                    # Track thinking-block boundaries so the UI only receives
                    # the actual answer, not the internal reasoning.
                    think_buffer += token
                    if "<think>" in think_buffer:
                        in_think_block = True
                    if "</think>" in think_buffer:
                        in_think_block = False
                        think_buffer = ""
                    elif not in_think_block:
                        think_buffer = ""
                        on_token(token)
                if chunk.get("done", False):
                    break

            # Strip any residual <think> blocks from the full accumulated text
            # (covers the non-streaming path and partial tags).
            return self._strip_thinking_tags("".join(accumulated))

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise

    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        """Remove <think>...</think> reasoning blocks from model output.

        Thinking models such as qwen3 wrap internal chain-of-thought reasoning
        in <think>...</think> tags.  These blocks should not be stored in
        conversation memory or scanned by LLM Guard — only the final answer
        matters for downstream use.

        Handles both complete blocks and the edge-case where a partial opening
        tag appears without a closing tag (model interrupted mid-think).

        Args:
            text: Raw model output, possibly containing <think> blocks.

        Returns:
            Output with all <think>...</think> blocks removed and whitespace
            trimmed.  Returns the original string unchanged if no tags found.
        """
        if "<think>" not in text:
            return text
        # Remove complete blocks (including nested newlines)
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Remove any dangling opening tag (model stopped mid-thinking)
        cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL)
        return cleaned.strip()

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

    def warm_up(self, model: str, timeout: int = 300) -> bool:
        """Warm up/preload a model into memory.

        Sends a minimal generation request to load the model weights into memory,
        reducing latency on the first real user request. Large models (e.g.
        qwen3:4b) can take 60+ seconds to transfer from disk to GPU VRAM, so
        a dedicated timeout of 300 s is used instead of the default request
        timeout.

        Args:
            model: Model name to warm up
            timeout: Request timeout in seconds (default 300 to accommodate
                     large model load times)

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Warming up model '{model}' (timeout={timeout}s)...")
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": "Hello",
                "stream": False,
                "options": {"num_predict": 1},  # Generate minimal output
            }
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            logger.info(f"Model '{model}' warmed up successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to warm up model '{model}': {e}")
            return False

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
