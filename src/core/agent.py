"""Agent orchestration for Agent Zero with LangChain integration.

This module implements the main agent that orchestrates retrieval,
tool calling, and LLM invocation for multi-turn conversations.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from src.core.retrieval import RetrievalEngine
from src.core.memory import ConversationManager
from src.models.agent import AgentConfig, AgentMessage, MessageRole, ConversationState
from src.models.retrieval import RetrievalResult
from src.services.ollama_client import OllamaClient
from src.security.guard import LLMGuard, ThreatLevel
from src.observability import get_langfuse_observability, track_llm_generation
from src.config import get_config

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Main agent for orchestrating multi-turn conversations with RAG.

    This agent manages:
    - Conversation state and multi-turn memory
    - Document retrieval via RAG
    - Tool invocation (retrieve_documents, search_knowledge_base)
    - LLM interaction via Ollama
    - Response generation with source attribution
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        retrieval_engine: RetrievalEngine,
        config: Optional[AgentConfig] = None,
        llm_guard: Optional[LLMGuard] = None,
    ) -> None:
        """Initialize the agent orchestrator.

        Args:
            ollama_client: Client for LLM inference
            retrieval_engine: Engine for document retrieval
            config: Agent configuration (uses defaults if not provided)
            llm_guard: Optional LLM Guard for security scanning (creates default if None)
        """
        self.ollama_client = ollama_client
        self.retrieval_engine = retrieval_engine
        self.config = config or AgentConfig()
        self.memory = ConversationManager()

        # Initialize LLM Guard from app config if not provided
        if llm_guard is None:
            app_config = get_config()
            self.llm_guard = LLMGuard(
                enabled=app_config.security.llm_guard_enabled,
                input_scan_enabled=app_config.security.llm_guard_input_scan,
                output_scan_enabled=app_config.security.llm_guard_output_scan,
                max_input_length=app_config.security.max_input_length,
                max_output_length=app_config.security.max_output_length,
            )
        else:
            self.llm_guard = llm_guard

        # Initialize Langfuse observability
        self.observability = get_langfuse_observability()

        # Define available tools
        self.tools = {
            "retrieve_documents": self._retrieve_documents,
            "search_knowledge_base": self._search_knowledge_base,
            "get_current_time": self._get_current_time,
        }

        logger.info(
            f"Initialized AgentOrchestrator with model {self.config.model_name}, "
            f"LLM Guard enabled={self.llm_guard.enabled}, "
            f"Langfuse observability enabled={self.observability.enabled}"
        )

    def start_conversation(self, metadata: Optional[Dict] = None) -> str:
        """Start a new conversation session.

        Args:
            metadata: Optional conversation metadata

        Returns:
            Unique conversation ID
        """
        conversation_id = self.memory.create_conversation(metadata)

        # Add system message if configured
        if self.config.system_prompt:
            self.memory.add_message(
                conversation_id,
                MessageRole.SYSTEM,
                self.config.system_prompt,
            )

        return conversation_id

    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        use_retrieval: bool = True,
        stream_callback: Optional[Callable[[str], None]] = None,
        thinking_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Process a user message and generate agent response.

        This method orchestrates the complete agent workflow:
        1. Add user message to history
        2. Retrieve relevant documents if enabled
        3. Build context from conversation history
        4. Invoke LLM to generate response
        5. Add response to history with source attribution

        Args:
            conversation_id: ID of the conversation
            user_message: User input text
            use_retrieval: Whether to retrieve documents
            stream_callback: Optional callback for streaming responses
            thinking_callback: Optional callback called once with the full
                content of <think>...</think> blocks (chain-of-thought reasoning).

        Returns:
            Agent response text with source attribution

        Raises:
            ValueError: If conversation or user message is invalid
        """
        if not user_message or not user_message.strip():
            raise ValueError("User message cannot be empty")

        import time
        start_time = time.time()
        logger.info(f"[TIMING] Starting message processing")

        try:
            # Scan user input for security threats
            scan_start = time.time()
            input_scan_result = self.llm_guard.scan_user_input(user_message)
            logger.info(f"[TIMING] Input scan completed in {time.time() - scan_start:.2f}s")

            # Block critical threats
            if not input_scan_result.is_safe:
                logger.warning(
                    f"User input blocked: threat_level={input_scan_result.threat_level.value}, "
                    f"violations={input_scan_result.violations}"
                )

                if input_scan_result.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                    error_msg = (
                        "Your message was blocked due to security concerns. "
                        f"Detected violations: {', '.join(input_scan_result.violations[:2])}"
                    )
                    logger.error(f"Critical threat blocked for conversation {conversation_id}")
                    return error_msg

            # Use sanitized input if available
            processed_message = (
                input_scan_result.sanitized_content
                if input_scan_result.sanitized_content
                else user_message
            )

            # Add user message to history
            self.memory.add_message(
                conversation_id,
                MessageRole.USER,
                processed_message,
            )

            # Retrieve relevant documents
            retrieved_docs: List[RetrievalResult] = []
            if use_retrieval:
                try:
                    retrieval_start = time.time()
                    retrieved_docs = self.retrieval_engine.retrieve_relevant_docs(
                        processed_message,
                        top_k=5,
                    )
                    logger.info(f"[TIMING] Retrieval completed in {time.time() - retrieval_start:.2f}s - Retrieved {len(retrieved_docs)} documents")

                    # Track retrieval metrics in Langfuse
                    self.observability.track_retrieval(
                        conversation_id=conversation_id,
                        query=processed_message,
                        results_count=len(retrieved_docs),
                        retrieval_type="hybrid",
                    )

                except Exception as e:
                    logger.warning(f"Document retrieval failed: {e}")

            prompt_start = time.time()
            context = self._build_prompt(
                conversation_id,
                processed_message,
                retrieved_docs,
            )
            logger.info(f"[TIMING] Prompt building completed in {time.time() - prompt_start:.2f}s")

            # Generate response
            llm_start = time.time()
            response_text = self._invoke_llm(
                context, stream_callback, thinking_callback=thinking_callback, conversation_id=conversation_id
            )
            logger.info(f"[TIMING] LLM generation completed in {time.time() - llm_start:.2f}s")

            # Scan LLM output for security threats.
            # Guard against empty responses (e.g. thinking-only output after
            # <think> stripping) to avoid hard ValueError in scan_llm_output.
            if not response_text or not response_text.strip():
                logger.warning("LLM returned empty response after processing; using fallback message")
                response_text = "I'm sorry, I wasn't able to generate a response. Please try rephrasing your question."

            output_scan_result = self.llm_guard.scan_llm_output(
                response_text, original_prompt=processed_message
            )

            # Block unsafe outputs
            if not output_scan_result.is_safe:
                logger.warning(
                    f"LLM output blocked: threat_level={output_scan_result.threat_level.value}, "
                    f"violations={output_scan_result.violations}"
                )

                if output_scan_result.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                    response_text = (
                        "I apologize, but I cannot provide that response due to safety concerns. "
                        "Please rephrase your question."
                    )
                elif output_scan_result.sanitized_content:
                    response_text = output_scan_result.sanitized_content

            # Add response to history
            sources = self._extract_sources(retrieved_docs)
            self.memory.add_message(
                conversation_id,
                MessageRole.ASSISTANT,
                response_text,
                metadata={
                    "sources": sources,
                    "documents_used": len(retrieved_docs),
                },
            )

            # When streaming: push the source-attribution footer to the UI
            # callback so it appears inline rather than being silently dropped.
            if stream_callback and sources:
                footer = "\n\n**Sources:**\n" + "\n".join(f"- {s}" for s in sources)
                stream_callback(footer)

            # Track agent decision in Langfuse
            self.observability.track_agent_decision(
                conversation_id=conversation_id,
                decision_type="rag_response",
                metadata={
                    "documents_used": len(retrieved_docs),
                    "used_retrieval": use_retrieval,
                    "response_length": len(response_text),
                },
            )

            # Format response with sources
            formatted_response = self._format_response_with_sources(
                response_text,
                retrieved_docs,
            )

            # Flush Langfuse traces
            self.observability.flush()

            logger.info(f"Generated response for conversation {conversation_id}")
            return formatted_response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise

    async def process_message_async(
        self,
        conversation_id: str,
        message: str,
        use_retrieval: bool = True,
    ) -> str:
        """Asynchronously process a user message via a worker thread.

        Args:
            conversation_id: ID of the conversation.
            message: User input text.
            use_retrieval: Whether retrieval should be used.

        Returns:
            Agent response text with source attribution.
        """
        return await asyncio.to_thread(
            self.process_message,
            conversation_id,
            message,
            use_retrieval,
        )

    def _retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Tool: Retrieve documents matching query.

        Args:
            query: Search query
            top_k: Number of documents to retrieve

        Returns:
            List of document results with content and metadata
        """
        try:
            results = self.retrieval_engine.retrieve_relevant_docs(query, top_k=top_k)
            return [
                {
                    "content": r.content,
                    "source": r.source,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Document retrieval tool failed: {e}")
            return []

    def _search_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Tool: Search knowledge base with context.

        Args:
            query: Search query

        Returns:
            Dictionary with search results and statistics
        """
        try:
            results = self.retrieval_engine.search_with_context(
                query,
                context_chunks=1,
                top_k=3,
            )

            return {
                "results": [
                    {
                        "content": r.content,
                        "source": r.source,
                        "score": r.score,
                    }
                    for r in results
                ],
                "count": len(results),
                "query": query,
            }
        except Exception as e:
            logger.error(f"Knowledge base search tool failed: {e}")
            return {"error": str(e), "results": []}

    def _get_current_time(self) -> Dict[str, str]:
        """Tool: Get current time.

        Returns:
            Dictionary with current timestamp
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "formatted": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    def _build_prompt(
        self,
        conversation_id: str,
        user_message: str,
        retrieved_docs: List[RetrievalResult],
    ) -> str:
        """Build the prompt for LLM inference.

        Args:
            conversation_id: Conversation ID
            user_message: Current user message
            retrieved_docs: Retrieved relevant documents

        Returns:
            Complete prompt string for LLM
        """
        prompt_parts = []

        # System prompt
        if self.config.system_prompt:
            prompt_parts.append(f"System: {self.config.system_prompt}\n")

        # Conversation history
        history = self.memory.get_conversation_context(
            conversation_id,
            window_size=self.config.memory_window,
        )
        if history:
            prompt_parts.append(f"Conversation History:\n{history}\n")

        # Retrieved context
        if retrieved_docs:
            prompt_parts.append("Retrieved Documents:")
            for i, doc in enumerate(retrieved_docs, 1):
                prompt_parts.append(
                    f"{i}. Source: {doc.source}\n"
                    f"   Content: {doc.content[:500]}...\n"
                    f"   Relevance: {doc.score:.2%}"
                )
            prompt_parts.append("")

        # Current message
        prompt_parts.append(f"User: {user_message}")
        prompt_parts.append("Assistant:")

        return "\n".join(prompt_parts)

    def _invoke_llm(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        thinking_callback: Optional[Callable[[str], None]] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        """Invoke LLM to generate response.

        When *stream_callback* is provided, tokens are forwarded to the callback
        as they arrive from Ollama, enabling real-time streaming in the UI.
        Thinking content (chain-of-thought inside <think> tags) is filtered
        from the token stream and optionally forwarded to *thinking_callback*.

        Args:
            prompt: Complete prompt for LLM
            stream_callback: Optional callback invoked with each token chunk.
            thinking_callback: Optional callback invoked once with the full
                <think> block content after generation completes.
            conversation_id: Optional conversation ID for observability tracking

        Returns:
            Generated response text (full string, reasoning stripped)
        """
        import time
        start_time = time.time()

        try:
            response = self.ollama_client.generate(
                model=self.config.model_name,
                prompt=prompt,
                system=self.config.system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                on_token=stream_callback,
                on_thinking=thinking_callback,
            )

            # Track LLM generation in Langfuse
            if self.observability and conversation_id:
                duration_ms = (time.time() - start_time) * 1000
                self.observability.track_llm_generation(
                    conversation_id=conversation_id,
                    model=self.config.model_name,
                    prompt=prompt,
                    response=response,
                    duration_ms=duration_ms,
                    metadata={
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                    },
                )
            
            # Track LLM generation metrics in Prometheus
            track_llm_generation(
                model=self.config.model_name,
                input_tokens=len(prompt.split()),  # Approximate token count
                output_tokens=len(response.split()),  # Approximate token count
                duration_seconds=time.time() - start_time
            )

            return response

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise

    def _extract_sources(self, retrieved_docs: List[RetrievalResult]) -> List[str]:
        """Extract unique source documents from retrieval results.

        Args:
            retrieved_docs: Retrieved documents

        Returns:
            List of unique source identifiers
        """
        sources = set()
        for doc in retrieved_docs:
            sources.add(doc.source)
        return sorted(list(sources))

    def _format_response_with_sources(
        self,
        response: str,
        retrieved_docs: List[RetrievalResult],
    ) -> str:
        """Format response with source attribution.

        Args:
            response: Generated response text
            retrieved_docs: Retrieved documents

        Returns:
            Formatted response with sources
        """
        formatted_parts = [response]

        if retrieved_docs:
            sources = self._extract_sources(retrieved_docs)
            formatted_parts.append("\n\n**Sources:**")
            for source in sources:
                formatted_parts.append(f"- {source}")

        return "\n".join(formatted_parts)

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[AgentMessage]:
        """Get message history for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to return

        Returns:
            List of messages in chronological order
        """
        return self.memory.get_conversation_history(conversation_id, limit)

    def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """End and clean up a conversation.

        Args:
            conversation_id: Conversation ID to end

        Returns:
            Conversation summary
        """
        summary = self.memory.get_conversation_summary(conversation_id)
        self.memory.delete_conversation(conversation_id)
        logger.info(f"Ended conversation {conversation_id}")
        return summary
