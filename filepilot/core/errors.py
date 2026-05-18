"""Error handling utilities for graceful degradation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def try_safe(
    fallback: T,
    on_error: Callable[[Exception], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: run fn, return fallback on exception with optional error callback.

    Usage::

        @try_safe(fallback=0, on_error=lambda e: logger.warning(e))
        def divide(a, b):
            return a / b
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if on_error:
                    on_error(e)
                return fallback
        return wrapper
    return decorator
