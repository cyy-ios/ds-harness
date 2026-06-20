"""重试工具：失败重试最大 2 次。"""
import functools
from mini_harness.logger import log


def with_retry(stage: str, max_retries: int = 2):
    """装饰器：对函数执行失败进行重试。

    max_retries=2 表示额外重试 2 次，总共最多执行 3 次。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 2):  # 1 initial + 2 retries
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
