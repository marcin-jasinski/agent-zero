"""Chat Interface Component for Agent Zero.

Implements the main chat tab with message history, input handling,
and agent response generation.

Phase 5 Step 19.5: Enhanced with progress indicators and error visibility.
Phase 6: Background processing support for non-blocking operations.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

# Global executor for background processing (shared across sessions)
_executor = ThreadPoolExecutor(max_workers=4)


def initialize_chat_session() -> None:
    """Initialize chat session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False
    if "last_error" not in st.session_state:
        st.session_state.last_error = None
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    # Background processing state
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "processing_future" not in st.session_state:
        st.session_state.processing_future = None
    if "processing_message" not in st.session_state:
        st.session_state.processing_message = ""
    if "processing_start_time" not in st.session_state:
        st.session_state.processing_start_time = None
    if "processing_last_warning_time" not in st.session_state:
        st.session_state.processing_last_warning_time = None


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
        
        logger.info(f"Agent initialized successfully: conversation_id={st.session_state.conversation_id}")
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


def _process_message(user_input: str, agent, conversation_id: str) -> tuple[str, Optional[str]]:
    """Process a message with the agent.
    
    Args:
        user_input: The user's message
        agent: The AgentOrchestrator instance
        conversation_id: The conversation ID
        
    Returns:
        Tuple of (response: str, error_message: Optional[str])
    """
    try:
        # Check if agent is initialized
        if agent is None:
            return "", "Agent not initialized. Please wait for the agent to start."
        
        start_time = time.time()
        
        response = agent.process_message(
            conversation_id,
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


def _background_process_wrapper(user_input: str, agent, conversation_id: str) -> tuple[str, Optional[str]]:
    """Wrapper for background processing that catches all exceptions.
    
    Args:
        user_input: The user's message
        agent: The AgentOrchestrator instance
        conversation_id: The conversation ID
        
    Returns:
        Tuple of (response: str, error_message: Optional[str])
    """
    try:
        return _process_message(user_input, agent, conversation_id)
    except Exception as e:
        logger.error(f"Uncaught exception in background processing: {e}", exc_info=True)
        return "", f"Unexpected error: {str(e)}"


def _check_processing_status() -> Optional[tuple[str, Optional[str]]]:
    """Check if background processing is complete.
    
    Returns:
        Tuple of (response, error) if complete, None if still processing
    """
    if not st.session_state.processing:
        return None
    
    future: Future = st.session_state.processing_future
    if future is None:
        return None
    
    # Check if processing is done
    if future.done():
        try:
            result = future.result(timeout=0.1)
            st.session_state.processing = False
            st.session_state.processing_future = None
            return result
        except Exception as e:
            logger.error(f"Error getting future result: {e}", exc_info=True)
            st.session_state.processing = False
            st.session_state.processing_future = None
            return "", f"Processing error: {str(e)}"
    
    return None


def render_chat_interface() -> None:
    """Render the chat interface component.

    Displays message history, handles user input, and sends queries
    to the agent for processing.
    """
    st.header("Chat Interface")

    # Initialize session state
    initialize_chat_session()
    
    # Log current state for debugging
    logger.debug(
        f"Chat render - agent exists: {st.session_state.get('agent') is not None}, "
        f"agent_initialized: {st.session_state.get('agent_initialized', False)}, "
        f"init_attempted: {st.session_state.get('init_attempted', False)}, "
        f"last_error: {st.session_state.get('last_error') is not None}"
    )
    
    # Auto-initialize agent on first load
    if st.session_state.agent is None:
        # Only try once per session unless user explicitly retries
        if not st.session_state.get("init_attempted", False):
            logger.info("Starting agent auto-initialization")
            st.session_state.init_attempted = True
            with st.spinner("Initializing Agent Zero... (connecting to services)"):
                success, error = _initialize_agent()
                if success:
                    # Clear any stale errors from previous attempts
                    st.session_state.last_error = None
                    logger.info("Agent auto-initialization succeeded")
                else:
                    st.session_state.last_error = error
                    logger.warning(f"Agent auto-initialization failed: {error}")
                st.rerun()
        else:
            logger.debug(f"Agent initialization already attempted, agent is None: {st.session_state.agent is None}")
    
    # Check for completed background processing
    # Add safety check: ensure processing state is consistent
    if st.session_state.processing:
        # Guard: if processing flag is True but no future exists, reset state
        if st.session_state.processing_future is None:
            logger.warning("Processing flag set but no future found - resetting state")
            st.session_state.processing = False
            st.session_state.processing_last_warning_time = None
        else:
            result = _check_processing_status()
            if result is not None:
                # Processing complete
                response, error = result
                
                if error:
                    st.session_state.messages.append({
                        "role": "error",
                        "content": f"Warning: {error}"
                    })
                    st.session_state.last_error = error
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                    })
                    st.session_state.last_error = None
                
                # Clear processing state
                st.session_state.processing = False
                st.session_state.processing_future = None
                st.session_state.processing_last_warning_time = None
                st.rerun()
            else:
                # Still processing - check if we should show a warning
                elapsed = time.time() - st.session_state.processing_start_time
                
                # Determine if we should show a warning (every 60 seconds)
                should_show_warning = False
                if st.session_state.processing_last_warning_time is None:
                    # First warning: show after 60 seconds
                    if elapsed >= 60.0:
                        should_show_warning = True
                else:
                    # Subsequent warnings: show every 60 seconds after last warning
                    time_since_last_warning = time.time() - st.session_state.processing_last_warning_time
                    if time_since_last_warning >= 60.0:
                        should_show_warning = True
                
                if should_show_warning:
                    # Show warning at the top with option to continue or cancel
                    st.warning(
                        f"⚠️ The agent is taking longer than expected.\n\n"
                        f"**Elapsed time:** {elapsed:.1f} seconds\n\n"
                        f"This might be a complex request. Would you like to continue waiting?"
                    )
                    col_continue, col_cancel = st.columns(2)
                    with col_continue:
                        if st.button("Continue Waiting", type="primary", use_container_width=True, key=f"continue_{int(elapsed)}"):
                            # User wants to continue - mark this warning as shown
                            st.session_state.processing_last_warning_time = time.time()
                            logger.info(f"User chose to continue waiting (elapsed: {elapsed:.1f}s)")
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel Request", use_container_width=True, key=f"cancel_{int(elapsed)}"):
                            # User wants to cancel
                            logger.info(f"User canceled processing after {elapsed:.1f}s")
                            st.session_state.messages.append({
                                "role": "error",
                                "content": f"Request canceled by user after {elapsed:.1f}s."
                            })
                            # Try to cancel the future (may not work if already running)
                            if st.session_state.processing_future:
                                st.session_state.processing_future.cancel()
                            # Clear processing state
                            st.session_state.processing = False
                            st.session_state.processing_future = None
                            st.session_state.processing_last_warning_time = None
                            st.rerun()
                    st.divider()
                # Continue rendering - show chat with processing indicator
    
    # Display errors only if agent is not initialized
    if st.session_state.last_error and st.session_state.agent is None:
        logger.warning(f"Displaying initialization error: {st.session_state.last_error}")
        st.error(f"Warning: {st.session_state.last_error}")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Retry Connection", use_container_width=True):
                st.session_state.last_error = None
                st.session_state.agent_initialized = False
                st.session_state.init_attempted = False
                logger.info("User clicked retry button, resetting init_attempted flag")
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.rerun()
        st.divider()
    else:
        logger.debug(f"Not displaying error - last_error: {st.session_state.last_error}, agent exists: {st.session_state.agent is not None}")

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
                
                # Show processing indicator if agent is working
                if st.session_state.processing:
                    with st.chat_message("assistant"):
                        elapsed = time.time() - st.session_state.processing_start_time
                        with st.spinner(f"Thinking... ({elapsed:.1f}s)"):
                            time.sleep(1)  # Poll every second
                        st.rerun()
            else:
                st.info("No messages yet. Start a conversation!")

        st.divider()

        # Input area
        st.subheader("Send Message")
        
        # Disable input during processing to prevent state corruption
        is_processing = st.session_state.processing
        
        user_input = st.text_area(
            "Your message:",
            value=st.session_state.user_input,
            placeholder="Ask the agent a question or request..." if not is_processing else "Agent is processing...",
            height=100,
            label_visibility="collapsed",
            key="chat_input",
            disabled=is_processing,
        )

        col_send, col_clear = st.columns([3, 1])

        with col_send:
            if st.button("Send", use_container_width=True, disabled=is_processing):
                if user_input.strip():
                    # Store the message before clearing input
                    message_to_send = user_input.strip()
                    
                    # Clear the input field
                    st.session_state.user_input = ""
                    
                    # Add user message to history
                    st.session_state.messages.append({"role": "user", "content": message_to_send})

                    # Check if agent is ready (should already be initialized by auto-init)
                    if st.session_state.agent is None:
                        st.session_state.messages.append({
                            "role": "error",
                            "content": "Agent not initialized. Please refresh the page and try again."
                        })
                        st.rerun()
                        return

                    # Submit processing to background thread (pass agent and conversation_id explicitly)
                    st.session_state.processing = True
                    st.session_state.processing_future = _executor.submit(
                        _background_process_wrapper,
                        message_to_send,
                        st.session_state.agent,  # Pass agent directly
                        st.session_state.conversation_id  # Pass conversation_id directly
                    )
                    st.session_state.processing_message = message_to_send
                    st.session_state.processing_start_time = time.time()
                    st.session_state.processing_last_warning_time = None  # Reset warning timer

                    st.rerun()
                else:
                    st.warning("Please enter a message.")

        with col_clear:
            if st.button("Clear", use_container_width=True, disabled=is_processing):
                st.session_state.messages = []
                st.session_state.last_error = None
                st.rerun()

    with col_sidebar:
        st.subheader("Info")
        
        # Show agent status
        if st.session_state.agent_initialized:
            st.success("Agent Ready")
        else:
            st.warning("Agent Idle")
        
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
        if st.button("Export"):
            import json

            conversation_json = json.dumps(st.session_state.messages, indent=2)
            st.download_button(
                "Download Conversation",
                conversation_json,
                "conversation.json",
                "application/json",
            )
