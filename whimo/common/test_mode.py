from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_test_mode: ContextVar[bool] = ContextVar("test_mode", default=False)


def is_test_mode() -> bool:
    return _test_mode.get()


@contextmanager
def enable_test_mode() -> Iterator[None]:
    token = _test_mode.set(True)
    try:
        yield
    finally:
        _test_mode.reset(token)
