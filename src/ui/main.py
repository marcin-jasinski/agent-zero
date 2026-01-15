"""Agent Zero (L.A.B.) - Main Streamlit Application Entry Point.

This is the A.P.I. (AI Playground Interface) - the web-based dashboard
for Agent Zero, the Local Agent Builder.
"""

import logging

import streamlit as st

from src.config import get_config
from src.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Agent Zero - L.A.B.",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS
st.markdown(
    """
    <style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """Main application entry point."""
    # Load configuration
    config = get_config()

    logger.info("Starting Agent Zero UI")

    # Header
    st.title("🤖 Agent Zero (L.A.B.)")
    st.markdown("**Local Agent Builder** - Build and test AI agents locally with ease")

    # Sidebar - Status and Info
    with st.sidebar:
        st.header("System Status")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Environment", config.env)
        with col2:
            st.metric("Debug", config.debug)

        st.divider()

        # Service Status Placeholder
        st.subheader("Service Status")
        st.info("⚠️ Service health checks will be displayed here")

        st.divider()

        # Settings
        st.subheader("Settings")
        if st.button("🔄 Refresh Status"):
            st.rerun()

    # Main Content - Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📚 Knowledge Base", "⚙️ Settings", "📋 Logs"])

    with tab1:
        st.header("Chat Interface")
        st.info("💬 Chat interface will be implemented here")
        st.write("Send messages to the Agent Zero agent and get intelligent responses.")

    with tab2:
        st.header("Knowledge Base")
        st.info("📚 Knowledge Base management will be implemented here")
        st.write("Upload and manage documents for semantic search and retrieval.")

    with tab3:
        st.header("Settings")
        st.info("⚙️ Configuration settings will be displayed here")
        st.write("Configure LLM parameters, models, and system behavior.")

    with tab4:
        st.header("System Logs")
        st.info("📋 Application logs will be streamed here")
        st.write("Monitor system health and debug information in real-time.")

    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🔗 Built with [Streamlit](https://streamlit.io/)")
    with col2:
        st.caption(f"Version: {config.app_version}")
    with col3:
        st.caption("[GitHub](https://github.com/marcin-jasinski/agent-zero)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        st.error(f"❌ Application error: {str(e)}")
        st.stop()
