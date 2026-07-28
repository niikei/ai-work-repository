"""Command-line interface tests."""

from pathlib import Path

from workrepo.cli import main

PROJECT_ROOT = Path(__file__).parents[1]


def test_check_command_succeeds() -> None:
    """The check command gives a concise success result."""
    result = main(("--root", str(PROJECT_ROOT), "check"))

    assert result == 0
