"""Logging configuration for Agent Zero.

This module provides structured logging setup with JSON formatting support
and configurable log levels per environment.
"""

import json
import logging
import logging.config
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import get_config

# Capture Python warnings in logging system
logging.captureWarnings(True)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom attributes
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Custom text formatter with color support."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors."""
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        level = record.levelname
        logger = record.name
        message = record.getMessage()

        # Add color if outputting to terminal
        if sys.stdout.isatty():
            color = self.COLORS.get(level, "")
            level = f"{color}{level}{self.RESET}"

        base_format = f"[{timestamp}] {level:20s} {logger:40s} - {message}"

        # Add exception info if present
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"

        return base_format


def setup_logging() -> None:
    """
    Configure logging for the application.

    Sets up structured logging with appropriate formatters and handlers
    based on the application environment configuration.
    """
    config = get_config()

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Determine formatter based on config
    if config.log_format == "json":
        formatter = JSONFormatter()
        file_format = "%(message)s"  # JSON formatter handles all formatting
    else:
        formatter = TextFormatter()
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logging config dict
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "text": {
                "()": TextFormatter,
            },
            "standard": {
                "format": file_format,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": config.log_level,
                "formatter": config.log_format,
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": config.log_level,
                "formatter": "standard",
                "filename": f"logs/agent-zero-{config.env}.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "standard",
                "filename": f"logs/agent-zero-{config.env}-error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": config.log_level,
            "handlers": ["console", "file", "error_file"],
        },
        "loggers": {
            "src": {
                "level": config.log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "py.warnings": {
                "level": "WARNING",
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "urllib3": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
            "requests": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
            "langchain": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "qdrant_client": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "ollama": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Log startup message at DEBUG level to avoid log flooding
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Logging configured: env={config.env}, "
        f"level={config.log_level}, format={config.log_format}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: The logger name, typically __name__

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)

