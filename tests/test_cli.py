"""Command-line interface tests."""

from pathlib import Path

import pytest

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
    assert (
        main(
            (
                *root_arguments,
                "new",
                "log",
                "erp-upgrade-meeting",
                "--title",
                "ERP更改定例",
                "--related",
                "project:erp-upgrade",
                "--template",
                "meeting",
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
                "artifact",
                "weekly-report",
                "--title",
                "ERP更改週次報告",
                "--parent",
                "project:erp-upgrade",
                "--kind",
                "weekly-report",
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
    assert "## Participants" in (
        repository / "10-log/2026/07/2026-07-27-week/2026-07-29-erp-upgrade-meeting.md"
    ).read_text(encoding="utf-8")
    assert (repository / "20-projects/erp-upgrade/reports/weekly-report.md").is_file()


def test_cli_auto_detects_root_from_nested_directory(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Commands work from a Project directory without an explicit root."""
    nested = repository / "20-projects/example"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    assert main(("capture", "Nested capture", "--date", "2026-07-29")) == 0
    assert (repository / "00-inbox/2026-07-29.md").is_file()


def test_cli_reports_missing_repository_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A path outside a repository receives one actionable error."""
    result = main(("--root", str(tmp_path), "check"))

    assert result == 1
    output = capsys.readouterr().out
    assert output.startswith("ERROR no work repository found")
    assert "Traceback" not in output


def test_cli_list_and_search_are_human_readable(
    repository: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Large repositories can be filtered without opening generated JSON."""
    project = repository / "20-projects/erp-upgrade/index.md"
    project.parent.mkdir(parents=True)
    project.write_text(
        """---
type: project
id: project:erp-upgrade
status: active
health: amber
created: 2026-07-29
updated: 2026-07-29
related: []
---

# ERP Upgrade

Cutover planning.
""",
        encoding="utf-8",
    )

    assert main(("--root", str(repository), "list", "--type", "project")) == 0
    list_output = capsys.readouterr().out
    assert "project:erp-upgrade" in list_output
    assert "ERP Upgrade" in list_output

    assert main(("--root", str(repository), "search", "cutover")) == 0
    search_output = capsys.readouterr().out
    assert "ERP Upgrade" in search_output
