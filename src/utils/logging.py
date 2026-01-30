"""Structured JSON logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON output with standard fields.

    Standard fields included in every log:
    - timestamp: ISO format UTC timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - event: Event name/type
    - message: Log message (via 'event' in structlog)

    Dynamic context fields can be added per-log:
    - doc_id: Document identifier
    - filename: Document filename
    - user_id: User identifier
    - Any other context-specific fields
    """
    # Configure standard library logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog processors
    structlog.configure(
        processors=[
            # Add contextvars for request-scoped context
            structlog.contextvars.merge_contextvars,
            # Add log level
            structlog.processors.add_log_level,
            # Add ISO timestamp
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            # Handle exceptions
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Ensure 'event' becomes 'message' in final output
            _rename_event_to_message,
            # Output as JSON
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _rename_event_to_message(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Processor to rename 'event' field to 'message' for clarity."""
    if "event" in event_dict:
        # Keep original event as 'message', add explicit 'event' if provided
        message = event_dict.pop("event")
        event_dict["message"] = message
        # If no explicit event type was set, use the message as event
        if "event" not in event_dict:
            event_dict["event"] = event_dict.get("event_type", method_name)
    return event_dict


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured structlog logger instance.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        A bound logger with the specified name
    """
    return structlog.get_logger(name)


# Convenience functions for common log patterns


def log_request_start(
    logger: structlog.BoundLogger,
    event: str,
    **context: Any,
) -> None:
    """Log the start of a request/operation.

    Args:
        logger: The structlog logger instance
        event: Event name (e.g., 'upload_started', 'get_status_started')
        **context: Dynamic context fields (doc_id, filename, user_id, etc.)
    """
    logger.info(
        f"{event.replace('_', ' ').title()}",
        event_type=event,
        **context,
    )


def log_request_success(
    logger: structlog.BoundLogger,
    event: str,
    **context: Any,
) -> None:
    """Log successful completion of a request/operation.

    Args:
        logger: The structlog logger instance
        event: Event name (e.g., 'upload_completed', 'get_status_completed')
        **context: Dynamic context fields (doc_id, processing_time_ms, etc.)
    """
    logger.info(
        f"{event.replace('_', ' ').title()}",
        event_type=event,
        **context,
    )


def log_request_error(
    logger: structlog.BoundLogger,
    event: str,
    error_type: str,
    error_message: str,
    **context: Any,
) -> None:
    """Log a failed request/operation with error details.

    Args:
        logger: The structlog logger instance
        event: Event name (e.g., 'upload_failed', 'processing_failed')
        error_type: Exception class name or error category
        error_message: Human-readable error description
        **context: Dynamic context fields (doc_id, stack_trace, etc.)
    """
    logger.error(
        f"{event.replace('_', ' ').title()}",
        event_type=event,
        error_type=error_type,
        error_message=error_message,
        **context,
    )
