"""Area review scheduling derived from explicit repository metadata."""

import calendar
from datetime import date, timedelta

REVIEW_MONTHS = {
    "monthly": 1,
    "quarterly": 3,
    "annual": 12,
}


def next_review(last_reviewed: date, cycle: str) -> date:
    """Return the next review date for a supported cycle."""
    if cycle == "weekly":
        return last_reviewed + timedelta(days=7)
    months = REVIEW_MONTHS.get(cycle)
    if months is None:
        message = f"unsupported review cycle: {cycle}"
        raise ValueError(message)
    month_index = last_reviewed.month - 1 + months
    year = last_reviewed.year + month_index // 12
    month = month_index % 12 + 1
    day = min(last_reviewed.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
