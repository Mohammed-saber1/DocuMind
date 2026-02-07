"""
Structured Logging Configuration for DocuMind
==============================================

Provides JSON-formatted logging suitable for production environments
and log aggregation systems (ELK, CloudWatch, etc.).
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Outputs log records as JSON objects with consistent fields
    for easy parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
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
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data)


class ContextLogger:
    """
    Logger wrapper that supports adding context to log messages.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Processing document", extra={"doc_id": "123", "size": 1024})
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _log(self, level: int, message: str, extra: dict[str, Any] | None = None, **kwargs):
        if extra:
            record_extra = {"extra_data": extra}
            kwargs["extra"] = record_extra
        self._logger.log(level, message, **kwargs)
    
    def debug(self, message: str, extra: dict[str, Any] | None = None, **kwargs):
        self._log(logging.DEBUG, message, extra, **kwargs)
    
    def info(self, message: str, extra: dict[str, Any] | None = None, **kwargs):
        self._log(logging.INFO, message, extra, **kwargs)
    
    def warning(self, message: str, extra: dict[str, Any] | None = None, **kwargs):
        self._log(logging.WARNING, message, extra, **kwargs)
    
    def error(self, message: str, extra: dict[str, Any] | None = None, **kwargs):
        self._log(logging.ERROR, message, extra, **kwargs)
    
    def critical(self, message: str, extra: dict[str, Any] | None = None, **kwargs):
        self._log(logging.CRITICAL, message, extra, **kwargs)
    
    def exception(self, message: str, extra: dict[str, Any] | None = None, **kwargs):
        kwargs["exc_info"] = True
        self._log(logging.ERROR, message, extra, **kwargs)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: str | None = None
) -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON formatting; otherwise, use plain text
        log_file: Optional file path for log output
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
        ))
    
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        ContextLogger instance
    """
    return ContextLogger(logging.getLogger(name))


# Example usage
if __name__ == "__main__":
    setup_logging(level="DEBUG", json_format=True)
    
    logger = get_logger(__name__)
    
    logger.info("Application started")
    logger.debug("Debug message", extra={"user_id": "123"})
    logger.warning("This is a warning")
    
    try:
        raise ValueError("Test exception")
    except Exception:
        logger.exception("An error occurred", extra={"context": "test"})
