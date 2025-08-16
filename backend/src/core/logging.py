"""Structured logging configuration for Local Web Memory Backend."""

import logging
import logging.config
import sys
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from src.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add process and thread info
        log_entry.update({
            "process_id": record.process,
            "thread_id": record.thread,
            "thread_name": record.threadName,
        })
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get extra fields (excluding standard fields)
            standard_fields = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'message'
            }
            
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in standard_fields and not key.startswith('_'):
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ContextualLogger:
    """Logger wrapper that adds contextual information to log entries."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set context that will be included in all log entries."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context."""
        self._context.clear()
    
    def _log_with_context(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log with context information."""
        # Merge context with extra kwargs
        extra = kwargs.get('extra', {})
        extra.update(self._context)
        kwargs['extra'] = extra
        
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message with context."""
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log exception with context."""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)


def setup_logging(
    log_level: str = "info",
    log_file: Optional[Path] = None,
    enable_console: bool = True,
    enable_json: bool = True
) -> None:
    """Setup structured logging configuration."""
    
    # Convert log level to uppercase
    log_level = log_level.upper()
    
    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": StructuredFormatter,
                "include_extra": True
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
            }
        },
        "handlers": {},
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": []
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": [],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": [],
                "propagate": False
            },
            "httpx": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True
            },
            "urllib3": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True
            }
        }
    }
    
    # Console handler
    if enable_console:
        if enable_json:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
                "level": log_level
            }
        else:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "detailed",
                "level": log_level
            }
        
        # Add console handler to loggers
        config["loggers"][""]["handlers"].append("console")
        config["loggers"]["uvicorn"]["handlers"].append("console")
        config["loggers"]["uvicorn.access"]["handlers"].append("console")
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_file),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": log_level
        }
        
        # Add file handler to loggers
        config["loggers"][""]["handlers"].append("file")
        config["loggers"]["uvicorn"]["handlers"].append("file")
        config["loggers"]["uvicorn.access"]["handlers"].append("file")
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log configuration info
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "console_enabled": enable_console,
            "json_enabled": enable_json,
            "file_enabled": log_file is not None,
            "log_file": str(log_file) if log_file else None
        }
    )


def get_logger(name: str) -> ContextualLogger:
    """Get a contextual logger instance."""
    return ContextualLogger(logging.getLogger(name))


def log_request_start(
    method: str,
    url: str,
    client_ip: str,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None
) -> ContextualLogger:
    """Log HTTP request start and return logger with request context."""
    logger = get_logger("api.request")
    
    # Set request context
    context = {
        "request_id": request_id,
        "method": method,
        "url": url,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "request_type": "http"
    }
    
    logger.set_context(**context)
    logger.info(
        f"Request started: {method} {url}",
        extra={"event": "request_start"}
    )
    
    return logger


def log_request_end(
    logger: ContextualLogger,
    status_code: int,
    response_time_ms: float,
    response_size: Optional[int] = None
) -> None:
    """Log HTTP request completion."""
    logger.info(
        f"Request completed: {status_code}",
        extra={
            "event": "request_end",
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "response_size": response_size
        }
    )


def log_api_call(
    service: str,
    operation: str,
    duration_ms: float,
    success: bool,
    error: Optional[str] = None,
    **kwargs
) -> None:
    """Log external API call."""
    logger = get_logger("api.external")
    
    extra = {
        "event": "api_call",
        "service": service,
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
        **kwargs
    }
    
    if error:
        extra["error"] = error
    
    if success:
        logger.info(f"API call succeeded: {service}.{operation}", extra=extra)
    else:
        logger.error(f"API call failed: {service}.{operation}", extra=extra)


def log_database_operation(
    operation: str,
    table: str,
    duration_ms: float,
    rows_affected: Optional[int] = None,
    error: Optional[str] = None
) -> None:
    """Log database operation."""
    logger = get_logger("database")
    
    extra = {
        "event": "database_operation",
        "operation": operation,
        "table": table,
        "duration_ms": duration_ms,
        "rows_affected": rows_affected
    }
    
    if error:
        extra["error"] = error
        logger.error(f"Database operation failed: {operation} on {table}", extra=extra)
    else:
        logger.info(f"Database operation: {operation} on {table}", extra=extra)


def log_cache_operation(
    operation: str,
    cache_type: str,
    key: str,
    hit: Optional[bool] = None,
    duration_ms: Optional[float] = None
) -> None:
    """Log cache operation."""
    logger = get_logger("cache")
    
    extra = {
        "event": "cache_operation",
        "operation": operation,
        "cache_type": cache_type,
        "key": key,
        "hit": hit,
        "duration_ms": duration_ms
    }
    
    logger.info(f"Cache {operation}: {cache_type}", extra=extra)


def log_security_event(
    event_type: str,
    client_ip: str,
    description: str,
    severity: str = "medium",
    **kwargs
) -> None:
    """Log security-related event."""
    logger = get_logger("security")
    
    extra = {
        "event": "security_event",
        "event_type": event_type,
        "client_ip": client_ip,
        "severity": severity,
        **kwargs
    }
    
    if severity in ["high", "critical"]:
        logger.error(f"Security event: {description}", extra=extra)
    else:
        logger.warning(f"Security event: {description}", extra=extra)


# Initialize logging when module is imported
def init_logging():
    """Initialize logging based on settings."""
    log_file = None
    if hasattr(settings, 'log_file') and settings.log_file:
        log_file = Path(settings.log_file)
    
    setup_logging(
        log_level=settings.log_level,
        log_file=log_file,
        enable_console=True,
        enable_json=True
    )


# Auto-initialize if not in test environment
if not any("pytest" in arg for arg in sys.argv):
    try:
        init_logging()
    except Exception as e:
        # Fallback to basic logging if initialization fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.getLogger(__name__).error(f"Failed to initialize structured logging: {e}")


# Export commonly used functions
__all__ = [
    'setup_logging',
    'get_logger',
    'log_request_start',
    'log_request_end',
    'log_api_call',
    'log_database_operation',
    'log_cache_operation',
    'log_security_event',
    'ContextualLogger',
    'StructuredFormatter'
]