"""Integration tests for Chainlit chat flow.

Validates session lifecycle and recovery behavior using mocked Chainlit runtime.
"""

import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest


def _load_main_module() -> object:
    """Import and reload `src.ui.main` so patched Chainlit module is used."""
    module = importlib.import_module("src.ui.main")
    return importlib.reload(module)


@pytest.mark.integration
class TestChatSessionLifecycle:
    """Test complete chat session lifecycle."""
    
    @pytest.mark.asyncio
    async def test_full_successful_session(self, mock_chainlit):
        """Test complete flow: start -> message -> end."""
        main_module = _load_main_module()
        
        # Mock successful agent initialization
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        mock_agent.process_message = Mock(return_value="Agent response with sources")
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            # Step 1: Start session
            await main_module.start()
            
            # Verify welcome message was sent
            assert len(mock_chainlit["messages"]) >= 1
            
            # Verify session was initialized
            assert mock_chainlit["session"]["agent"] == mock_agent
            assert mock_chainlit["session"]["conversation_id"] == "conv-123"
            assert mock_chainlit["session"]["agent_initialized"] is True
            
            # Step 2: Process message
            user_message = SimpleNamespace(content="What is RAG?", elements=[])
            
            await main_module.main(user_message)
            
            # Verify agent processed the message
            mock_agent.process_message.assert_called_once_with(
                "conv-123",
                "What is RAG?",
                use_retrieval=True
            )
            
            # Step 3: End session
            await main_module.end()
            
            # Session should have completed without errors
            assert mock_chainlit["session"]["agent_initialized"] is True
    
    @pytest.mark.asyncio
    async def test_session_with_initialization_failure(self, mock_chainlit):
        """Test session when agent initialization fails."""
        main_module = _load_main_module()
        
        # Mock failed agent initialization
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (None, None, "Ollama is not responding")
            
            # Start session
            await main_module.start()
            
            # Verify initialization failed
            assert mock_chainlit["session"].get("agent_initialized", True) is False
            assert mock_chainlit["session"].get("agent") is None
            
            # Try to send a message (should fail gracefully)
            user_message = SimpleNamespace(content="Test message", elements=[])
            
            await main_module.main(user_message)
            
            # Should have sent error message
            assert len(mock_chainlit["messages"]) > 0
            assert any("Agent not initialized" in msg.content for msg in mock_chainlit["messages"])
    
    @pytest.mark.asyncio
    async def test_multiple_messages_in_session(self, mock_chainlit):
        """Test multiple messages in single session."""
        main_module = _load_main_module()
        
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        mock_agent.process_message = Mock(side_effect=[
            "First response",
            "Second response",
            "Third response"
        ])
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            # Start session
            await main_module.start()
            
            # Send multiple messages
            messages = ["First", "Second", "Third"]
            for msg_text in messages:
                user_message = SimpleNamespace(content=msg_text, elements=[])
                await main_module.main(user_message)
            
            # Verify all messages were processed
            assert mock_agent.process_message.call_count == 3
            
            # Verify conversation_id stayed the same
            calls = mock_agent.process_message.call_args_list
            for call in calls:
                assert call[0][0] == "conv-123"


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_recovery_from_timeout(self, mock_chainlit):
        """Test that session continues after a timeout."""
        main_module = _load_main_module()
        
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        mock_agent.process_message = Mock(side_effect=[
            TimeoutError("Request timed out"),
            "Successful response"
        ])
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            await main_module.start()
            
            # First message times out
            user_message = SimpleNamespace(content="First", elements=[])
            await main_module.main(user_message)
            
            # Second message succeeds
            user_message.content = "Second"
            await main_module.main(user_message)
            
            # Verify both attempts were made
            assert mock_agent.process_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_recovery_from_connection_error(self, mock_chainlit):
        """Test that session continues after connection error."""
        main_module = _load_main_module()
        
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        mock_agent.process_message = Mock(side_effect=[
            ConnectionError("Service unavailable"),
            "Successful response"
        ])
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            await main_module.start()
            
            # First message has connection error
            user_message = SimpleNamespace(content="First", elements=[])
            await main_module.main(user_message)
            
            # Second message succeeds (connection recovered)
            user_message.content = "Second"
            await main_module.main(user_message)
            
            # Verify both attempts were made
            assert mock_agent.process_message.call_count == 2


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.mark.asyncio
    async def test_rapid_message_sequence(self, mock_chainlit):
        """Test handling of rapid message sequence."""
        main_module = _load_main_module()
        
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        
        # Simulate variable response times
        responses = [f"Response {i}" for i in range(10)]
        mock_agent.process_message = Mock(side_effect=responses)
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            await main_module.start()
            
            # Send 10 messages rapidly
            tasks = []
            for i in range(10):
                user_message = SimpleNamespace(content=f"Message {i}", elements=[])
                task = main_module.main(user_message)
                tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks)
            
            # All messages should have been processed
            assert mock_agent.process_message.call_count == 10
    
    @pytest.mark.asyncio
    async def test_session_without_messages(self, mock_chainlit):
        """Test session that starts but receives no messages."""
        main_module = _load_main_module()
        
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            # Start and immediately end
            await main_module.start()
            await main_module.end()
            
            # Agent should be initialized but never used
            assert mock_chainlit["session"]["agent_initialized"] is True
            assert mock_agent.process_message.call_count == 0
    
    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, mock_chainlit):
        """Test messages with special characters."""
        main_module = _load_main_module()
        
        mock_agent = MagicMock()
        mock_agent.start_conversation = Mock(return_value="conv-123")
        mock_agent.process_message = Mock(return_value="Response")
        
        with patch.object(main_module, "_initialize_agent") as mock_init:
            mock_init.return_value = (mock_agent, "conv-123", None)
            
            await main_module.start()
            
            # Test various special characters
            special_messages = [
                "Hello 👋 emoji test",
                "Code: `print('hello')`",
                "Math: x² + y² = z²",
                "Symbols: @#$%^&*()",
                "Newlines:\nLine 1\nLine 2"
            ]
            
            for msg_text in special_messages:
                user_message = SimpleNamespace(content=msg_text, elements=[])
                await main_module.main(user_message)
            
            # All messages should have been processed
            assert mock_agent.process_message.call_count == len(special_messages)
            
            # Verify exact content was passed
            calls = mock_agent.process_message.call_args_list
            for i, call in enumerate(calls):
                assert call[0][1] == special_messages[i]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
