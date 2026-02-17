"""Logs Viewer Component for Agent Zero.

Implements real-time log streaming and application monitoring.
"""

import logging
from pathlib import Path
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def initialize_logs_session() -> None:
    """Initialize logs session state variables."""
    if "log_tail_lines" not in st.session_state:
        st.session_state.log_tail_lines = 50
    if "log_filter_level" not in st.session_state:
        st.session_state.log_filter_level = "ALL"
    if "log_service_filter" not in st.session_state:
        st.session_state.log_service_filter = "ALL"


# Service-to-logger pattern mapping
SERVICE_LOGGER_PATTERNS = {
    "ALL": [],
    "Ollama": ["ollama_client", "ollama", "OllamaClient"],
    "Qdrant": ["qdrant_client", "qdrant", "QdrantVectorClient"],
    "Meilisearch": ["meilisearch_client", "meilisearch", "MeilisearchClient"],
    "Langfuse": ["langfuse_client", "langfuse", "observability"],
    "Agent Core": ["src.core.agent", "src.core.retrieval", "src.core.ingest", "src.core.memory", "AgentOrchestrator", "RetrievalEngine", "DocumentIngestor"],
    "UI": ["src.ui", "streamlit", "render_", "navigation"],
}


def get_app_logs(log_file: Path, tail_lines: int = 50, level_filter: str = "ALL", service_filter: str = "ALL") -> str:
    """Read application logs from file.

    Args:
        log_file: Path to the log file
        tail_lines: Number of lines to read from end of file
        level_filter: Log level to filter (ALL, INFO, WARNING, ERROR, DEBUG)
        service_filter: Service to filter (ALL, Ollama, Qdrant, etc.)

    Returns:
        Formatted log content
    """
    if not log_file.exists():
        return "[No logs available yet]"

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Apply log level filter
        if level_filter != "ALL":
            lines = [line for line in lines if level_filter in line.upper()]

        # Apply service filter
        if service_filter != "ALL":
            patterns = SERVICE_LOGGER_PATTERNS.get(service_filter, [])
            if patterns:
                filtered_lines = []
                for line in lines:
                    if any(pattern in line for pattern in patterns):
                        filtered_lines.append(line)
                lines = filtered_lines

        selected_lines = lines[-tail_lines:] if len(lines) > tail_lines else lines

        return "".join(selected_lines) if selected_lines else "[No logs matching filter]"
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return f"[Error reading logs: {str(e)}]"


def render_logs() -> None:
    """Render the logs viewer interface."""
    st.title("📋 Application Logs")
    st.markdown(
        "Real-time application logs with filtering and export capabilities."
    )

    # Filters row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        log_level = st.selectbox(
            "Log Level:",
            ["ALL", "DEBUG", "INFO", "WARNING", "ERROR"],
            index=2,
            key="log_filter_level",
        )

    with col2:
        service_filter = st.selectbox(
            "Service:",
            ["ALL", "Ollama", "Qdrant", "Meilisearch", "Langfuse", "Agent Core", "UI"],
            index=0,
            key="log_service_filter",
        )

    with col3:
        tail_lines = st.number_input(
            "Lines to display:",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            key="log_tail_lines",
        )

    with col4:
        auto_refresh = st.checkbox("Auto-refresh (2s)", value=False)

    st.divider()

    # Log display area
    log_container = st.container(border=True)

    # Get logs - use actual log file name based on environment
    from src.config import get_config
    config = get_config()
    log_file = Path(f"/app/logs/agent-zero-{config.env}.log")

    if log_file.exists():
        log_content = get_app_logs(log_file, tail_lines, log_level, service_filter)

        # Display logs in monospace
        log_container.code(
            log_content,
            language="log",
        )

        # Log statistics
        st.divider()
        st.subheader("Log Statistics")

        col1, col2, col3, col4 = st.columns(4)

        # Count log levels
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            with col1:
                info_count = content.count("INFO")
                st.metric("Info", info_count)

            with col2:
                debug_count = content.count("DEBUG")
                st.metric("Debug", debug_count)

            with col3:
                warning_count = content.count("WARNING")
                st.metric("Warnings", warning_count)

            with col4:
                error_count = content.count("ERROR")
                st.metric("Errors", error_count)

        except Exception as e:
            st.warning(f"Could not calculate log statistics: {e}")

    else:
        from src.config import get_config
        config = get_config()
        expected_log = f"/app/logs/agent-zero-{config.env}.log"
        log_container.info(
            f"No logs available yet. Start the application to see logs here.\n\n"
            f"Expected log file: `{expected_log}`"
        )

    # Export logs
    st.divider()
    st.subheader("Export Logs")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Download Current Logs"):
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = f.read()

                st.download_button(
                    "Download as TXT",
                    log_data,
                    "app_logs.txt",
                    "text/plain",
                )
            else:
                st.warning("No logs file found")

    with col2:
        if st.button("Clear Logs"):
            # NOTE: In production, this would require admin authentication
            try:
                if log_file.exists():
                    log_file.unlink()  # Delete the file
                    st.success("Logs cleared")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not clear logs: {e}")

    # Auto-refresh mechanism
    if auto_refresh:
        import time

        st.info("Auto-refreshing every 2 seconds...")
        time.sleep(2)
        st.rerun()

    st.divider()
    from src.config import get_config
    config = get_config()
    log_path = f"/app/logs/agent-zero-{config.env}.log"
    st.caption(
        f"Tip: Logs are written to `{log_path}` inside the container. "
        "Use `docker-compose logs app-agent` to view logs in your terminal."
    )
