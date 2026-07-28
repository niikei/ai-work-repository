"""Shared calendar conventions for work records."""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class WorkWeek:
    """A Monday-based work week with human and machine representations."""

    start: date
    iso_label: str

    @property
    def directory_name(self) -> str:
        """Return the human-readable directory name."""
        return f"{self.start.isoformat()}-week"


def work_week(day: date) -> WorkWeek:
    """Return the Monday-based week containing a calendar date."""
    start = day - timedelta(days=day.weekday())
    iso_calendar = day.isocalendar()
    return WorkWeek(
        start=start,
        iso_label=f"{iso_calendar.year}-W{iso_calendar.week:02d}",
    )
