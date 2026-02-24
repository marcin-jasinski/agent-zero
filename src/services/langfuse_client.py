"""Langfuse API client for observability dashboard.

This module provides a read-only HTTP API wrapper for Langfuse
to display trace information in the Agent Zero dashboard.

Design Reference: DASHBOARD_DESIGN.md § "Langfuse Observability Tab"
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class TraceSummary:
    """Summary statistics for Langfuse traces.
    
    Attributes:
        total_traces: Total number of traces
        traces_24h: Traces in last 24 hours
        avg_latency_ms: Average trace latency in milliseconds
        error_rate: Error rate as percentage (0-100)
        time_range: Time range for the summary
    """
    total_traces: int = 0
    traces_24h: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    time_range: str = "24h"


@dataclass
class TraceInfo:
    """Information about a single Langfuse trace.
    
    Attributes:
        trace_id: Unique trace identifier
        name: Trace name/operation
        timestamp: Trace start timestamp
        duration_ms: Total duration in milliseconds
        status: Trace status (success, error, etc.)
        input_tokens: Number of input tokens (if available)
        output_tokens: Number of output tokens (if available)
        metadata: Additional trace metadata
    """
    trace_id: str
    name: str
    timestamp: datetime
    duration_ms: float = 0.0
    status: str = "unknown"
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceDetails:
    """Detailed information about a trace including spans.
    
    Attributes:
        trace: Basic trace information
        spans: List of spans within the trace
        events: List of events within the trace
        token_usage: Token usage breakdown
        latency_breakdown: Latency breakdown by component
        error_message: Error message if trace failed
    """
    trace: TraceInfo
    spans: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    latency_breakdown: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None


class LangfuseClient:
    """Read-only HTTP client for Langfuse API.
    
    Provides methods to retrieve trace information and metrics
    from Langfuse for display in the observability dashboard.
    
    Attributes:
        host: Langfuse API host URL
        public_key: Langfuse public API key
        secret_key: Langfuse secret API key
        timeout: Request timeout in seconds
        enabled: Whether Langfuse is enabled
    """
    
    def __init__(self) -> None:
        """Initialize Langfuse client from configuration."""
        self.config = get_config()
        self.host = self.config.langfuse.host.rstrip("/")
        self.public_key = self.config.langfuse.public_key
        self.secret_key = self.config.langfuse.secret_key
        self.timeout = self.config.langfuse.timeout
        self.enabled = self.config.langfuse.enabled
        
        # Setup session with retry logic
        self._session = self._create_session()
        
        logger.info(f"LangfuseClient initialized: host={self.host}, enabled={self.enabled}")
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry configuration.
        
        Returns:
            Configured requests Session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set authentication if available
        if self.public_key and self.secret_key:
            session.auth = (self.public_key, self.secret_key)
        
        return session
    
    def is_healthy(self) -> bool:
        """Check Langfuse API connectivity.
        
        Returns:
            True if Langfuse is reachable and responding
        """
        if not self.enabled:
            logger.debug("Langfuse is disabled, skipping health check")
            return False
        
        try:
            # Try to access Langfuse health endpoint or API root
            response = self._session.get(
                f"{self.host}/api/public/health",
                timeout=5
            )
            
            # Accept 200-299 status codes
            if response.ok:
                logger.debug("Langfuse health check passed")
                return True
            
            # Try alternative endpoint
            response = self._session.get(
                f"{self.host}/api/public/traces",
                params={"limit": 1},
                timeout=5
            )
            
            if response.ok or response.status_code == 401:
                # 401 means API is reachable but auth failed
                logger.debug("Langfuse API reachable (auth may be needed)")
                return True
            
            logger.warning(f"Langfuse health check failed: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Langfuse health check failed: {e}")
            return False
    
    def get_trace_summary(self, time_range: str = "24h") -> TraceSummary:
        """Get summary statistics for traces.
        
        Args:
            time_range: Time range for summary ("24h", "7d", "30d")
            
        Returns:
            TraceSummary with aggregated statistics
        """
        if not self.enabled:
            return TraceSummary(time_range=time_range)
        
        if not self.public_key or not self.secret_key:
            logger.debug("Langfuse API keys not configured, skipping trace fetch")
            return TraceSummary(time_range=time_range)
        
        try:
            # Calculate time range
            now = datetime.utcnow()
            if time_range == "24h":
                start_time = now - timedelta(hours=24)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            elif time_range == "30d":
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(hours=24)
            
            # Fetch traces from Langfuse API
            response = self._session.get(
                f"{self.host}/api/public/traces",
                params={
                    "limit": 1000,
                    "orderBy": "timestamp",
                    "order": "desc",
                },
                timeout=self.timeout
            )
            
            if not response.ok:
                logger.warning(f"Failed to fetch traces: {response.status_code}")
                return TraceSummary(time_range=time_range)
            
            data = response.json()
            traces = data.get("data", [])
            
            # Filter by time range and calculate stats
            total_traces = len(traces)
            traces_in_range = [
                t for t in traces
                if self._parse_timestamp(t.get("timestamp")) >= start_time
            ]
            
            # Calculate averages
            latencies = [
                t.get("latency", 0) or 0 
                for t in traces_in_range 
                if t.get("latency") is not None
            ]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            # Calculate error rate
            errors = sum(
                1 for t in traces_in_range 
                if t.get("status") in ["error", "ERROR", "failed"]
            )
            error_rate = (errors / len(traces_in_range) * 100) if traces_in_range else 0.0
            
            # Get 24h count
            last_24h_start = now - timedelta(hours=24)
            traces_24h = sum(
                1 for t in traces
                if self._parse_timestamp(t.get("timestamp")) >= last_24h_start
            )
            
            return TraceSummary(
                total_traces=total_traces,
                traces_24h=traces_24h,
                avg_latency_ms=avg_latency,
                error_rate=error_rate,
                time_range=time_range
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get trace summary: {e}")
            return TraceSummary(time_range=time_range)
        except Exception as e:
            logger.error(f"Error processing trace summary: {e}")
            return TraceSummary(time_range=time_range)
    
    def get_recent_traces(
        self, 
        limit: int = 20, 
        status_filter: Optional[str] = None
    ) -> List[TraceInfo]:
        """Get recent traces from Langfuse.
        
        Args:
            limit: Maximum number of traces to return (1-100)
            status_filter: Filter by status ("success", "error", or None for all)
            
        Returns:
            List of TraceInfo objects
        """
        if not self.enabled:
            return []
        
        if not self.public_key or not self.secret_key:
            logger.debug("Langfuse API keys not configured, skipping trace fetch")
            return []
        
        try:
            # Clamp limit to valid range
            limit = max(1, min(100, limit))
            
            # Build query parameters
            params = {
                "limit": limit,
                "orderBy": "timestamp",
                "order": "desc",
            }
            
            response = self._session.get(
                f"{self.host}/api/public/traces",
                params=params,
                timeout=self.timeout
            )
            
            if not response.ok:
                logger.warning(f"Failed to fetch recent traces: {response.status_code}")
                return []
            
            data = response.json()
            traces = data.get("data", [])
            
            # Convert to TraceInfo objects
            result = []
            for trace in traces:
                trace_info = TraceInfo(
                    trace_id=trace.get("id", ""),
                    name=trace.get("name", "Unknown"),
                    timestamp=self._parse_timestamp(trace.get("timestamp")),
                    duration_ms=trace.get("latency", 0) or 0,
                    status=trace.get("status", "unknown") or "unknown",
                    input_tokens=trace.get("inputTokens", 0) or 0,
                    output_tokens=trace.get("outputTokens", 0) or 0,
                    metadata=trace.get("metadata", {}) or {},
                )
                
                # Apply status filter if specified
                if status_filter:
                    if status_filter.lower() == "success" and trace_info.status.lower() not in ["success", "ok"]:
                        continue
                    if status_filter.lower() == "error" and trace_info.status.lower() not in ["error", "failed"]:
                        continue
                
                result.append(trace_info)
            
            logger.debug(f"Retrieved {len(result)} recent traces")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get recent traces: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing recent traces: {e}")
            return []
    
    def get_trace_details(self, trace_id: str) -> Optional[TraceDetails]:
        """Get detailed information about a specific trace.
        
        Args:
            trace_id: Unique trace identifier
            
        Returns:
            TraceDetails if found, None otherwise
        """
        if not self.enabled:
            return None
        
        if not trace_id:
            logger.warning("Empty trace_id provided")
            return None
        
        try:
            # Fetch trace details
            response = self._session.get(
                f"{self.host}/api/public/traces/{trace_id}",
                timeout=self.timeout
            )
            
            if not response.ok:
                if response.status_code == 404:
                    logger.warning(f"Trace not found: {trace_id}")
                else:
                    logger.warning(f"Failed to fetch trace details: {response.status_code}")
                return None
            
            trace_data = response.json()
            
            # Build basic trace info
            trace_info = TraceInfo(
                trace_id=trace_data.get("id", trace_id),
                name=trace_data.get("name", "Unknown"),
                timestamp=self._parse_timestamp(trace_data.get("timestamp")),
                duration_ms=trace_data.get("latency", 0) or 0,
                status=trace_data.get("status", "unknown") or "unknown",
                input_tokens=trace_data.get("inputTokens", 0) or 0,
                output_tokens=trace_data.get("outputTokens", 0) or 0,
                metadata=trace_data.get("metadata", {}) or {},
            )
            
            # Get spans/observations for this trace
            spans = []
            observations = trace_data.get("observations", [])
            for obs in observations:
                spans.append({
                    "id": obs.get("id", ""),
                    "name": obs.get("name", ""),
                    "type": obs.get("type", ""),
                    "start_time": obs.get("startTime"),
                    "end_time": obs.get("endTime"),
                    "duration_ms": obs.get("latency", 0),
                    "model": obs.get("model"),
                    "input": obs.get("input"),
                    "output": obs.get("output"),
                })
            
            # Calculate token usage
            token_usage = {
                "input": trace_info.input_tokens,
                "output": trace_info.output_tokens,
                "total": trace_info.input_tokens + trace_info.output_tokens,
            }
            
            # Calculate latency breakdown by span type
            latency_breakdown = {}
            for span in spans:
                span_type = span.get("type", "unknown")
                latency_breakdown[span_type] = (
                    latency_breakdown.get(span_type, 0) + 
                    (span.get("duration_ms", 0) or 0)
                )
            
            # Extract error message if present
            error_message = None
            if trace_info.status.lower() in ["error", "failed"]:
                error_message = trace_data.get("error") or trace_data.get("statusMessage")
            
            return TraceDetails(
                trace=trace_info,
                spans=spans,
                events=[],  # Events not always available in public API
                token_usage=token_usage,
                latency_breakdown=latency_breakdown,
                error_message=error_message,
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get trace details: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing trace details: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime object.
        
        Args:
            timestamp_str: ISO format timestamp string
            
        Returns:
            Parsed datetime (always naive UTC), or current time if parsing fails
        """
        if not timestamp_str:
            return datetime.utcnow()
        
        try:
            # Handle ISO format with Z suffix
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1]
            
            # Remove timezone info to get naive datetime for comparison
            # This is acceptable for local dev as all times are UTC
            if "+" in timestamp_str:
                timestamp_str = timestamp_str.split("+")[0]
            if "-" in timestamp_str and timestamp_str.count("-") > 2:
                # Handle negative timezone offset like -05:00
                parts = timestamp_str.rsplit("-", 1)
                if ":" in parts[-1] and len(parts[-1]) <= 6:
                    timestamp_str = parts[0]
            
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return datetime.utcnow()
    
    def get_full_dashboard_url(self) -> str:
        """Get URL to full Langfuse dashboard.
        
        Returns:
            URL to Langfuse web interface
        """
        return self.host
