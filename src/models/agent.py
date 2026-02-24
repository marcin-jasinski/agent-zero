"""Agent models for Agent Zero conversation system.

This module defines data structures for agent configuration, messages,
and conversation state management.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from src.config import get_config


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class AgentMessage:
    """Represents a single message in a multi-turn conversation.

    Attributes:
        role: Role of message sender (user, assistant, system, tool)
        content: Message text content
        timestamp: When the message was created
        tool_used: Name of tool used (if role is assistant or tool)
        tool_input: Input passed to tool
        tool_output: Output from tool execution
        metadata: Additional message metadata
    """

    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_used: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate message after initialization."""
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if isinstance(self.role, str):
            try:
                self.role = MessageRole(self.role)
            except ValueError:
                raise ValueError(f"Invalid role: {self.role}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_used": self.tool_used,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "metadata": self.metadata,
        }


@dataclass
class AgentConfig:
    """Configuration for Agent Zero's behavior and capabilities.

    Attributes:
        model_name: Name of the LLM model to use
        temperature: Sampling temperature (0.0-1.0, higher = more creative)
        max_tokens: Maximum tokens in generated response
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        system_prompt: System prompt to guide agent behavior
        tools: List of available tools
        memory_window: Number of previous messages to include in context
    """

    model_name: str = field(default_factory=lambda: get_config().ollama.model)
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    system_prompt: str = ""
    tools: List[str] = field(
        default_factory=lambda: [
            "retrieve_documents",
            "search_knowledge_base",
            "get_current_time",
        ]
    )
    memory_window: int = 10

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError(f"temperature must be 0.0-1.0, got {self.temperature}")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError(f"top_p must be 0.0-1.0, got {self.top_p}")
        if self.top_k <= 0:
            raise ValueError(f"top_k must be positive, got {self.top_k}")
        if self.memory_window < 0:
            raise ValueError(f"memory_window must be non-negative, got {self.memory_window}")


@dataclass
class ConversationState:
    """State of a single conversation session.

    Attributes:
        conversation_id: Unique identifier for this conversation
        messages: List of messages in chronological order
        created_at: When conversation was started
        updated_at: When conversation was last updated
        metadata: Session metadata (user, context, etc.)
    """

    conversation_id: str
    messages: List[AgentMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: AgentMessage) -> None:
        """Add a message to the conversation.

        Args:
            message: Message to add

        Raises:
            ValueError: If message is invalid
        """
        if not isinstance(message, AgentMessage):
            raise ValueError("message must be AgentMessage instance")
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, limit: Optional[int] = None) -> List[AgentMessage]:
        """Get recent messages from conversation.

        Args:
            limit: Maximum number of messages to return (None = all)

        Returns:
            List of recent AgentMessage objects
        """
        if limit is None or limit <= 0:
            return self.messages
        return self.messages[-limit:]

    def clear_messages(self) -> None:
        """Clear all messages from conversation."""
        self.messages = []
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
