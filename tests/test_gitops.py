"""Tests for local Git checks and managed hooks."""

import os
import shutil
import subprocess
from collections.abc import Mapping
from datetime import date, timedelta
from pathlib import Path

import pytest

from workrepo.cli import main
from workrepo.clock import current_date, use_date
from workrepo.creation import CreateRequest, create_document
from workrepo.gitops import check_ref, check_staged, hooks_active, install_hooks
from workrepo.repository import refresh_repository

PROJECT_ROOT = Path(__file__).parents[1]
TIMEZONE = "Asia/Tokyo"


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        pytest.skip("Git is not installed")
    return subprocess.run(  # noqa: S603
        (executable, "-C", str(root), *arguments),
        check=check,
        capture_output=True,
        text=True,
        env=None if env is None else {**os.environ, **env},
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


def _commit_all(
    root: Path,
    message: str,
    *,
    commit_date: str | None = None,
) -> str:
    _git(root, "add", ".")
    environment = (
        None
        if commit_date is None
        else {
            "GIT_AUTHOR_DATE": commit_date,
            "GIT_COMMITTER_DATE": commit_date,
        }
    )
    _git(root, "commit", "--quiet", "-m", message, env=environment)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def test_check_ref_isolated_from_dirty_worktree(git_repository: Path) -> None:
    """Historical validation neither reads nor changes the caller's files."""
    refresh_repository(git_repository)
    commit = _commit_all(git_repository, "Add generated views")
    invalid = git_repository / "00-inbox/a.md"
    invalid.write_text("# Dirty working tree\n", encoding="utf-8")
    status_before = _git(git_repository, "status", "--porcelain=v1").stdout
    worktrees_before = _git(git_repository, "worktree", "list", "--porcelain").stdout

    result = check_ref(git_repository, commit)

    assert not result.report.errors
    assert _git(git_repository, "status", "--porcelain=v1").stdout == status_before
    assert _git(git_repository, "worktree", "list", "--porcelain").stdout == worktrees_before


def test_check_ref_detects_stale_generated_files(git_repository: Path) -> None:
    """A structurally valid commit still fails when refresh was omitted."""
    refresh_repository(git_repository)
    _commit_all(git_repository, "Add generated views")
    create_document(
        git_repository,
        CreateRequest(
            document_type="project",
            slug="stale-dashboard",
            title="Stale dashboard",
        ),
    )
    commit = _commit_all(git_repository, "Add project without refresh")

    result = check_ref(git_repository, commit)

    stale_paths = {issue.path for issue in result.report.errors}
    assert Path("DASHBOARD.md") in stale_paths
    assert Path("NAVIGATION.md") in stale_paths


def test_check_ref_uses_commit_date_for_generated_views(git_repository: Path) -> None:
    """A historical dashboard is reproduced at its commit-local date."""
    historical_date = date(2026, 7, 1)
    create_document(
        git_repository,
        CreateRequest(
            document_type="area",
            slug="historical-area",
            title="Historical Area",
            document_date=historical_date,
        ),
    )
    with use_date(historical_date):
        refresh_repository(git_repository)
    commit = _commit_all(
        git_repository,
        "Add historical Area",
        commit_date="2026-07-01T12:00:00+09:00",
    )

    result = check_ref(git_repository, commit)

    assert not result.report.errors


def test_check_ref_accepts_root_and_merge_commits(git_repository: Path) -> None:
    """Snapshot validation does not assume that one parent exists."""
    root_commit = _git(
        git_repository,
        "rev-list",
        "--max-parents=0",
        "HEAD",
    ).stdout.strip()
    root_result = check_ref(git_repository, root_commit)
    assert root_result.commit == root_commit
    assert not root_result.report.errors

    base_branch = _git(
        git_repository,
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    ).stdout.strip()
    _git(git_repository, "switch", "-c", "feature", "--quiet")
    (git_repository / "README.md").write_text("# Feature\n", encoding="utf-8")
    _commit_all(git_repository, "Add feature")
    _git(git_repository, "switch", base_branch, "--quiet")
    (git_repository / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
    _commit_all(git_repository, "Add contribution guide")
    _git(git_repository, "merge", "--no-ff", "--quiet", "feature", "-m", "Merge feature")
    merge_commit = _git(git_repository, "rev-parse", "HEAD").stdout.strip()

    merge_result = check_ref(git_repository, merge_commit)
    assert merge_result.commit == merge_commit
    assert not merge_result.report.errors


def test_check_ref_rejects_invalid_ref(git_repository: Path) -> None:
    """User input cannot be interpreted as a Git option or non-commit object."""
    with pytest.raises(ValueError, match="does not resolve to a commit"):
        check_ref(git_repository, "--not-a-ref")


def test_cli_check_ref_reports_resolved_snapshot(
    git_repository: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    refresh_repository(git_repository)
    commit = _commit_all(git_repository, "Add generated views")

    result = main(
        (
            "--root",
            str(git_repository),
            "check",
            "--ref",
            commit[:12],
            "--strict",
        ),
    )

    assert result == 0
    output = capsys.readouterr().out
    assert f"Git snapshot: {commit}" in output
    assert "Repository is valid." in output


def test_check_staged_uses_index_not_worktree(git_repository: Path) -> None:
    invalid = git_repository / "00-inbox/a.md"
    invalid.write_text("# Temporary\n", encoding="utf-8")
    _git(git_repository, "add", invalid.relative_to(git_repository).as_posix())
    invalid.unlink()

    report = check_staged(git_repository)

    assert len(report.errors) == 1
    assert report.errors[0].path == Path("00-inbox/a.md")


def test_check_staged_requires_updated_change(git_repository: Path) -> None:
    yesterday = current_date(TIMEZONE) - timedelta(days=1)
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
    today = current_date(TIMEZONE)
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


def test_installed_hook_rejects_markdown_lint_issue(git_repository: Path) -> None:
    """The hook lints the staged snapshot after structural validation."""
    install_hooks(git_repository)
    readme = git_repository / "README.md"
    readme.write_text("# Repository\n\nTrailing space \n", encoding="utf-8")
    _git(git_repository, "add", readme.name)

    result = _git(
        git_repository,
        "commit",
        "-m",
        "Commit malformed Markdown",
        check=False,
    )

    assert result.returncode != 0
    assert "MD009" in f"{result.stdout}\n{result.stderr}"
