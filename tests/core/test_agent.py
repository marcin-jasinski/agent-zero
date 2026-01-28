"""Unit tests for agent orchestration.

Tests the AgentOrchestrator class covering multi-turn conversations,
tool invocation, and response generation.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.agent import AgentOrchestrator
from src.models.agent import AgentConfig, MessageRole
from src.models.retrieval import RetrievalResult


class TestAgentConfig:
    """Test AgentConfig."""

    def test_valid_config(self) -> None:
        """Test creating valid agent config."""
        config = AgentConfig(
            model_name="test-model",
            temperature=0.5,
            max_tokens=1000,
        )
        assert config.model_name == "test-model"
        assert config.temperature == 0.5

    def test_invalid_temperature(self) -> None:
        """Test that temperature must be 0.0-1.0."""
        with pytest.raises(ValueError, match="temperature"):
            AgentConfig(temperature=1.5)

    def test_invalid_max_tokens(self) -> None:
        """Test that max_tokens must be positive."""
        with pytest.raises(ValueError, match="max_tokens"):
            AgentConfig(max_tokens=-1)

    def test_invalid_memory_window(self) -> None:
        """Test that memory_window must be non-negative."""
        with pytest.raises(ValueError, match="memory_window"):
            AgentConfig(memory_window=-1)


class TestAgentOrchestrator:
    """Test AgentOrchestrator class."""

    @pytest.fixture
    def mock_clients(self) -> tuple:
        """Create mock service clients."""
        ollama_mock = Mock()
        retrieval_mock = Mock()
        return ollama_mock, retrieval_mock

    @pytest.fixture
    def agent(self, mock_clients) -> AgentOrchestrator:
        """Create AgentOrchestrator with mocked clients."""
        ollama, retrieval = mock_clients
        config = AgentConfig(system_prompt="You are a helpful assistant")
        return AgentOrchestrator(ollama, retrieval, config)

    def test_agent_initialization(self, mock_clients) -> None:
        """Test agent initialization."""
        ollama, retrieval = mock_clients
        agent = AgentOrchestrator(ollama, retrieval)

        assert agent.ollama_client is not None
        assert agent.retrieval_engine is not None
        assert len(agent.tools) == 3

    def test_start_conversation(self, agent) -> None:
        """Test starting a conversation."""
        conv_id = agent.start_conversation()

        assert conv_id is not None
        assert isinstance(conv_id, str)

    def test_start_conversation_with_metadata(self, agent) -> None:
        """Test starting conversation with metadata."""
        metadata = {"user_id": "123", "session": "abc"}
        conv_id = agent.start_conversation(metadata=metadata)

        summary = agent.memory.get_conversation_summary(conv_id)
        assert summary["metadata"]["user_id"] == "123"

    def test_process_empty_message_fails(self, agent) -> None:
        """Test that empty message raises error."""
        conv_id = agent.start_conversation()

        with pytest.raises(ValueError, match="cannot be empty"):
            agent.process_message(conv_id, "")

    def test_process_message_adds_to_history(self, agent) -> None:
        """Test that processed message is added to history."""
        conv_id = agent.start_conversation()

        agent.ollama_client.generate = Mock(return_value="Response text")  # Mock generate, not chat
        agent.retrieval_engine.retrieve_relevant_docs = Mock(return_value=[])

        agent.process_message(conv_id, "Hello assistant")

        history = agent.memory.get_conversation_history(conv_id)
        # Should have: system message + user message + assistant response
        assert any(m.role == MessageRole.USER for m in history)
        assert any(m.role == MessageRole.ASSISTANT for m in history)

    def test_process_message_with_retrieval(self, agent) -> None:
        """Test message processing with document retrieval."""
        conv_id = agent.start_conversation()

        agent.ollama_client.generate = Mock(return_value="Generated response")

        mock_docs = [
            RetrievalResult(
                id="doc_1",
                content="Relevant content",
                source="test.pdf",
                chunk_index=0,
                score=0.95,
            )
        ]
        agent.retrieval_engine.retrieve_relevant_docs = Mock(return_value=mock_docs)

        response = agent.process_message(conv_id, "What is in the documents?")

        assert "Generated response" in response
        assert agent.retrieval_engine.retrieve_relevant_docs.called

    def test_process_message_without_retrieval(self, agent) -> None:
        """Test message processing without retrieval."""
        conv_id = agent.start_conversation()

        agent.ollama_client.generate = Mock(return_value="Simple response")

        response = agent.process_message(conv_id, "Hello", use_retrieval=False)

        assert "Simple response" in response
        agent.retrieval_engine.retrieve_relevant_docs.assert_not_called()

    def test_retrieve_documents_tool(self, agent) -> None:
        """Test retrieve_documents tool."""
        agent.retrieval_engine.retrieve_relevant_docs = Mock(
            return_value=[
                RetrievalResult(
                    id="doc_1",
                    content="Content 1",
                    source="file1.pdf",
                    chunk_index=0,
                    score=0.9,
                )
            ]
        )

        results = agent._retrieve_documents("test query", top_k=5)

        assert len(results) == 1
        assert results[0]["source"] == "file1.pdf"
        assert results[0]["score"] == 0.9

    def test_search_knowledge_base_tool(self, agent) -> None:
        """Test search_knowledge_base tool."""
        agent.retrieval_engine.search_with_context = Mock(
            return_value=[
                RetrievalResult(
                    id="doc_1",
                    content="Content",
                    source="file.pdf",
                    chunk_index=0,
                    score=0.85,
                )
            ]
        )

        result = agent._search_knowledge_base("test query")

        assert result["count"] == 1
        assert result["query"] == "test query"
        assert len(result["results"]) == 1

    def test_get_current_time_tool(self, agent) -> None:
        """Test get_current_time tool."""
        result = agent._get_current_time()

        assert "timestamp" in result
        assert "formatted" in result
        assert isinstance(result["timestamp"], str)

    def test_retrieve_documents_tool_handles_errors(self, agent) -> None:
        """Test that retrieve_documents tool handles errors gracefully."""
        agent.retrieval_engine.retrieve_relevant_docs = Mock(
            side_effect=Exception("Retrieval failed")
        )

        results = agent._retrieve_documents("test")

        assert results == []

    def test_build_prompt_includes_system_message(self, agent) -> None:
        """Test that prompt includes system message."""
        conv_id = agent.start_conversation()

        prompt = agent._build_prompt(conv_id, "test query", [])

        assert "helpful assistant" in prompt

    def test_build_prompt_includes_history(self, agent) -> None:
        """Test that prompt includes conversation history."""
        conv_id = agent.start_conversation()
        agent.memory.add_message(conv_id, MessageRole.USER, "First question")
        agent.memory.add_message(conv_id, MessageRole.ASSISTANT, "First answer")

        prompt = agent._build_prompt(conv_id, "Second question", [])

        assert "Conversation History" in prompt
        assert "First question" in prompt

    def test_build_prompt_includes_retrieved_docs(self, agent) -> None:
        """Test that prompt includes retrieved documents."""
        conv_id = agent.start_conversation()

        docs = [
            RetrievalResult(
                id="doc_1",
                content="Important information",
                source="test.pdf",
                chunk_index=0,
                score=0.95,
            )
        ]

        prompt = agent._build_prompt(conv_id, "test query", docs)

        assert "Retrieved Documents" in prompt
        assert "Important information" in prompt
        assert "test.pdf" in prompt

    def test_extract_sources(self, agent) -> None:
        """Test extracting sources from documents."""
        docs = [
            RetrievalResult(
                id="doc_1", content="c1", source="file1.pdf", chunk_index=0, score=0.9
            ),
            RetrievalResult(
                id="doc_2", content="c2", source="file1.pdf", chunk_index=1, score=0.8
            ),
            RetrievalResult(
                id="doc_3", content="c3", source="file2.pdf", chunk_index=0, score=0.7
            ),
        ]

        sources = agent._extract_sources(docs)

        assert len(sources) == 2
        assert "file1.pdf" in sources
        assert "file2.pdf" in sources

    def test_format_response_with_sources(self, agent) -> None:
        """Test formatting response with source attribution."""
        response = "This is the answer"
        docs = [
            RetrievalResult(
                id="doc_1", content="c1", source="doc1.pdf", chunk_index=0, score=0.9
            ),
            RetrievalResult(
                id="doc_2", content="c2", source="doc2.pdf", chunk_index=0, score=0.8
            ),
        ]

        formatted = agent._format_response_with_sources(response, docs)

        assert "This is the answer" in formatted
        assert "Sources:" in formatted
        assert "doc1.pdf" in formatted
        assert "doc2.pdf" in formatted

    def test_get_conversation_history(self, agent) -> None:
        """Test retrieving conversation history."""
        conv_id = agent.start_conversation()

        agent.memory.add_message(conv_id, MessageRole.USER, "Question 1")
        agent.memory.add_message(conv_id, MessageRole.ASSISTANT, "Answer 1")

        history = agent.get_conversation_history(conv_id)

        assert len(history) >= 2
        user_msgs = [m for m in history if m.role == MessageRole.USER]
        assert len(user_msgs) >= 1

    def test_end_conversation(self, agent) -> None:
        """Test ending a conversation."""
        conv_id = agent.start_conversation()

        agent.memory.add_message(conv_id, MessageRole.USER, "Test")

        summary = agent.end_conversation(conv_id)

        assert summary["conversation_id"] == conv_id
        # Conversation should be deleted
        assert conv_id not in agent.memory.list_conversations()

    def test_multi_turn_conversation(self, agent) -> None:
        """Test multi-turn conversation flow."""
        conv_id = agent.start_conversation()

        agent.ollama_client.generate = Mock(
            side_effect=["Response 1", "Response 2", "Response 3"]
        )
        agent.retrieval_engine.retrieve_relevant_docs = Mock(return_value=[])

        # First turn
        agent.process_message(conv_id, "First question")
        history1 = len(agent.memory.get_conversation_history(conv_id))

        # Second turn
        agent.process_message(conv_id, "Second question")
        history2 = len(agent.memory.get_conversation_history(conv_id))

        # Third turn
        agent.process_message(conv_id, "Third question")
        history3 = len(agent.memory.get_conversation_history(conv_id))

        # History should grow (each call adds user + assistant messages)
        assert history1 < history2
        assert history2 < history3

    def test_memory_window_limits_context(self, agent) -> None:
        """Test that memory window limits context."""
        agent.config.memory_window = 2
        conv_id = agent.start_conversation()

        # Add many messages
        for i in range(5):
            agent.memory.add_message(conv_id, MessageRole.USER, f"Message {i}")

        # Build prompt should only use recent messages
        prompt = agent._build_prompt(conv_id, "Current query", [])

        # The prompt should include conversation history but limited
        history_lines = [l for l in prompt.split("\n") if "Message" in l]
        assert len(history_lines) <= 2  # memory_window=2
