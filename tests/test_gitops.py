"""Tests for local Git checks and managed hooks."""

import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from workrepo.creation import CreateRequest, create_document
from workrepo.gitops import check_staged, hooks_active, install_hooks

PROJECT_ROOT = Path(__file__).parents[1]


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        pytest.skip("Git is not installed")
    return subprocess.run(  # noqa: S603
        (executable, "-C", str(root), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repository(repository: Path) -> Path:
    """Initialize a disposable repository with the production hook."""
    shutil.copytree(PROJECT_ROOT / ".githooks", repository / ".githooks")
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Work Repository Test")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "add", ".")
    _git(repository, "commit", "--quiet", "-m", "Initial snapshot")
    return repository


def test_check_staged_uses_index_not_worktree(git_repository: Path) -> None:
    invalid = git_repository / "00-inbox/a.md"
    invalid.write_text("# Temporary\n", encoding="utf-8")
    _git(git_repository, "add", invalid.relative_to(git_repository).as_posix())
    invalid.unlink()

    report = check_staged(git_repository)

    assert len(report.errors) == 1
    assert report.errors[0].path == Path("00-inbox/a.md")


def test_check_staged_requires_updated_change(git_repository: Path) -> None:
    yesterday = datetime.now(tz=UTC).astimezone().date() - timedelta(days=1)
    document = create_document(
        git_repository,
        CreateRequest(
            document_type="project",
            slug="upgrade",
            title="Upgrade",
            document_date=yesterday,
        ),
    )
    _git(git_repository, "add", ".")
    _git(git_repository, "commit", "--quiet", "-m", "Add project")
    source = document.read_text(encoding="utf-8")
    document.write_text(source.replace("## Outcome", "## Revised outcome"), encoding="utf-8")
    _git(git_repository, "add", document.relative_to(git_repository).as_posix())

    report = check_staged(git_repository)

    assert any("updated is not today" in issue.message for issue in report.errors)


def test_check_staged_allows_multiple_updates_on_same_day(git_repository: Path) -> None:
    document = create_document(
        git_repository,
        CreateRequest(
            document_type="project",
            slug="same-day",
            title="Same-day editing",
        ),
    )
    _git(git_repository, "add", ".")
    _git(git_repository, "commit", "--quiet", "-m", "Add project")
    source = document.read_text(encoding="utf-8")
    document.write_text(source.replace("## Outcome", "## Revised outcome"), encoding="utf-8")
    _git(git_repository, "add", document.relative_to(git_repository).as_posix())

    report = check_staged(git_repository)

    assert not report.errors


def test_check_staged_rejects_created_date_change(git_repository: Path) -> None:
    document = create_document(
        git_repository,
        CreateRequest(
            document_type="project",
            slug="immutable-created",
            title="Immutable created date",
        ),
    )
    _git(git_repository, "add", ".")
    _git(git_repository, "commit", "--quiet", "-m", "Add project")
    today = datetime.now(tz=UTC).astimezone().date()
    yesterday = today - timedelta(days=1)
    source = document.read_text(encoding="utf-8")
    document.write_text(
        source.replace(
            f"created: {today.isoformat()}",
            f"created: {yesterday.isoformat()}",
        ),
        encoding="utf-8",
    )
    _git(git_repository, "add", document.relative_to(git_repository).as_posix())

    report = check_staged(git_repository)

    assert any("created is immutable" in issue.message for issue in report.errors)


def test_install_hooks_and_real_commit_reject_invalid_inbox(git_repository: Path) -> None:
    install_hooks(git_repository)
    assert hooks_active(git_repository)
    invalid = git_repository / "00-inbox/a.md"
    invalid.write_text("# Temporary\n", encoding="utf-8")
    _git(git_repository, "add", invalid.relative_to(git_repository).as_posix())

    result = _git(
        git_repository,
        "commit",
        "-m",
        "Commit invalid inbox file",
        check=False,
    )

    assert result.returncode != 0
    assert "Inbox only allows" in f"{result.stdout}\n{result.stderr}"
