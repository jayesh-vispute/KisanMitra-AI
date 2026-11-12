"""
KisanMitra AI — Structured Logging Setup
Configures application-wide logging with structured format and API metrics tracking.
"""

import logging
from logging.handlers import RotatingFileHandler
import time
from functools import wraps
import os
import contextvars

# Context variable for request ID
request_id_var = contextvars.ContextVar("request_id", default="NO-REQ-ID")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True

# ---------------------------------------------------------------------------
# Configure root logger for the application
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s | [%(request_id)s] | %(name)-25s | %(levelname)-7s | %(message)s"

def setup_logging(level=logging.INFO):
    """Configure application-wide logging with log rotation and request IDs."""
    
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "kisanmitra.log")

    # Set up formatter and filter
    formatter = logging.Formatter(LOG_FORMAT)
    req_filter = RequestIdFilter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(req_filter)

    # File handler with rotation (10 MB max size, keep 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(req_filter)

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the KisanMitra namespace."""
    return logging.getLogger(f"KisanMitra.{name}")


# ---------------------------------------------------------------------------
# API call timing decorator
# ---------------------------------------------------------------------------
def log_api_call(logger_name: str = "API"):
    """
    Decorator that logs API call duration, success/failure, and response size.
    """
    api_logger = get_logger(logger_name)

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = round((time.time() - start) * 1000)
                size = len(result) if isinstance(result, (list, dict, str)) else "N/A"
                api_logger.info(
                    f"{func.__name__} completed in {elapsed}ms | records={size}"
                )
                return result
            except Exception as e:
                elapsed = round((time.time() - start) * 1000)
                api_logger.error(
                    f"{func.__name__} FAILED in {elapsed}ms | error={type(e).__name__}: {e}"
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = round((time.time() - start) * 1000)
                size = len(result) if isinstance(result, (list, dict, str)) else "N/A"
                api_logger.info(
                    f"{func.__name__} completed in {elapsed}ms | records={size}"
                )
                return result
            except Exception as e:
                elapsed = round((time.time() - start) * 1000)
                api_logger.error(
                    f"{func.__name__} FAILED in {elapsed}ms | error={type(e).__name__}: {e}"
                )
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
