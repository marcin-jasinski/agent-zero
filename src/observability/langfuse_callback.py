"""Langfuse observability integration for Agent Zero.

This module provides observability tracking for Langfuse integration,
tracking LLM calls, tool usage, agent decisions, and execution metrics.

Uses Langfuse SDK v2 API with trace-based tracking.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from langfuse import Langfuse

from src.config import get_config

logger = logging.getLogger(__name__)


class LangfuseObservability:
    """Manages Langfuse observability integration for Agent Zero.

    This class provides:
    - Trace management for conversations
    - Custom metrics tracking (retrieval count, confidence scores)
    - Error handling and graceful degradation
    
    Uses Langfuse SDK v2 trace-based API.
    """

    def __init__(self) -> None:
        """Initialize Langfuse observability.

        Raises:
            ImportError: If langfuse library is not available
            ValueError: If Langfuse is enabled but configuration is incomplete
        """
        self.config = get_config()
        self.enabled = self.config.langfuse.enabled
        self.client: Optional[Langfuse] = None
        # Cache active traces by conversation_id
        self._traces: Dict[str, Any] = {}

        if self.enabled:
            try:
                self._initialize_langfuse()
                logger.info(
                    f"Langfuse observability initialized: host={self.config.langfuse.host}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                logger.warning("Langfuse observability disabled due to initialization error")
                self.enabled = False

    def _initialize_langfuse(self) -> None:
        """Initialize Langfuse client.

        Raises:
            ValueError: If configuration is incomplete
            ConnectionError: If cannot connect to Langfuse service
        """
        # Validate configuration
        if not self.config.langfuse.host:
            raise ValueError("Langfuse host not configured")

        # Initialize Langfuse client
        try:
            self.client = Langfuse(
                host=self.config.langfuse.host,
                public_key=self.config.langfuse.public_key or None,
                secret_key=self.config.langfuse.secret_key or None,
            )

            # Test connection
            self.client.auth_check()

            logger.info("Langfuse client initialized successfully")

        except Exception as e:
            logger.error(f"Langfuse initialization failed: {e}")
            raise ConnectionError(f"Cannot connect to Langfuse at {self.config.langfuse.host}: {e}")

    def _get_or_create_trace(self, conversation_id: str, name: str = "agent-zero-conversation") -> Any:
        """Get existing trace or create new one for conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            name: Name for the trace
            
        Returns:
            Langfuse trace object
        """
        if conversation_id not in self._traces:
            self._traces[conversation_id] = self.client.trace(
                id=conversation_id,
                name=name,
                metadata={"created_at": datetime.utcnow().isoformat()},
            )
        return self._traces[conversation_id]

    def track_retrieval(
        self,
        conversation_id: str,
        query: str,
        results_count: int,
        retrieval_type: str = "hybrid",
    ) -> None:
        """Track document retrieval metrics.

        Args:
            conversation_id: Unique conversation identifier
            query: User query that triggered retrieval
            results_count: Number of documents retrieved
            retrieval_type: Type of retrieval (semantic, keyword, hybrid)
        """
        if not self.enabled or not self.client:
            return

        try:
            trace = self._get_or_create_trace(conversation_id)
            
            # Create a span for the retrieval operation
            trace.span(
                name="document_retrieval",
                input={"query": query[:500], "type": retrieval_type},
                output={"results_count": results_count},
                metadata={
                    "retrieval_type": retrieval_type,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.debug(
                f"Tracked retrieval: conversation_id={conversation_id}, "
                f"results={results_count}, type={retrieval_type}"
            )

        except Exception as e:
            logger.error(f"Failed to track retrieval metrics: {e}")

    def track_llm_generation(
        self,
        conversation_id: str,
        model: str,
        prompt: str,
        response: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track LLM generation call.

        Args:
            conversation_id: Unique conversation identifier
            model: Model name used
            prompt: Input prompt
            response: Generated response
            duration_ms: Generation duration in milliseconds
            metadata: Additional metadata (temperature, tokens, etc.)
        """
        if not self.enabled or not self.client:
            return

        try:
            trace = self._get_or_create_trace(conversation_id)
            
            generation_metadata = {
                "duration_ms": duration_ms,
                "prompt_length": len(prompt),
                "response_length": len(response),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if metadata:
                generation_metadata.update(metadata)

            # Use trace.generation() for LLM calls (Langfuse v2 API)
            trace.generation(
                name="llm_generation",
                input=prompt[:2000],  # Truncate for storage
                output=response[:2000],  # Truncate for storage
                model=model,
                metadata=generation_metadata,
            )

            logger.debug(
                f"Tracked LLM generation: conversation_id={conversation_id}, "
                f"model={model}, duration={duration_ms:.2f}ms"
            )

        except Exception as e:
            logger.error(f"Failed to track LLM generation: {e}")

    def track_agent_decision(
        self,
        conversation_id: str,
        decision_type: str,
        tool_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track agent decision-making events.

        Args:
            conversation_id: Unique conversation identifier
            decision_type: Type of decision (tool_call, direct_response, etc.)
            tool_used: Name of tool used (if applicable)
            metadata: Additional decision metadata
        """
        if not self.enabled or not self.client:
            return

        try:
            trace = self._get_or_create_trace(conversation_id)
            
            event_metadata = {
                "decision_type": decision_type,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if tool_used:
                event_metadata["tool_used"] = tool_used

            if metadata:
                event_metadata.update(metadata)

            # Create a span for the agent decision
            trace.span(
                name=f"agent_decision_{decision_type}",
                input={"decision_type": decision_type, "tool": tool_used},
                metadata=event_metadata,
            )

            logger.debug(
                f"Tracked agent decision: conversation_id={conversation_id}, "
                f"type={decision_type}, tool={tool_used}"
            )

        except Exception as e:
            logger.error(f"Failed to track agent decision: {e}")

    def track_confidence_score(
        self,
        conversation_id: str,
        confidence: float,
        reasoning: Optional[str] = None,
    ) -> None:
        """Track answer confidence scores.

        Args:
            conversation_id: Unique conversation identifier
            confidence: Confidence score (0.0-1.0)
            reasoning: Optional reasoning for confidence score
        """
        if not self.enabled or not self.client:
            return

        try:
            trace = self._get_or_create_trace(conversation_id)
            
            # Use trace.score() for Langfuse v2 API
            trace.score(
                name="answer_confidence",
                value=confidence,
                comment=reasoning,
            )

            logger.debug(
                f"Tracked confidence score: conversation_id={conversation_id}, "
                f"confidence={confidence:.2f}"
            )

        except Exception as e:
            logger.error(f"Failed to track confidence score: {e}")

    def end_conversation(self, conversation_id: str) -> None:
        """End tracking for a conversation and flush data.
        
        Args:
            conversation_id: Unique conversation identifier
        """
        if not self.enabled or not self.client:
            return
            
        try:
            # Remove from cache
            if conversation_id in self._traces:
                del self._traces[conversation_id]
            
            # Flush to ensure data is sent
            self.client.flush()
            
            logger.debug(f"Ended conversation tracking: {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to end conversation tracking: {e}")

    def flush(self) -> None:
        """Flush pending traces to Langfuse.

        Should be called at the end of operations to ensure all traces are sent.
        """
        if not self.enabled or not self.client:
            return

        try:
            self.client.flush()
            logger.debug("Langfuse traces flushed successfully")
        except Exception as e:
            logger.error(f"Failed to flush Langfuse traces: {e}")

    def is_healthy(self) -> bool:
        """Check if Langfuse connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.auth_check()
            return True
        except Exception as e:
            logger.warning(f"Langfuse health check failed: {e}")
            return False


# Singleton instance
_observability_instance: Optional[LangfuseObservability] = None


def get_langfuse_observability() -> LangfuseObservability:
    """Get or create singleton Langfuse observability instance.

    Returns:
        LangfuseObservability instance
    """
    global _observability_instance

    if _observability_instance is None:
        _observability_instance = LangfuseObservability()

    return _observability_instance
