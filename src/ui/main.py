"""Agent Zero (L.A.B.) - Main Streamlit Application Entry Point.

This is the A.P.I. (AI Playground Interface) - the web-based dashboard
for Agent Zero, the Local Agent Builder.

Phase 4b: Implements dynamic sidebar navigation with feature flags.
Design Reference: DASHBOARD_DESIGN.md § "Sidebar Navigation Structure"
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
from src.ui.components.navigation import SidebarNavigation, ToolDefinition
from src.ui.tools import (
    initialize_chat_session,
    initialize_kb_session,
    initialize_logs_session,
    initialize_settings_session,
    render_chat_interface,
    render_knowledge_base,
    render_langfuse_dashboard,
    render_logs,
    render_promptfoo_dashboard,
    render_qdrant_dashboard,
    render_settings,
    render_system_health_dashboard,
)

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Agent Zero - L.A.B.",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Prometheus metrics server (one-time startup)
# This runs at module level, protected by session state
if "metrics_server_started" not in st.session_state:
    try:
        from src.observability import start_metrics_server, METRICS_AVAILABLE
        
        if METRICS_AVAILABLE:
            start_metrics_server(port=9091)
            logger.info("Prometheus metrics server started on port 9091")
            st.session_state["metrics_server_started"] = True
        else:
            st.session_state["metrics_server_started"] = False
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")
        st.session_state["metrics_server_started"] = False

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


def render_system_health_sidebar() -> None:
    """Render service health status in sidebar (below navigation).
    
    This will eventually be replaced by the full System Health dashboard tool.
    For now, provides quick status view in sidebar.
    """
    config = get_config()
    
    with st.sidebar:
        st.divider()
        st.subheader("Service Status")

        # Initialize and run health checks
        if "health_checker" not in st.session_state:
            st.session_state.health_checker = HealthChecker()

        health_checker = st.session_state.health_checker
        service_statuses = health_checker.check_all()

        # External URLs for browser access (localhost, not internal Docker hostnames)
        # These are the ports exposed by docker-compose to the host machine
        service_urls = {
            "Ollama": "http://localhost:11434",
            "Qdrant": "http://localhost:6333/dashboard",
            "Meilisearch": "http://localhost:7700",
            "Langfuse": "http://localhost:3000",
        }
        
        for service_name, status in service_statuses.items():
            status_indicator = "[OK]" if status.is_healthy else "[FAIL]"
            status_text = "Healthy" if status.is_healthy else "Unhealthy"
            
            # Get URL for this service (if available)
            service_url = service_urls.get(status.name, "")
            
            if service_url:
                # Render as clickable link with status
                st.markdown(
                    f"{status_indicator} **{status.name}**: {status_text} "
                    f"[Open]({service_url})",
                    help=f"Click 'Open' to access {status.name} dashboard"
                )
            else:
                st.write(f"{status_indicator} {status.name}: {status_text}")

            if status.message:
                st.caption(status.message)

        st.divider()

        # Quick Actions
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Refresh", use_container_width=True, key="refresh_health"):
                # Clear health checker cache to force new checks
                st.session_state.health_checker = HealthChecker()
                st.rerun()

        with col2:
            if st.button("About", use_container_width=True, key="about_btn"):
                st.info(
                    f"**Agent Zero (L.A.B.)**\n\n"
                    f"Version: {config.app_version}\n\n"
                    f"Local Agent Builder - Build and test AI agents locally.\n\n"
                    f"[GitHub](https://github.com/marcin-jasinski/agent-zero)"
                )

        st.divider()
        st.caption("Agent Zero: Local-First, Secure-by-Design")


def setup_navigation() -> SidebarNavigation:
    """Set up navigation with all available tools based on feature flags.
    
    Returns:
        Configured SidebarNavigation instance with registered tools
    """
    config = get_config()
    nav = SidebarNavigation()
    
    # Register Core Tools (always available if enabled)
    if config.dashboard.show_chat:
        nav.register_tool(ToolDefinition(
            key="chat",
            icon=">",
            label="Chat",
            description="Chat with Agent Zero",
            render_func=render_chat_interface,
            enabled=True,
            category="core"
        ))
    
    if config.dashboard.show_knowledge_base:
        nav.register_tool(ToolDefinition(
            key="knowledge_base",
            icon=">",
            label="Knowledge Base",
            description="Upload and manage documents",
            render_func=render_knowledge_base,
            enabled=True,
            category="core"
        ))
    
    if config.dashboard.show_settings:
        nav.register_tool(ToolDefinition(
            key="settings",
            icon=">",
            label="Settings",
            description="Configure Agent Zero",
            render_func=render_settings,
            enabled=True,
            category="core"
        ))
    
    if config.dashboard.show_logs:
        nav.register_tool(ToolDefinition(
            key="logs",
            icon=">",
            label="Logs",
            description="View system logs",
            render_func=render_logs,
            enabled=True,
            category="core"
        ))
    
    # Register Management Tools (Phase 4b - feature flagged)
    if config.dashboard.show_qdrant_manager:
        nav.register_tool(ToolDefinition(
            key="qdrant_manager",
            icon=">",
            label="Qdrant Manager",
            description="Manage vector database",
            render_func=render_qdrant_dashboard,
            enabled=True,
            category="management"
        ))
    
    # Langfuse Observability Dashboard (Step 19)
    if config.dashboard.show_langfuse_dashboard:
        nav.register_tool(ToolDefinition(
            key="langfuse_dashboard",
            icon=">",
            label="Langfuse Observability",
            description="View traces and metrics",
            render_func=render_langfuse_dashboard,
            enabled=True,
            category="management"
        ))
    
    # Promptfoo Testing Dashboard (Step 20)
    if config.dashboard.show_promptfoo:
        nav.register_tool(ToolDefinition(
            key="promptfoo",
            icon=">",
            label="Promptfoo Testing",
            description="Test and version prompts",
            render_func=render_promptfoo_dashboard,
            enabled=True,
            category="management"
        ))
    
    # System Health Dashboard (Step 21)
    if config.dashboard.show_system_health:
        nav.register_tool(ToolDefinition(
            key="system_health",
            icon=">",
            label="System Health",
            description="Monitor service health and resources",
            render_func=render_system_health_dashboard,
            enabled=True,
            category="management"
        ))
    
    logger.info(f"Navigation configured with {len(nav.tools)} tools")
    return nav


def render_sidebar_status() -> None:
    """Render the sidebar with system status and service health.
    
    DEPRECATED: This function is kept for backwards compatibility but is
    no longer used with the new navigation system. Use render_system_health_sidebar()
    and setup_navigation() instead.
    """
    """Render the sidebar with system status and service health."""
    with st.sidebar:
        st.header("System Status")

        config = get_config()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Environment", config.env)
        with col2:
            st.metric("Debug", "ON" if config.debug else "OFF")

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
            status_indicator = "[OK]" if status.is_healthy else "[FAIL]"
            status_text = "Healthy" if status.is_healthy else "Unhealthy"
            st.write(f"{status_indicator} {status.name}: {status_text}")

            if status.message:
                st.caption(status.message)

        st.divider()

        # Settings
        st.subheader("Quick Actions")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Refresh", use_container_width=True):
                # Clear health checker cache to force new checks
                st.session_state.health_checker = HealthChecker()
                st.rerun()

        with col2:
            if st.button("About", use_container_width=True):
                st.info(
                    f"**Agent Zero (L.A.B.)**\n\n"
                    f"Version: {config.app_version}\n\n"
                    f"Local Agent Builder - Build and test AI agents locally.\n\n"
                    f"[GitHub](https://github.com/marcin-jasinski/agent-zero)"
                )

        st.divider()
        st.caption("Agent Zero: Local-First, Secure-by-Design")


def _render_loading_screen() -> None:
    """Render a loading screen with progress bar during startup."""
    # Center the loading content
    st.markdown(
        """
        <style>
        .loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 60vh;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## Agent Zero")
        st.markdown("### Initializing Local Agent Builder...")
        st.markdown("---")
        
        # Progress bar placeholder
        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_text = st.empty()
        
        # Step definitions with progress percentages
        steps = [
            (0.05, "Starting initialization...", "Loading configuration"),
            (0.15, "Checking service health...", "Loading... or am I?"),
            (0.40, "Initializing Ollama...", "Loading, please wait... or just buy more RAM"),
            (0.65, "Initializing Qdrant...", "Adding 1s and 0s..."),
            (0.85, "Initializing Meilisearch...", "Generating more waiting time..."),
            (1.0, "Startup complete!", "Ready to use"),
        ]
        
        # Show initial state
        progress_bar.progress(steps[0][0])
        status_text.markdown(f"**{steps[0][1]}**")
        detail_text.caption(steps[0][2])
        
        return progress_bar, status_text, detail_text, steps


