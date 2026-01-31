"""Langfuse Observability Dashboard for Agent Zero.

This module provides the Langfuse observability dashboard UI component,
displaying trace summaries, recent traces, and links to the full dashboard.

Design Reference: DASHBOARD_DESIGN.md § "Langfuse Observability Tab"
"""

import logging
from datetime import datetime

import streamlit as st

from src.config import get_config
from src.services.langfuse_client import LangfuseClient, TraceSummary, TraceInfo

logger = logging.getLogger(__name__)


def _get_langfuse_client() -> LangfuseClient:
    """Get or create cached Langfuse client.
    
    Returns:
        LangfuseClient instance
    """
    if "langfuse_client" not in st.session_state:
        st.session_state.langfuse_client = LangfuseClient()
    return st.session_state.langfuse_client


@st.cache_data(ttl=60)
def _get_trace_summary(time_range: str) -> dict:
    """Get cached trace summary.
    
    Args:
        time_range: Time range for summary ("24h", "7d", "30d")
        
    Returns:
        Dictionary with trace summary data
    """
    client = LangfuseClient()
    summary = client.get_trace_summary(time_range)
    return {
        "total_traces": summary.total_traces,
        "traces_24h": summary.traces_24h,
        "avg_latency_ms": summary.avg_latency_ms,
        "error_rate": summary.error_rate,
        "time_range": summary.time_range,
    }


@st.cache_data(ttl=30)
def _get_recent_traces(limit: int, status_filter: str) -> list:
    """Get cached recent traces.
    
    Args:
        limit: Maximum number of traces to return
        status_filter: Filter by status ("all", "success", "error")
        
    Returns:
        List of trace dictionaries
    """
    client = LangfuseClient()
    filter_value = None if status_filter == "all" else status_filter
    traces = client.get_recent_traces(limit=limit, status_filter=filter_value)
    
    return [
        {
            "trace_id": t.trace_id,
            "name": t.name,
            "timestamp": t.timestamp.isoformat(),
            "duration_ms": t.duration_ms,
            "status": t.status,
            "input_tokens": t.input_tokens,
            "output_tokens": t.output_tokens,
            "metadata": t.metadata,
        }
        for t in traces
    ]


def _render_summary_metrics(summary: dict) -> None:
    """Render summary metrics section.
    
    Args:
        summary: Trace summary dictionary
    """
    st.subheader("Summary Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Traces",
            value=f"{summary['total_traces']:,}",
            help="Total number of traces recorded"
        )
    
    with col2:
        st.metric(
            label="Last 24h",
            value=f"{summary['traces_24h']:,}",
            help="Traces recorded in the last 24 hours"
        )
    
    with col3:
        latency_str = f"{summary['avg_latency_ms']:.0f}ms" if summary['avg_latency_ms'] > 0 else "N/A"
        st.metric(
            label="Avg Latency",
            value=latency_str,
            help="Average trace latency"
        )
    
    with col4:
        error_str = f"{summary['error_rate']:.1f}%"
        st.metric(
            label="Error Rate",
            value=error_str,
            delta=None,
            delta_color="inverse" if summary['error_rate'] > 0 else "off",
            help="Percentage of traces with errors"
        )


def _get_status_icon(status: str) -> str:
    """Get status indicator icon.
    
    Args:
        status: Trace status string
        
    Returns:
        Emoji icon for status
    """
    status_lower = status.lower()
    if status_lower in ["success", "ok", "completed"]:
        return "✓"
    elif status_lower in ["error", "failed"]:
        return "✗"
    elif status_lower in ["running", "pending"]:
        return "⋯"
    else:
        return "○"


def _get_status_color(status: str) -> str:
    """Get status color for styling.
    
    Args:
        status: Trace status string
        
    Returns:
        Color name for status
    """
    status_lower = status.lower()
    if status_lower in ["success", "ok", "completed"]:
        return "green"
    elif status_lower in ["error", "failed"]:
        return "red"
    elif status_lower in ["running", "pending"]:
        return "orange"
    else:
        return "gray"


def _format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display.
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        Formatted timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return "N/A"


def _format_duration(duration_ms: float) -> str:
    """Format duration for display.
    
    Args:
        duration_ms: Duration in milliseconds
        
    Returns:
        Formatted duration string
    """
    if duration_ms >= 1000:
        return f"{duration_ms/1000:.1f}s"
    else:
        return f"{duration_ms:.0f}ms"


