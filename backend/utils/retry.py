import time
import logging
from functools import wraps
import httpx

logger = logging.getLogger(__name__)


def with_retry(max_retries=3, base_delay=2, max_delay=30):
    """
    Decorator for exponential backoff retries.
    Catches HTTP and network-related errors.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (
                    httpx.RequestError,
                    httpx.HTTPStatusError,
                    TimeoutError,
                    ConnectionError,
                ) as e:
                    if retries == max_retries:
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_retries} retries. Final error: {e}"
                        )
                        raise e

                    delay = min(base_delay * (2**retries), max_delay)
                    logger.warning(
                        f"Function '{func.__name__}' failed with {e}. Retrying in {delay} seconds... ({retries + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    retries += 1
                except Exception as e:
                    # For non-network/HTTP errors, raise immediately
                    logger.error(f"Unexpected error in '{func.__name__}': {e}")
                    raise e

        return wrapper

    return decorator
