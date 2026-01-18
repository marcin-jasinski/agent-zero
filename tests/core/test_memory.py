"""Unit tests for agent memory and conversation management.

Tests the ConversationManager and agent message handling.
"""

import pytest
from datetime import datetime

from src.core.memory import ConversationManager
from src.models.agent import AgentMessage, MessageRole, ConversationState


class TestAgentMessage:
    """Test AgentMessage data model."""

    def test_valid_message_creation(self) -> None:
        """Test creating a valid agent message."""
        msg = AgentMessage(
            role=MessageRole.USER,
            content="Test message",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Test message"

    def test_message_with_string_role(self) -> None:
        """Test that string role is converted to enum."""
        msg = AgentMessage(role="user", content="Test")
        assert msg.role == MessageRole.USER
        assert isinstance(msg.role, MessageRole)

    def test_message_requires_non_empty_content(self) -> None:
        """Test that message content cannot be empty."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            AgentMessage(role=MessageRole.USER, content="")

    def test_message_invalid_role(self) -> None:
        """Test that invalid role raises error."""
        with pytest.raises(ValueError, match="Invalid role"):
            AgentMessage(role="invalid", content="test")

    def test_message_to_dict(self) -> None:
        """Test converting message to dictionary."""
        msg = AgentMessage(
            role=MessageRole.ASSISTANT,
            content="Response",
            tool_used="retrieve_documents",
        )
        msg_dict = msg.to_dict()

        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "Response"
        assert msg_dict["tool_used"] == "retrieve_documents"
        assert "timestamp" in msg_dict

    def test_message_with_tool_info(self) -> None:
        """Test message with tool execution details."""
        msg = AgentMessage(
            role=MessageRole.ASSISTANT,
            content="Found documents",
            tool_used="search_knowledge_base",
            tool_input={"query": "test"},
            tool_output="3 documents found",
        )
        assert msg.tool_used == "search_knowledge_base"
        assert msg.tool_input["query"] == "test"


class TestConversationState:
    """Test ConversationState."""

    def test_valid_state_creation(self) -> None:
        """Test creating conversation state."""
        state = ConversationState(conversation_id="conv_1")
        assert state.conversation_id == "conv_1"
        assert state.messages == []

    def test_add_message_to_state(self) -> None:
        """Test adding messages to conversation state."""
        state = ConversationState(conversation_id="conv_1")
        msg = AgentMessage(role=MessageRole.USER, content="Hello")
        state.add_message(msg)

        assert len(state.messages) == 1
        assert state.messages[0].content == "Hello"

    def test_add_invalid_message_fails(self) -> None:
        """Test that adding non-message object fails."""
        state = ConversationState(conversation_id="conv_1")
        with pytest.raises(ValueError, match="must be AgentMessage"):
            state.add_message("not a message")

    def test_get_recent_messages(self) -> None:
        """Test retrieving recent messages."""
        state = ConversationState(conversation_id="conv_1")
        for i in range(5):
            state.add_message(
                AgentMessage(role=MessageRole.USER, content=f"Message {i}")
            )

        recent = state.get_recent_messages(limit=3)
        assert len(recent) == 3
        assert recent[0].content == "Message 2"

    def test_clear_messages(self) -> None:
        """Test clearing conversation messages."""
        state = ConversationState(conversation_id="conv_1")
        state.add_message(AgentMessage(role=MessageRole.USER, content="Test"))
        assert len(state.messages) == 1

        state.clear_messages()
        assert len(state.messages) == 0


class TestConversationManager:
    """Test ConversationManager class."""

    def test_manager_initialization(self) -> None:
        """Test initializing conversation manager."""
        manager = ConversationManager(max_conversations=50)
        assert manager.max_conversations == 50

    def test_invalid_max_conversations(self) -> None:
        """Test that invalid max_conversations raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            ConversationManager(max_conversations=0)

    def test_create_conversation(self) -> None:
        """Test creating a conversation."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        assert conv_id is not None
        assert isinstance(conv_id, str)
        assert conv_id in manager.list_conversations()

    def test_create_conversation_with_metadata(self) -> None:
        """Test creating conversation with metadata."""
        manager = ConversationManager()
        metadata = {"user": "test_user", "session": "123"}
        conv_id = manager.create_conversation(metadata=metadata)

        summary = manager.get_conversation_summary(conv_id)
        assert summary["metadata"]["user"] == "test_user"

    def test_max_conversations_limit(self) -> None:
        """Test that max conversations limit is enforced."""
        manager = ConversationManager(max_conversations=3)

        # Create max conversations
        for _ in range(3):
            manager.create_conversation()

        # Next one should fail
        with pytest.raises(RuntimeError, match="Maximum conversations"):
            manager.create_conversation()

    def test_add_message_to_conversation(self) -> None:
        """Test adding messages to conversation."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        msg = manager.add_message(
            conv_id,
            MessageRole.USER,
            "Hello assistant",
        )

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello assistant"

    def test_add_message_to_nonexistent_conversation(self) -> None:
        """Test adding message to nonexistent conversation fails."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            manager.add_message("nonexistent", MessageRole.USER, "Hello")

    def test_add_message_with_tool_info(self) -> None:
        """Test adding message with tool information."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        msg = manager.add_message(
            conv_id,
            MessageRole.ASSISTANT,
            "Found results",
            tool_used="search",
            tool_input={"query": "test"},
            tool_output="2 results",
        )

        assert msg.tool_used == "search"
        assert msg.tool_input["query"] == "test"

    def test_get_conversation_history(self) -> None:
        """Test retrieving conversation history."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        # Add messages
        for i in range(3):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            manager.add_message(conv_id, role, f"Message {i}")

        history = manager.get_conversation_history(conv_id)
        assert len(history) == 3

    def test_get_conversation_history_limit(self) -> None:
        """Test retrieving limited conversation history."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        # Add multiple messages
        for i in range(10):
            manager.add_message(conv_id, MessageRole.USER, f"Message {i}")

        # Get only last 3
        history = manager.get_conversation_history(conv_id, limit=3)
        assert len(history) == 3

    def test_get_nonexistent_conversation_history(self) -> None:
        """Test getting history for nonexistent conversation."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            manager.get_conversation_history("nonexistent")

    def test_get_conversation_context(self) -> None:
        """Test getting formatted conversation context."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        manager.add_message(conv_id, MessageRole.USER, "What is AI?")
        manager.add_message(conv_id, MessageRole.ASSISTANT, "AI is artificial intelligence")

        context = manager.get_conversation_context(conv_id)

        assert "User: What is AI?" in context
        assert "Assistant: AI is artificial intelligence" in context

    def test_clear_conversation(self) -> None:
        """Test clearing conversation messages."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        manager.add_message(conv_id, MessageRole.USER, "Test")
        manager.add_message(conv_id, MessageRole.ASSISTANT, "Response")

        manager.clear_conversation(conv_id)

        history = manager.get_conversation_history(conv_id)
        assert len(history) == 0

    def test_delete_conversation(self) -> None:
        """Test deleting a conversation."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        manager.add_message(conv_id, MessageRole.USER, "Test")

        manager.delete_conversation(conv_id)

        assert conv_id not in manager.list_conversations()

    def test_delete_nonexistent_conversation(self) -> None:
        """Test deleting nonexistent conversation fails."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            manager.delete_conversation("nonexistent")

    def test_get_conversation_summary(self) -> None:
        """Test getting conversation summary."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        # Add different types of messages
        manager.add_message(conv_id, MessageRole.USER, "Question 1")
        manager.add_message(conv_id, MessageRole.ASSISTANT, "Answer 1", tool_used="search")
        manager.add_message(conv_id, MessageRole.USER, "Question 2")
        manager.add_message(conv_id, MessageRole.ASSISTANT, "Answer 2", tool_used="retrieve")

        summary = manager.get_conversation_summary(conv_id)

        assert summary["conversation_id"] == conv_id
        assert summary["message_count"] == 4
        assert summary["user_messages"] == 2
        assert summary["assistant_messages"] == 2
        assert "search" in summary["tools_used"]

    def test_list_conversations(self) -> None:
        """Test listing all conversations."""
        manager = ConversationManager()

        conv_ids = [manager.create_conversation() for _ in range(3)]

        listed = manager.list_conversations()
        assert len(listed) == 3
        assert all(cid in listed for cid in conv_ids)

    def test_summarize_conversation(self) -> None:
        """Test conversation summary generation."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        manager.add_message(conv_id, MessageRole.USER, "What is machine learning?")
        manager.add_message(conv_id, MessageRole.ASSISTANT, "ML is a subset of AI")

        summary = manager.summarize_conversation(conv_id)

        assert "Conversation started at" in summary
        assert "questions" in summary or "Question" in summary

    def test_summarize_empty_conversation(self) -> None:
        """Test summarizing empty conversation."""
        manager = ConversationManager()
        conv_id = manager.create_conversation()

        summary = manager.summarize_conversation(conv_id)
        assert "Empty conversation" in summary
