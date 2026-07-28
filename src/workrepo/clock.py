"""Repository-calendar helpers independent from the machine timezone."""

from datetime import date, datetime
from zoneinfo import ZoneInfo


def current_date(timezone_name: str) -> date:
    """Return today's date in the repository's configured timezone."""
    return datetime.now(tz=ZoneInfo(timezone_name)).date()
