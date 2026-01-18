"""Chat Interface Component for Agent Zero.

Implements the main chat tab with message history, input handling,
and agent response generation.
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def initialize_chat_session() -> None:
    """Initialize chat session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None


def render_chat_interface() -> None:
    """Render the chat interface component.

    Displays message history, handles user input, and sends queries
    to the agent for processing.
    """
    st.header("💬 Chat Interface")

    # Initialize session state
    initialize_chat_session()

    # Create two columns: messages and sidebar
    col_main, col_sidebar = st.columns([4, 1])

    with col_main:
        # Message history container
        st.subheader("Conversation History")

        # Display existing messages
        message_container = st.container()
        with message_container:
            if st.session_state.messages:
                for msg in st.session_state.messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")

                    if role == "user":
                        with st.chat_message("user"):
                            st.write(content)
                    elif role == "assistant":
                        with st.chat_message("assistant"):
                            st.write(content)
                    elif role == "system":
                        with st.chat_message("assistant"):
                            st.info(content)
            else:
                st.info("No messages yet. Start a conversation!")

        st.divider()

        # Input area
        st.subheader("Send Message")
        user_input = st.text_area(
            "Your message:",
            placeholder="Ask the agent a question or request...",
            height=100,
            label_visibility="collapsed",
        )

        col_send, col_clear = st.columns([3, 1])

        with col_send:
            if st.button("📤 Send", use_container_width=True):
                if user_input.strip():
                    # Add user message to history
                    st.session_state.messages.append({"role": "user", "content": user_input})

                    # Process message with agent
                    with st.spinner("⏳ Agent is thinking..."):
                        try:
                            # Initialize agent if not already done
                            if "agent" not in st.session_state:
                                from src.core.agent import AgentOrchestrator
                                from src.core.retrieval import RetrievalEngine
                                from src.services.ollama_client import OllamaClient
                                from src.services.qdrant_client import QdrantClient
                                from src.services.meilisearch_client import MeilisearchClient
                                from src.config import get_config
                                
                                config = get_config()
                                ollama = OllamaClient(config.ollama)
                                qdrant = QdrantClient(config.qdrant)
                                meilisearch = MeilisearchClient(config.meilisearch)
                                retrieval = RetrievalEngine(ollama, qdrant, meilisearch)
                                
                                st.session_state.agent = AgentOrchestrator(ollama, retrieval)
                                st.session_state.conversation_id = st.session_state.agent.start_conversation()
                            
                            # Get response from agent
                            response = st.session_state.agent.process_message(
                                st.session_state.conversation_id,
                                user_input,
                                use_retrieval=True
                            )
                            
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": response,
                                }
                            )
                        except Exception as e:
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": f"Error: {str(e)}. Please try again.",
                                }
                            )
                            import logging
                            logging.error(f"Agent processing error: {e}", exc_info=True)

                    st.rerun()
                else:
                    st.warning("Please enter a message.")

        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

    with col_sidebar:
        st.subheader("Info")
        st.metric(
            "Messages",
            len(st.session_state.messages),
        )

        if st.session_state.messages:
            st.metric(
                "Last Role",
                st.session_state.messages[-1].get("role", "unknown").capitalize(),
            )

        # Export conversation
        if st.button("💾 Export"):
            import json

            conversation_json = json.dumps(st.session_state.messages, indent=2)
            st.download_button(
                "Download Conversation",
                conversation_json,
                "conversation.json",
                "application/json",
            )
