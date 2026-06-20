"""Retry utility: configurable max_retries via kwarg, default 2."""
import functools
from mini_harness.logger import log


def with_retry(stage: str, default_max_retries: int = 2):
    """Decorator: retry on failure, max_retries configurable via kwarg.

    The decorated function may accept max_retries=N to override the default.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = kwargs.pop("max_retries", default_max_retries)
            last_exc = None
            for attempt in range(1, max_retries + 2):
                try:
                    result = func(*args, **kwargs)
                    log(attempt, stage, "ok", retries_used=attempt - 1)
                    return result
                except Exception as exc:
                    last_exc = exc
                    log(attempt, stage, "fail", error=str(exc))
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