def _run_startup_with_progress() -> tuple[bool, list]:
    """Run startup sequence with progress updates.
    
    Returns:
        Tuple of (success, startup_statuses)
    """
    from src.startup import ApplicationStartup
    
    # Get progress UI elements from session state
    progress_bar = st.session_state.get("_progress_bar")
    status_text = st.session_state.get("_status_text")
    detail_text = st.session_state.get("_detail_text")
    steps = st.session_state.get("_steps")
    
    startup = ApplicationStartup()
    
    def update_progress(step_index: int) -> None:
        """Update progress bar and status text."""
        if progress_bar and steps and step_index < len(steps):
            progress_bar.progress(steps[step_index][0])
            if status_text:
                status_text.markdown(f"**{steps[step_index][1]}**")
            if detail_text:
                detail_text.caption(steps[step_index][2])
    
    # Step 1: Health check
    update_progress(1)
    startup._check_services()
    
    # Step 2: Ollama
    update_progress(2)
    startup._initialize_ollama()
    
    # Step 3: Qdrant
    update_progress(3)
    startup._initialize_qdrant()
    
    # Step 4: Meilisearch
    update_progress(4)
    startup._initialize_meilisearch()
    
    # Complete
    update_progress(5)
    startup._log_startup_summary()
    
    # Check for critical failures
    critical_failed = [s for s in startup.statuses if not s.success and "critical" in s.message.lower()]
    success = len(critical_failed) == 0
    
    return success, startup.get_status()


