"""Repository policy loading tests."""

from pathlib import Path

import pytest

from workrepo.policy import POLICY_PATH, load_policy


def test_policy_defines_repository_calendar_timezone(repository: Path) -> None:
    """Dates are evaluated consistently on local machines and UTC CI runners."""
    assert load_policy(repository).timezone == "Asia/Tokyo"


def test_policy_rejects_unknown_timezone(repository: Path) -> None:
    """A typo cannot silently fall back to the runner's local timezone."""
    path = repository / POLICY_PATH
    path.write_text(
        path.read_text(encoding="utf-8").replace("Asia/Tokyo", "Invalid/Timezone"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"unknown policy\.timezone"):
        load_policy(repository)
