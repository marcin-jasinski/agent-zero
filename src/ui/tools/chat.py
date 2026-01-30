"""Chat Interface Component for Agent Zero.

Implements the main chat tab with message history, input handling,
and agent response generation.

Phase 5 Step 19.5: Enhanced with progress indicators and error visibility.
"""

import logging
import time
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def initialize_chat_session() -> None:
    """Initialize chat session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False
    if "last_error" not in st.session_state:
        st.session_state.last_error = None


def _initialize_agent() -> tuple[bool, Optional[str]]:
    """Initialize the agent with proper error handling.
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        from src.core.agent import AgentOrchestrator
        from src.core.retrieval import RetrievalEngine
        from src.services.ollama_client import OllamaClient
        from src.services.qdrant_client import QdrantVectorClient
        from src.services.meilisearch_client import MeilisearchClient
        
        # Initialize services with health checks
        ollama = OllamaClient()
        if not ollama.is_healthy():
            return False, "Ollama service is not responding. Please ensure Ollama is running (`docker-compose up -d ollama`)."
        
        qdrant = QdrantVectorClient()
        if not qdrant.is_healthy():
            return False, "Qdrant service is not responding. Please ensure Qdrant is running (`docker-compose up -d qdrant`)."
        
        meilisearch = MeilisearchClient()
        if not meilisearch.is_healthy():
            return False, "Meilisearch service is not responding. Please ensure Meilisearch is running (`docker-compose up -d meilisearch`)."
        
        retrieval = RetrievalEngine(ollama, qdrant, meilisearch)
        
        st.session_state.agent = AgentOrchestrator(ollama, retrieval)
        st.session_state.conversation_id = st.session_state.agent.start_conversation()
        st.session_state.agent_initialized = True
        
        return True, None
        
    except ImportError as e:
        logger.error(f"Import error during agent initialization: {e}", exc_info=True)
        return False, f"Missing dependency: {str(e)}. Please check your installation."
    except ConnectionError as e:
        logger.error(f"Connection error during agent initialization: {e}", exc_info=True)
        return False, f"Connection failed: {str(e)}. Please check if all services are running."
    except Exception as e:
        logger.error(f"Agent initialization error: {e}", exc_info=True)
        return False, f"Failed to initialize agent: {str(e)}"


def _process_message(user_input: str) -> tuple[str, Optional[str]]:
    """Process a message with the agent.
    
    Args:
        user_input: The user's message
        
    Returns:
        Tuple of (response: str, error_message: Optional[str])
    """
    try:
        start_time = time.time()
        
        response = st.session_state.agent.process_message(
            st.session_state.conversation_id,
            user_input,
            use_retrieval=True
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Agent response generated in {elapsed:.2f}s")
        
        return response, None
        
    except TimeoutError as e:
        logger.error(f"Timeout during message processing: {e}", exc_info=True)
        return "", "The request timed out. The LLM may be busy or the model is too large. Try again or use a smaller model."
    except ConnectionError as e:
        logger.error(f"Connection error during message processing: {e}", exc_info=True)
        return "", "Lost connection to a service. Please check if Ollama, Qdrant, and Meilisearch are running."
    except Exception as e:
        logger.error(f"Error during message processing: {e}", exc_info=True)
        return "", f"Error processing message: {str(e)}"


def render_chat_interface() -> None:
    """Render the chat interface component.

    Displays message history, handles user input, and sends queries
    to the agent for processing.
    """
    st.header("💬 Chat Interface")

    # Initialize session state
    initialize_chat_session()
    
    # Display any previous errors
    if st.session_state.last_error:
        st.error(f"⚠️ {st.session_state.last_error}")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Retry Connection", use_container_width=True):
                st.session_state.last_error = None
                st.session_state.agent_initialized = False
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.rerun()
        st.divider()

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
                    elif role == "error":
                        with st.chat_message("assistant"):
                            st.error(content)
            else:
                st.info("👋 No messages yet. Start a conversation!")
                
                # Show example queries for new users
                st.markdown("### 💡 Try asking:")
                example_queries = [
                    "What is RAG and how does it work?",
                    "Explain embeddings in simple terms",
                    "How does Agent Zero process documents?",
                    "What are the components of an AI agent?",
                ]
                for query in example_queries:
                    if st.button(f"📝 {query}", key=f"example_{query[:20]}"):
                        st.session_state.messages.append({"role": "user", "content": query})
                        st.rerun()

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

                    # Initialize agent if needed
                    if not st.session_state.agent_initialized or "agent" not in st.session_state:
                        with st.spinner("🔄 Initializing Agent Zero... (connecting to services)"):
                            success, error = _initialize_agent()
                            if not success:
                                st.session_state.last_error = error
                                st.session_state.messages.append({
                                    "role": "error",
                                    "content": f"⚠️ {error}"
                                })
                                st.rerun()
                                return

                    # Process message with agent
                    progress_placeholder = st.empty()
                    with progress_placeholder.container():
                        with st.spinner("🤔 Agent is thinking... (querying knowledge base and generating response)"):
                            response, error = _process_message(user_input)
                    
                    progress_placeholder.empty()
                    
                    if error:
                        st.session_state.messages.append({
                            "role": "error",
                            "content": f"⚠️ {error}"
                        })
                        st.session_state.last_error = error
                    else:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                        })
                        st.session_state.last_error = None

                    st.rerun()
                else:
                    st.warning("⚠️ Please enter a message.")

        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.last_error = None
                st.rerun()

    with col_sidebar:
        st.subheader("Info")
        
        # Show agent status
        if st.session_state.agent_initialized:
            st.success("🟢 Agent Ready")
        else:
            st.warning("🟡 Agent Idle")
        
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
