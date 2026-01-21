"""Structured JSON logging for RAG LLM Service."""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add log level
        log_record["level"] = record.levelname

        # Add component (logger name)
        log_record["component"] = record.name

        # Extract structured data from extra fields
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if hasattr(record, "event"):
            log_record["event"] = record.event

        if hasattr(record, "data"):
            log_record["data"] = record.data

        if hasattr(record, "error"):
            log_record["error"] = record.error

        # Add exception info if present
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'text')
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if log_format.lower() == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(component)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing query", extra={
        ...     'request_id': 'req_123',
        ...     'event': 'query_received',
        ...     'data': {'question': 'What is the policy?'}
        ... })
    """
    return logging.getLogger(name)


class StructuredLogger:
    """Helper class for structured logging with consistent format.

    Provides convenient methods for logging with structured data.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize with a logger instance."""
        self.logger = logger

    def log(
        self,
        level: str,
        message: str,
        request_id: Optional[str] = None,
        event: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log a structured message.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            request_id: Request ID for tracing
            event: Event type/name
            data: Additional structured data
            error: Error message or exception info
        """
        extra = {}
        if request_id:
            extra["request_id"] = request_id
        if event:
            extra["event"] = event
        if data:
            extra["data"] = data
        if error:
            extra["error"] = error

        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.log("info", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.log("warning", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.log("error", message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.log("critical", message, **kwargs)