def main() -> None:
    """Main application entry point."""
    # Load configuration
    config = get_config()

    logger.info("Starting Agent Zero UI")

    # Run startup sequence (one-time initialization)
    if "startup_complete" not in st.session_state:
        st.session_state.startup_complete = False

    if not st.session_state.startup_complete:
        # Show loading screen
        progress_bar, status_text, detail_text, steps = _render_loading_screen()
        
        # Store in session state for progress updates
        st.session_state._progress_bar = progress_bar
        st.session_state._status_text = status_text
        st.session_state._detail_text = detail_text
        st.session_state._steps = steps
        
        # Run startup with progress
        import time
        time.sleep(0.3)  # Brief pause for UI to render
        
        success, statuses = _run_startup_with_progress()
        
        st.session_state.startup_complete = True
        st.session_state.startup_status = statuses
        
        # Clean up temporary session state
        for key in ["_progress_bar", "_status_text", "_detail_text", "_steps"]:
            if key in st.session_state:
                del st.session_state[key]
        
        # Brief pause to show completion, then rerun to show main UI
        time.sleep(0.5)
        st.rerun()

    # Initialize all session states for existing tools
    initialize_chat_session()
    initialize_kb_session()
    initialize_settings_session()
    initialize_logs_session()

    # Setup navigation
    nav = setup_navigation()
    
    # Render navigation sidebar
    nav.render_sidebar()
    
    # Render system health in sidebar (below navigation)
    render_system_health_sidebar()
    
    # Main Content Area - render active tool content directly
    nav.render_active_tool()

    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("Built with [Streamlit](https://streamlit.io/)")
    with col2:
        st.caption(f"Version: {config.app_version}")
    with col3:
        st.caption("[GitHub](https://github.com/marcin-jasinski/agent-zero)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        st.error(f"Application error: {str(e)}")
        st.stop()
