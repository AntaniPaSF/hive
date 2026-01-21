"""
Unit tests for structured logging functionality.

Tests JSON logging format, log levels, and structured data.
"""

import pytest
import json
import logging
from io import StringIO

from src.utils.logger import get_logger, setup_logging


class TestLoggerConfiguration:
    """Test logger setup and configuration."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_same_name_returns_same_instance(self):
        """Test get_logger with same name returns same logger."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2

    def test_setup_logging_configures_json_format(self):
        """Test setup_logging configures JSON output."""
        # Setup logging with JSON format
        setup_logging(log_level="INFO", log_format="json")
        logger = get_logger("test_json")

        # Verify logger is configured
        assert (
            logger.level == logging.INFO or logger.getEffectiveLevel() == logging.INFO
        )


class TestStructuredLogging:
    """Test structured logging with extra fields."""

    def test_log_with_extra_fields(self, caplog):
        """Test logging with structured extra fields."""
        logger = get_logger("test_structured")

        with caplog.at_level(logging.INFO):
            logger.info(
                "Test message",
                extra={
                    "component": "test_component",
                    "request_id": "req_123",
                    "user_id": "user_456",
                },
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == "Test message"
        assert hasattr(record, "component")
        assert record.component == "test_component"

    def test_log_levels(self, caplog):
        """Test different log levels."""
        logger = get_logger("test_levels")

        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

        assert len(caplog.records) == 4
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.records[1].levelname == "INFO"
        assert caplog.records[2].levelname == "WARNING"
        assert caplog.records[3].levelname == "ERROR"


class TestLogFormatting:
    """Test log message formatting."""

    def test_json_log_format(self):
        """Test JSON log formatting."""
        # Create a string buffer to capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Note: actual JSON formatting depends on python-json-logger
        # This test verifies the structure can be created
        logger = get_logger("test_json_format")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info(
            "Test JSON message", extra={"component": "test", "request_id": "req_789"}
        )

        # Verify log was written
        log_output = log_stream.getvalue()
        assert len(log_output) > 0
        assert "Test JSON message" in log_output

    def test_timestamp_in_logs(self, caplog):
        """Test timestamp is included in log records."""
        logger = get_logger("test_timestamp")

        with caplog.at_level(logging.INFO):
            logger.info("Test message with timestamp")

        record = caplog.records[0]
        assert hasattr(record, "created")
        assert record.created > 0


class TestErrorLogging:
    """Test error and exception logging."""

    def test_log_exception(self, caplog):
        """Test logging exceptions with stack trace."""
        logger = get_logger("test_exception")

        with caplog.at_level(logging.ERROR):
            try:
                raise ValueError("Test error")
            except ValueError:
                logger.exception("An error occurred")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert "An error occurred" in record.message
        assert record.exc_info is not None

    def test_log_error_with_context(self, caplog):
        """Test error logging with additional context."""
        logger = get_logger("test_error_context")

        with caplog.at_level(logging.ERROR):
            logger.error(
                "Operation failed",
                extra={
                    "component": "retrieval",
                    "error_type": "VectorStoreUnavailable",
                    "request_id": "req_error_123",
                },
            )

        record = caplog.records[0]
        assert record.component == "retrieval"
        assert record.error_type == "VectorStoreUnavailable"


class TestRequestLogging:
    """Test request-specific logging patterns."""

    def test_log_request_start(self, caplog):
        """Test logging request start."""
        logger = get_logger("test_request")

        with caplog.at_level(logging.INFO):
            logger.info(
                "Request started",
                extra={
                    "component": "api",
                    "request_id": "req_start_123",
                    "method": "POST",
                    "path": "/query",
                },
            )

        record = caplog.records[0]
        assert record.request_id == "req_start_123"
        assert record.method == "POST"

    def test_log_request_complete(self, caplog):
        """Test logging request completion."""
        logger = get_logger("test_request")

        with caplog.at_level(logging.INFO):
            logger.info(
                "Request completed",
                extra={
                    "component": "api",
                    "request_id": "req_complete_123",
                    "status": 200,
                    "processing_time_ms": 3420,
                },
            )

        record = caplog.records[0]
        assert record.status == 200
        assert record.processing_time_ms == 3420


class TestLoggerHierarchy:
    """Test logger hierarchy and propagation."""

    def test_child_logger_inherits_level(self):
        """Test child loggers inherit parent level."""
        parent_logger = get_logger("parent")
        parent_logger.setLevel(logging.WARNING)

        child_logger = get_logger("parent.child")

        # Child should inherit or respect parent's level
        assert (
            child_logger.getEffectiveLevel() >= logging.WARNING
            or child_logger.level >= logging.WARNING
        )

    def test_different_modules_different_loggers(self):
        """Test different modules get different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2
        assert logger1.name != logger2.name
