"""Retry utility: configurable max_retries via kwarg, default 2."""
import functools
from mini_harness.logger import log

_retry_counter = 0


def reset_retry_counter() -> None:
    """Reset the module-level retry counter (call before pipeline run)."""
    global _retry_counter
    _retry_counter = 0


def get_retry_counter() -> int:
    """Return total retries accumulated across all @with_retry calls."""
    return _retry_counter


def with_retry(stage: str, default_max_retries: int = 2):
    """Decorator: retry on failure, max_retries configurable via kwarg.

    The decorated function may accept max_retries=N to override the default.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            global _retry_counter
            max_retries = kwargs.pop("max_retries", default_max_retries)
            last_exc = None
            for attempt in range(1, max_retries + 2):
                if attempt > 1:
                    _retry_counter += 1
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