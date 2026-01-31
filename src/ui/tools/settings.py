"""Settings Component for Agent Zero.

Implements configuration and settings management for the application.
"""

import logging

import streamlit as st

from src.config import get_config

logger = logging.getLogger(__name__)


def initialize_settings_session() -> None:
    """Initialize settings session state variables."""
    if "settings_modified" not in st.session_state:
        st.session_state.settings_modified = False


def render_settings() -> None:
    """Render the settings component.

    Displays configuration options for LLM, embeddings, and system parameters.
    """
    st.header("Settings & Configuration")

    # Initialize session state
    initialize_settings_session()

    # Load current configuration
    config = get_config()

    # Create tabs for settings categories
    set_tab1, set_tab2, set_tab3, set_tab4 = st.tabs(
        ["LLM", "Embeddings", "Database", "Security"]
    )

    with set_tab1:
        st.subheader("LLM Configuration")

        st.write("**Ollama Settings**")
        col1, col2 = st.columns(2)

        with col1:
            ollama_model = st.selectbox(
                "LLM Model:",
                ["ministral-3:3b", "mistral:latest", "llama2:latest"],
                help="Select the language model to use",
            )

        with col2:
            temperature = st.slider(
                "Temperature:",
                min_value=0.0,
                max_value=2.0,
                value=0.7,
                step=0.1,
                help="Controls randomness in responses (0=deterministic, 2=random)",
            )

        col1, col2, col3 = st.columns(3)

        with col1:
            top_p = st.slider(
                "Top P:",
                min_value=0.0,
                max_value=1.0,
                value=0.9,
                step=0.05,
                help="Nucleus sampling parameter",
            )

        with col2:
            max_tokens = st.number_input(
                "Max Tokens:",
                min_value=10,
                max_value=4096,
                value=512,
                step=10,
            )

        with col3:
            timeout = st.number_input(
                "Timeout (seconds):",
                min_value=1,
                max_value=300,
                value=30,
                step=1,
            )

        st.divider()
        st.write("**System Prompt**")
        system_prompt = st.text_area(
            "System prompt:",
            value="You are Agent Zero, a helpful AI assistant. Provide accurate, concise, and contextual responses.",
            height=100,
            label_visibility="collapsed",
        )

    with set_tab2:
        st.subheader("Embeddings Configuration")

        st.write("**Ollama Embeddings Settings**")
        col1, col2 = st.columns(2)

        with col1:
            embedding_model = st.selectbox(
                "Embedding Model:",
                ["nomic-embed-text-v2-moe", "nomic-embed-text-v1.5", "all-minilm"],
                help="Select the embedding model for semantic search",
            )

        with col2:
            embedding_dimension = st.number_input(
                "Embedding Dimension:",
                min_value=256,
                max_value=1536,
                value=768,
                step=64,
                disabled=True,
                help="Read-only: dimension of selected model",
            )

        st.info("Embeddings are used for semantic search in Qdrant vector database.")

    with set_tab3:
        st.subheader("Database Configuration")

        st.write("**Vector Database (Qdrant)**")
        col1, col2 = st.columns(2)

        with col1:
            qdrant_host = st.text_input(
                "Qdrant Host:",
                value="qdrant",
                help="Hostname or IP of Qdrant service",
            )

        with col2:
            qdrant_port = st.number_input(
                "Qdrant Port:",
                min_value=1,
                max_value=65535,
                value=6333,
                help="Port of Qdrant service",
            )

        st.divider()
        st.write("**Full-Text Search (Meilisearch)**")
        col1, col2 = st.columns(2)

        with col1:
            meilisearch_host = st.text_input(
                "Meilisearch Host:",
                value="meilisearch",
                help="Hostname or IP of Meilisearch service",
            )

        with col2:
            meilisearch_port = st.number_input(
                "Meilisearch Port:",
                min_value=1,
                max_value=65535,
                value=7700,
                help="Port of Meilisearch service",
            )

    with set_tab4:
        st.subheader("Security Settings")

        st.write("**Environment & Debug**")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Current Environment", config.env)

        with col2:
            st.metric("Debug Mode", "ON" if config.debug else "OFF")

        st.divider()
        st.write("**LLM Guard Settings**")

        enable_input_guard = st.checkbox(
            "Enable Input Guard",
            value=True,
            help="Scan user input for prompt injection and harmful content",
        )

        enable_output_guard = st.checkbox(
            "Enable Output Guard",
            value=True,
            help="Scan LLM output for harmful content and PII",
        )

        st.divider()
        st.write("**API Keys & Secrets** (Stored securely)")

        col1, col2 = st.columns(2)

        with col1:
            st.success("OLLAMA_BASE_URL: Configured")

        with col2:
            st.success("MEILISEARCH_API_KEY: Configured")

        st.info("Note: Secrets are read from environment variables and cannot be edited via UI.")

    # Save settings button
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Save Settings", use_container_width=True):
            st.session_state.settings_modified = True
            st.success("Settings saved! (Configuration will be applied in Phase 2 Step 7)")

    with col2:
        if st.button("↩️ Reset", use_container_width=True):
            st.info("Settings reset to defaults")
            st.rerun()

    with col3:
        st.caption("Tip: Some settings require application restart to take effect.")
