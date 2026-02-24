"""Conversation memory management for Agent Zero.

This module handles multi-turn conversation state, message history,
and context window management.
"""

import logging
from typing import Dict, List, Optional
from uuid import uuid4

from src.models.agent import AgentMessage, ConversationState, MessageRole

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation state and multi-turn message history.

    This class maintains in-memory conversation state, handles message
    persistence within a session, and manages context windows for the LLM.
    """

    def __init__(self, max_conversations: int = 100) -> None:
        """Initialize conversation manager.

        Args:
            max_conversations: Maximum number of active conversations to store
        """
        if max_conversations <= 0:
            raise ValueError("max_conversations must be positive")

        self.max_conversations = max_conversations
        self._conversations: Dict[str, ConversationState] = {}

    def create_conversation(
        self,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Create a new conversation session.

        Args:
            metadata: Optional metadata for the conversation

        Returns:
            Unique conversation ID

        Raises:
            RuntimeError: If maximum conversations reached
        """
        if len(self._conversations) >= self.max_conversations:
            raise RuntimeError(
                f"Maximum conversations ({self.max_conversations}) reached"
            )

        conversation_id = str(uuid4())
        self._conversations[conversation_id] = ConversationState(
            conversation_id=conversation_id,
            metadata=metadata or {},
        )

        logger.info("Created conversation %s", conversation_id)
        return conversation_id

    def add_message(  # pylint: disable=too-many-positional-arguments
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        tool_used: Optional[str] = None,
        tool_input: Optional[Dict] = None,
        tool_output: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AgentMessage:
        """Add a message to a conversation.

        Args:
            conversation_id: ID of target conversation
            role: Message role (user, assistant, system, tool)
            content: Message text
            tool_used: Optional name of tool used
            tool_input: Optional input to tool
            tool_output: Optional output from tool
            metadata: Optional message metadata

        Returns:
            Created AgentMessage object

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        message = AgentMessage(
            role=role,
            content=content,
            tool_used=tool_used,
            tool_input=tool_input,
            tool_output=tool_output,
            metadata=metadata or {},
        )

        self._conversations[conversation_id].add_message(message)
        logger.debug(
            "Added %s message to conversation %s", role.value, conversation_id
        )

        return message

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[AgentMessage]:
        """Get message history for a conversation.

        Args:
            conversation_id: ID of target conversation
            limit: Maximum number of messages to return

        Returns:
            List of AgentMessage objects in chronological order

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = self._conversations[conversation_id]
        return conversation.get_recent_messages(limit)

    def get_conversation_context(
        self,
        conversation_id: str,
        window_size: int = 10,
    ) -> str:
        """Get formatted conversation context for LLM.

        Formats the recent message history as a string suitable for
        passing to the language model as context.

        Args:
            conversation_id: ID of target conversation
            window_size: Number of recent messages to include

        Returns:
            Formatted conversation context string

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        messages = self.get_conversation_history(
            conversation_id,
            limit=window_size,
        )

        context_parts = []
        for msg in messages:
            role_str = msg.role.value.capitalize()
            context_parts.append(f"{role_str}: {msg.content}")
            if msg.tool_used:
                context_parts.append(f"  (Tool: {msg.tool_used})")

        return "\n".join(context_parts)

    def clear_conversation(self, conversation_id: str) -> None:
        """Clear all messages from a conversation.

        Args:
            conversation_id: ID of target conversation

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        self._conversations[conversation_id].clear_messages()
        logger.info("Cleared messages in conversation %s", conversation_id)

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete an entire conversation.

        Args:
            conversation_id: ID of target conversation

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        del self._conversations[conversation_id]
        logger.info("Deleted conversation %s", conversation_id)

    def get_conversation_summary(
        self,
        conversation_id: str,
    ) -> Dict:
        """Get summary information about a conversation.

        Args:
            conversation_id: ID of target conversation

        Returns:
            Dictionary with conversation metadata and statistics

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = self._conversations[conversation_id]
        messages = conversation.messages

        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "user_messages": sum(
                1 for m in messages if m.role == MessageRole.USER
            ),
            "assistant_messages": sum(
                1 for m in messages if m.role == MessageRole.ASSISTANT
            ),
            "tools_used": set(
                m.tool_used for m in messages if m.tool_used
            ),
            "metadata": conversation.metadata,
        }

    def list_conversations(self) -> List[str]:
        """Get list of all active conversation IDs.

        Returns:
            List of conversation identifiers
        """
        return list(self._conversations.keys())

    def summarize_conversation(
        self,
        conversation_id: str,
        max_length: int = 500,
    ) -> str:
        """Summarize a conversation (simplified version without LLM).

        For a proper summary, this should use the LLM, but for now
        returns a basic text summary.

        Args:
            conversation_id: ID of target conversation
            max_length: Maximum summary length

        Returns:
            Conversation summary string

        Raises:
            ValueError: If conversation doesn't exist
        """
        if conversation_id not in self._conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = self._conversations[conversation_id]
        messages = conversation.messages

        if not messages:
            return "Empty conversation."

        # Simple summary: list user messages and assistant responses
        summary_parts = [
            f"Conversation started at {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        ]

        user_queries = [m.content for m in messages if m.role == MessageRole.USER]
        if user_queries:
            summary_parts.append(f"\nUser asked {len(user_queries)} questions:")
            for query in user_queries[:3]:  # Show first 3
                summary_parts.append(f"  - {query[:100]}...")

        if len(user_queries) > 3:
            summary_parts.append(f"  ... and {len(user_queries) - 3} more")

        tools_used = set(m.tool_used for m in messages if m.tool_used)
        if tools_used:
            summary_parts.append(f"\nTools used: {', '.join(tools_used)}")

        summary = "\n".join(summary_parts)
        return summary[: max_length]
