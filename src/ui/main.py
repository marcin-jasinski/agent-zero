"""Agent Zero (L.A.B.) - Main Streamlit Application Entry Point.

This is the A.P.I. (AI Playground Interface) - the web-based dashboard
for Agent Zero, the Local Agent Builder.
"""

import logging
import sys
from pathlib import Path

# Add project root to Python path for module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from src.config import get_config
from src.logging_config import setup_logging
from src.services import HealthChecker
from src.startup import ApplicationStartup
from src.ui.components import (
    initialize_chat_session,
    initialize_kb_session,
    initialize_logs_session,
    initialize_settings_session,
    render_chat_interface,
    render_knowledge_base,
    render_logs,
    render_settings,
)

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


def render_sidebar_status() -> None:
    """Render the sidebar with system status and service health."""
    with st.sidebar:
        st.header("System Status")

        config = get_config()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Environment", config.env)
        with col2:
            st.metric("Debug", "🟢 ON" if config.debug else "🔴 OFF")

        st.divider()

        # Service Status Section
        st.subheader("Service Status")

        # Initialize and run health checks
        if "health_checker" not in st.session_state:
            st.session_state.health_checker = HealthChecker()

        health_checker = st.session_state.health_checker
        service_statuses = health_checker.check_all()

        # Display each service status
        for service_name, status in service_statuses.items():
            icon = "✅" if status.is_healthy else "❌"
            status_text = "Healthy" if status.is_healthy else "Unhealthy"
            st.write(f"{icon} {status.name}: {status_text}")

            if status.message:
                st.caption(status.message)

        st.divider()

        # Settings
        st.subheader("Quick Actions")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                # Clear health checker cache to force new checks
                st.session_state.health_checker = HealthChecker()
                st.rerun()

        with col2:
            if st.button("ℹ️ About", use_container_width=True):
                st.info(
                    f"**Agent Zero (L.A.B.)**\n\n"
                    f"Version: {config.app_version}\n\n"
                    f"Local Agent Builder - Build and test AI agents locally.\n\n"
                    f"[GitHub](https://github.com/marcin-jasinski/agent-zero)"
                )

        st.divider()
        st.caption("💡 Agent Zero: Local-First, Secure-by-Design")


def main() -> None:
    """Main application entry point."""
    # Load configuration
    config = get_config()

    logger.info("Starting Agent Zero UI")

    # Run startup sequence (one-time initialization)
    if "startup_complete" not in st.session_state:
        st.session_state.startup_complete = False

    if not st.session_state.startup_complete:
        startup = ApplicationStartup()
        startup.run()
        st.session_state.startup_complete = True
        st.session_state.startup_status = startup.get_status()

    # Initialize all session states
    initialize_chat_session()
    initialize_kb_session()
    initialize_settings_session()
    initialize_logs_session()

    # Header
    st.title("🤖 Agent Zero (L.A.B.)")
    st.markdown("**Local Agent Builder** - Build and test AI agents locally with ease")

    # Render sidebar
    render_sidebar_status()

    # Main Content - Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📚 Knowledge Base", "⚙️ Settings", "📋 Logs"])

    with tab1:
        render_chat_interface()

    with tab2:
        render_knowledge_base()

    with tab3:
        render_settings()

    with tab4:
        render_logs()

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
