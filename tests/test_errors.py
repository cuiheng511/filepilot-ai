"""Tests for filepilot.core.errors — try_safe decorator"""

from filepilot.core.errors import try_safe


def test_try_safe_returns_result_on_success():
    @try_safe(fallback=0)
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_try_safe_returns_fallback_on_exception():
    @try_safe(fallback=0)
    def fail():
        raise ValueError("nope")

    assert fail() == 0


def test_try_safe_fallback_none():
    @try_safe(fallback=None)
    def fail():
        raise RuntimeError

    assert fail() is None


def test_try_safe_passes_args():
    @try_safe(fallback="")
    def concat(a, b):
        return a + b

    assert concat("hello", " world") == "hello world"


def test_try_safe_on_error_callback():
    errors = []

    @try_safe(fallback=-1, on_error=lambda e: errors.append(str(e)))
    def fail():
        raise ValueError("op failed")

    result = fail()
    assert result == -1
    assert len(errors) == 1
    assert "op failed" in errors[0]


def test_try_safe_preserves_return_type():
    @try_safe(fallback=0)
    def div(a, b):
        return a / b

    assert isinstance(div(10, 0), int)
    assert isinstance(div(10, 2), float)
