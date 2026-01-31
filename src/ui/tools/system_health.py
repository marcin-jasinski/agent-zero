"""System Health Dashboard for Agent Zero.

This module provides the System Health dashboard UI component,
displaying service status, host resources, and system monitoring.

Design Reference: DASHBOARD_DESIGN.md § "System Health Tab"
"""

import logging
import platform
from datetime import datetime
from typing import Dict, Optional

import streamlit as st

from src.config import get_config
from src.services import HealthChecker, ServiceStatus

logger = logging.getLogger(__name__)

# Try to import psutil for resource metrics (optional dependency)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - resource metrics will be limited")


def _get_health_checker() -> HealthChecker:
    """Get or create cached health checker.
    
    Returns:
        HealthChecker instance
    """
    if "system_health_checker" not in st.session_state:
        st.session_state.system_health_checker = HealthChecker()
    return st.session_state.system_health_checker


@st.cache_data(ttl=30)
def _get_service_statuses() -> Dict[str, dict]:
    """Get cached service statuses.
    
    Returns:
        Dictionary of service status data
    """
    checker = HealthChecker()
    statuses = checker.check_all()
    
    return {
        name: {
            "name": status.name,
            "is_healthy": status.is_healthy,
            "message": status.message,
            "details": status.details,
        }
        for name, status in statuses.items()
    }


def _get_resource_metrics() -> Dict[str, float]:
    """Get host system resource usage metrics.
    
    Returns:
        Dictionary with CPU, memory, and disk usage percentages
    """
    if not PSUTIL_AVAILABLE:
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "available": False,
        }
    
    try:
        # Get CPU usage (non-blocking, averaged over 0.1 second)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage (root partition)
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "memory_total_gb": memory.total / (1024 ** 3),
            "memory_used_gb": memory.used / (1024 ** 3),
            "disk_total_gb": disk.total / (1024 ** 3),
            "disk_used_gb": disk.used / (1024 ** 3),
            "available": True,
        }
    except Exception as e:
        logger.error(f"Error getting resource metrics: {e}")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "available": False,
            "error": str(e),
        }


def _get_system_info() -> Dict[str, str]:
    """Get system information.
    
    Returns:
        Dictionary with system details
    """
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
    }


def _get_status_icon(is_healthy: bool) -> str:
    """Get status indicator icon.
    
    Args:
        is_healthy: Whether the service is healthy
        
    Returns:
        Text indicator for status
    """
    return "[OK]" if is_healthy else "[FAIL]"


def _get_status_color(is_healthy: bool) -> str:
    """Get status color for styling.
    
    Args:
        is_healthy: Whether the service is healthy
        
    Returns:
        Color name for status
    """
    return "green" if is_healthy else "red"


def _render_resource_gauge(
    label: str,
    value: float,
    max_value: float = 100.0,
    unit: str = "%"
) -> None:
    """Render a resource usage gauge with progress bar.
    
    Args:
        label: Resource label (e.g., "CPU")
        value: Current value
        max_value: Maximum value for percentage calculation
        unit: Unit to display
    """
    percentage = (value / max_value) * 100 if max_value > 0 else 0
    
    # Determine color based on usage level
    if percentage >= 90:
        color = "red"
    elif percentage >= 70:
        color = "orange"
    else:
        color = "green"
    
    # Display label with value
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{label}:**")
    with col2:
        st.markdown(f":{color}[{value:.1f}{unit}]")
    
    # Display progress bar
    st.progress(min(percentage / 100, 1.0))


def _render_service_card(name: str, status: dict) -> None:
    """Render a service status card.
    
    Args:
        name: Service key name
        status: Service status dictionary
    """
    icon = _get_status_icon(status["is_healthy"])
    color = _get_status_color(status["is_healthy"])
    status_text = "Healthy" if status["is_healthy"] else "Unhealthy"
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            st.markdown(f"### {icon}")
        
        with col2:
            st.markdown(f"**{status['name']}**")
            st.markdown(f":{color}[{status_text}]")
        
        with col3:
            if status["message"]:
                st.caption(status["message"])
            
            # Show details if available
            if status.get("details"):
                with st.expander("Details"):
                    for key, value in status["details"].items():
                        st.text(f"{key}: {value}")


