"""Area review schedule tests."""

from datetime import date

import pytest

from workrepo.review import next_review


@pytest.mark.parametrize(
    ("last_reviewed", "cycle", "expected"),
    [
        (date(2026, 1, 31), "monthly", date(2026, 2, 28)),
        (date(2024, 2, 29), "annual", date(2025, 2, 28)),
        (date(2026, 11, 30), "quarterly", date(2027, 2, 28)),
        (date(2026, 7, 29), "weekly", date(2026, 8, 5)),
    ],
)
def test_next_review_handles_calendar_boundaries(
    last_reviewed: date,
    cycle: str,
    expected: date,
) -> None:
    """Month-end and leap-year reviews stay on valid calendar dates."""
    assert next_review(last_reviewed, cycle) == expected
