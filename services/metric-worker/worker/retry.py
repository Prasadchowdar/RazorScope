"""Retry decorator with exponential backoff for transient I/O failures."""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, Type

log = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """Retry a function up to max_attempts times with exponential backoff."""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    wait = backoff_base * (2 ** (attempt - 1))
                    log.warning(
                        "transient error in %s (attempt %d/%d), retrying in %.1fs: %s",
                        fn.__name__, attempt, max_attempts, wait, exc,
                    )
                    time.sleep(wait)
        return wrapper
    return decorator