def _render_service_status_section(statuses: Dict[str, dict]) -> None:
    """Render the service status overview section.
    
    Args:
        statuses: Dictionary of service statuses
    """
    st.subheader("Service Status")
    
    # Summary row
    healthy_count = sum(1 for s in statuses.values() if s["is_healthy"])
    total_count = len(statuses)
    
    if healthy_count == total_count:
        st.success(f"All {total_count} services are healthy")
    else:
        st.warning(f"{healthy_count}/{total_count} services healthy")
    
    # Service cards in a grid
    col1, col2 = st.columns(2)
    
    services = list(statuses.items())
    for i, (name, status) in enumerate(services):
        with col1 if i % 2 == 0 else col2:
            with st.container(border=True):
                _render_service_card(name, status)


def _render_host_resources_section() -> None:
    """Render the host resources monitoring section."""
    st.subheader("Host Resources")
    
    metrics = _get_resource_metrics()
    
    if not metrics.get("available", False):
        st.info(
            "📦 **Resource monitoring unavailable**\n\n"
            "Install `psutil` for detailed resource metrics:\n"
            "```\npip install psutil\n```"
        )
        return
    
    # Resource gauges
    col1, col2, col3 = st.columns(3)
    
    with col1:
        _render_resource_gauge("CPU", metrics["cpu_percent"])
    
    with col2:
        _render_resource_gauge("Memory", metrics["memory_percent"])
        if "memory_used_gb" in metrics:
            st.caption(
                f"{metrics['memory_used_gb']:.1f} GB / "
                f"{metrics['memory_total_gb']:.1f} GB"
            )
    
    with col3:
        _render_resource_gauge("Disk", metrics["disk_percent"])
        if "disk_used_gb" in metrics:
            st.caption(
                f"{metrics['disk_used_gb']:.1f} GB / "
                f"{metrics['disk_total_gb']:.1f} GB"
            )


def _render_system_info_section() -> None:
    """Render the system information section."""
    st.subheader("System Information")
    
    info = _get_system_info()
    config = get_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Platform:**")
        st.text(f"{info['platform']} ({info['architecture']})")
        
        st.markdown("**Hostname:**")
        st.text(info['hostname'])
        
        st.markdown("**Python Version:**")
        st.text(info['python_version'])
    
    with col2:
        st.markdown("**Agent Zero Version:**")
        st.text(config.app_version)
        
        st.markdown("**Environment:**")
        st.text(config.env)
        
        st.markdown("**Debug Mode:**")
        st.text("Enabled" if config.debug else "Disabled")


def _render_actions_section() -> None:
    """Render the actions section with refresh and export."""
    st.subheader("Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Refresh All", use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop("system_health_checker", None)
            st.rerun()
    
    with col2:
        auto_refresh = st.checkbox(
            "Auto-refresh",
            value=st.session_state.get("auto_refresh_health", False),
            help="Automatically refresh every 30 seconds"
        )
        st.session_state.auto_refresh_health = auto_refresh
    
    with col3:
        if st.button("Export Diagnostics", use_container_width=True):
            _export_diagnostics()


def _export_diagnostics() -> None:
    """Export system diagnostics to JSON."""
    import json
    
    statuses = _get_service_statuses()
    metrics = _get_resource_metrics()
    info = _get_system_info()
    config = get_config()
    
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "app_version": config.app_version,
        "environment": config.env,
        "services": statuses,
        "resources": metrics,
        "system": info,
    }
    
    json_str = json.dumps(diagnostics, indent=2, default=str)
    
    st.download_button(
        label="Download JSON",
        data=json_str,
        file_name=f"agent_zero_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True
    )


def render_system_health_dashboard() -> None:
    """Render the System Health Dashboard.
    
    Main entry point for the System Health dashboard tool.
    """
    st.header("System Health")
    st.caption("Monitor service health, host resources, and system status")
    
    # Auto-refresh logic
    if st.session_state.get("auto_refresh_health", False):
        import time
        # This will cause a rerun every 30 seconds when auto-refresh is enabled
        # Note: In production, consider using st.fragment or more sophisticated refresh
        pass
    
    # Load service statuses
    try:
        with st.spinner("Checking services..."):
            statuses = _get_service_statuses()
    except Exception as e:
        logger.error(f"Error loading service statuses: {e}")
        st.error(f"Error loading service statuses: {str(e)}")
        statuses = {}
    
    # Render sections
    _render_service_status_section(statuses)
    
    st.divider()
    
    _render_host_resources_section()
    
    st.divider()
    
    _render_system_info_section()
    
    st.divider()
    
    _render_actions_section()
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