def _render_trace_card(trace: dict, expanded: bool = False) -> None:
    """Render a single trace card.
    
    Args:
        trace: Trace data dictionary
        expanded: Whether to show expanded details
    """
    status_icon = _get_status_icon(trace["status"])
    status_color = _get_status_color(trace["status"])
    timestamp = _format_timestamp(trace["timestamp"])
    duration = _format_duration(trace["duration_ms"])
    
    # Token info
    tokens_str = ""
    if trace["input_tokens"] > 0 or trace["output_tokens"] > 0:
        tokens_str = f" | {trace['input_tokens']}→{trace['output_tokens']} tokens"
    
    with st.expander(
        f"[{timestamp}] {trace['name']} | {duration} {status_icon}{tokens_str}",
        expanded=expanded
    ):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Trace ID:** `{trace['trace_id'][:12]}...`")
            st.markdown(f"**Status:** :{status_color}[{trace['status']}]")
            st.markdown(f"**Duration:** {duration}")
        
        with col2:
            st.markdown(f"**Input Tokens:** {trace['input_tokens']:,}")
            st.markdown(f"**Output Tokens:** {trace['output_tokens']:,}")
            total_tokens = trace['input_tokens'] + trace['output_tokens']
            st.markdown(f"**Total Tokens:** {total_tokens:,}")
        
        # Show metadata if available
        if trace.get("metadata"):
            st.markdown("**Metadata:**")
            st.json(trace["metadata"])


def _render_recent_traces(traces: list, show_details: bool = False) -> None:
    """Render recent traces section.
    
    Args:
        traces: List of trace dictionaries
        show_details: Whether to show detailed view
    """
    st.subheader("Recent Traces")
    
    if not traces:
        st.info("No traces found. Start using the agent to generate traces!")
        return
    
    st.caption(f"Showing {len(traces)} most recent traces")
    
    for i, trace in enumerate(traces):
        _render_trace_card(trace, expanded=(i == 0 and show_details))


def _render_langfuse_disabled() -> None:
    """Render UI when Langfuse is disabled."""
    st.warning(
        "**Langfuse Observability is Disabled**\n\n"
        "To enable Langfuse, set `LANGFUSE_ENABLED=true` in your `.env` file "
        "and ensure the Langfuse service is running."
    )
    
    st.markdown("""
    ### Why use Langfuse?
    
    Langfuse provides:
    - **Trace tracking** for all LLM calls
    - **Performance metrics** and latency analysis
    - **Debugging** for agent decisions
    - **Cost tracking** for token usage
    
    ### Quick Setup
    
    1. Ensure Langfuse is running: `docker-compose up langfuse -d`
    2. Set environment variables in `.env`:
       ```
       LANGFUSE_ENABLED=true
       LANGFUSE_HOST=http://langfuse:3000
       ```
    3. Restart the application
    """)


def _render_connection_error() -> None:
    """Render UI when Langfuse connection fails."""
    st.error(
        "**Cannot Connect to Langfuse**\n\n"
        "The Langfuse service is not responding. Please check:\n"
        "- Is the Langfuse container running?\n"
        "- Is the host URL correct in your configuration?\n"
        "- Are the API keys configured correctly?"
    )
    
    config = get_config()
    st.info(f"Current Langfuse host: `{config.langfuse.host}`")
    
    if st.button("Retry Connection"):
        st.cache_data.clear()
        st.rerun()


def render_langfuse_dashboard() -> None:
    """Render the Langfuse Observability Dashboard.
    
    Main entry point for the Langfuse dashboard tool.
    """
    st.header("Langfuse Observability")
    st.caption("Monitor agent traces, performance metrics, and token usage")
    
    config = get_config()
    
    # Check if Langfuse is enabled
    if not config.langfuse.enabled:
        _render_langfuse_disabled()
        return
    
    # Check connection
    client = _get_langfuse_client()
    if not client.is_healthy():
        _render_connection_error()
        return
    
    # Controls row
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        time_range = st.selectbox(
            "Time Range",
            options=["24h", "7d", "30d"],
            index=0,
            help="Time range for summary metrics"
        )
    
    with col2:
        status_filter = st.selectbox(
            "Status Filter",
            options=["all", "success", "error"],
            index=0,
            help="Filter traces by status"
        )
    
    with col3:
        trace_limit = st.slider(
            "Traces to Show",
            min_value=5,
            max_value=50,
            value=20,
            step=5,
            help="Number of recent traces to display"
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # Load data with caching
    try:
        with st.spinner("Loading trace data..."):
            summary = _get_trace_summary(time_range)
            traces = _get_recent_traces(trace_limit, status_filter)
    except Exception as e:
        logger.error(f"Error loading Langfuse data: {e}")
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Render summary metrics
    _render_summary_metrics(summary)
    
    st.divider()
    
    # Render recent traces
    _render_recent_traces(traces)
    
    st.divider()
    
    # Full dashboard link
    st.subheader("Full Dashboard")
    
    dashboard_url = client.get_full_dashboard_url()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(
            f"For advanced analysis, visit the full Langfuse dashboard at "
            f"[{dashboard_url}]({dashboard_url})"
        )
    
    with col2:
        st.link_button(
            "Open Dashboard →",
            url=dashboard_url,
            use_container_width=True
        )
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
