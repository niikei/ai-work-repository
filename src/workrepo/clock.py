"""Repository-calendar helpers independent from the machine timezone."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime
from zoneinfo import ZoneInfo

_DATE_OVERRIDE: ContextVar[date | None] = ContextVar("workrepo_date_override", default=None)


def current_date(timezone_name: str) -> date:
    """Return today's date in the repository's configured timezone."""
    if override := _DATE_OVERRIDE.get():
        return override
    return datetime.now(tz=ZoneInfo(timezone_name)).date()


@contextmanager
def use_date(value: date) -> Iterator[None]:
    """Use one deterministic repository date within the current context."""
    token = _DATE_OVERRIDE.set(value)
    try:
        yield
    finally:
        _DATE_OVERRIDE.reset(token)
