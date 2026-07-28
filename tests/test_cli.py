"""Command-line interface tests."""

from pathlib import Path

from workrepo.cli import main

PROJECT_ROOT = Path(__file__).parents[1]


def test_check_command_succeeds() -> None:
    """The check command gives a concise success result."""
    result = main(("--root", str(PROJECT_ROOT), "check"))

    assert result == 0


def test_cli_supports_capture_to_review_workflow(repository: Path) -> None:
    """A user can establish work context without manually placing files."""
    root_arguments = ("--root", str(repository))

    assert (
        main(
            (
                *root_arguments,
                "capture",
                "Review interface monitoring",
                "--date",
                "2026-07-29",
            ),
        )
        == 0
    )
    assert (
        main(
            (
                *root_arguments,
                "new",
                "area",
                "erp-operations",
                "--title",
                "ERP運用",
                "--date",
                "2026-07-29",
            ),
        )
        == 0
    )
    assert (
        main(
            (
                *root_arguments,
                "new",
                "project",
                "erp-upgrade",
                "--title",
                "ERP更改",
                "--related",
                "area:erp-operations",
                "--date",
                "2026-07-29",
            ),
        )
        == 0
    )
    assert main((*root_arguments, "refresh")) == 0

    dashboard = (repository / "DASHBOARD.md").read_text(encoding="utf-8")
    assert "Open items: **1**" in dashboard
    assert "[ERP更改](20-projects/erp-upgrade/index.md)" in dashboard
