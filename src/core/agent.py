"""Agent orchestration for Agent Zero with LangChain integration.

This module implements the main agent that orchestrates retrieval,
tool calling, and LLM invocation for multi-turn conversations.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from src.core.retrieval import RetrievalEngine
from src.core.memory import ConversationManager
from src.models.agent import AgentConfig, AgentMessage, MessageRole, ConversationState
from src.models.retrieval import RetrievalResult
from src.services.ollama_client import OllamaClient

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
    ) -> None:
        """Initialize the agent orchestrator.

        Args:
            ollama_client: Client for LLM inference
            retrieval_engine: Engine for document retrieval
            config: Agent configuration (uses defaults if not provided)
        """
        self.ollama_client = ollama_client
        self.retrieval_engine = retrieval_engine
        self.config = config or AgentConfig()
        self.memory = ConversationManager()

        # Define available tools
        self.tools = {
            "retrieve_documents": self._retrieve_documents,
            "search_knowledge_base": self._search_knowledge_base,
            "get_current_time": self._get_current_time,
        }

        logger.info(f"Initialized AgentOrchestrator with model {self.config.model_name}")

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

        Returns:
            Agent response text with source attribution

        Raises:
            ValueError: If conversation or user message is invalid
        """
        if not user_message or not user_message.strip():
            raise ValueError("User message cannot be empty")

        try:
            # Add user message to history
            self.memory.add_message(
                conversation_id,
                MessageRole.USER,
                user_message,
            )

            # Retrieve relevant documents
            retrieved_docs: List[RetrievalResult] = []
            if use_retrieval:
                try:
                    retrieved_docs = self.retrieval_engine.retrieve_relevant_docs(
                        user_message,
                        top_k=5,
                    )
                    logger.info(f"Retrieved {len(retrieved_docs)} documents")
                except Exception as e:
                    logger.warning(f"Document retrieval failed: {e}")

            # Build context
            context = self._build_prompt(
                conversation_id,
                user_message,
                retrieved_docs,
            )

            # Generate response
            response_text = self._invoke_llm(context, stream_callback)

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

            # Format response with sources
            formatted_response = self._format_response_with_sources(
                response_text,
                retrieved_docs,
            )

            logger.info(f"Generated response for conversation {conversation_id}")
            return formatted_response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise

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
    ) -> str:
        """Invoke LLM to generate response.

        Args:
            prompt: Complete prompt for LLM
            stream_callback: Optional callback for streaming tokens

        Returns:
            Generated response text
        """
        try:
            response = self.ollama_client.chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.config.model_name,
                stream=stream_callback is not None,
            )

            if stream_callback and isinstance(response, str):
                # If streaming, invoke callback
                stream_callback(response)
                return response
            elif isinstance(response, str):
                return response
            else:
                # Handle response as dict/object
                return response.get("message", {}).get("content", "")

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
