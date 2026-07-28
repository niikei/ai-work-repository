"""Local Git integration without requiring a hosted remote."""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from workrepo.generated import remove_related_block
from workrepo.models import Issue
from workrepo.validation import (
    inspect_repository,
    repository_warnings,
)
from workrepo.yamlutil import load_yaml

HOOKS_PATH = ".githooks"
PRE_COMMIT_PATH = Path(HOOKS_PATH) / "pre-commit"


@dataclass(frozen=True, slots=True)
class CheckReport:
    """Errors and warnings produced for one repository snapshot."""

    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...]


def check_worktree(root: Path) -> CheckReport:
    """Check the current working-tree snapshot."""
    state, errors = inspect_repository(root)
    return CheckReport(tuple(errors), tuple(repository_warnings(state)))


def check_staged(root: Path) -> CheckReport:
    """Check exactly what is currently staged in the Git index."""
    repository_root = root.resolve()
    with staged_tree(repository_root) as staged_root:
        state, errors = inspect_repository(staged_root)
        warnings = repository_warnings(state)
    errors.extend(_updated_date_issues(repository_root))
    return CheckReport(tuple(sorted(errors)), tuple(sorted(warnings)))


@contextmanager
def staged_tree(root: Path) -> Iterator[Path]:
    """Materialize the Git index in a temporary directory."""
    _git(root, "rev-parse", "--git-dir")
    with tempfile.TemporaryDirectory(prefix="workrepo-staged-") as temporary:
        staged_root = Path(temporary)
        prefix = f"{staged_root}{os.sep}"
        _git(root, "checkout-index", "--all", f"--prefix={prefix}")
        yield staged_root


def install_hooks(root: Path) -> None:
    """Activate repository-managed hooks for the local clone."""
    hook = root / PRE_COMMIT_PATH
    if not hook.is_file():
        message = f"managed hook does not exist: {PRE_COMMIT_PATH}"
        raise FileNotFoundError(message)
    hook.chmod(hook.stat().st_mode | 0o111)
    _git(root, "config", "core.hooksPath", HOOKS_PATH)


def hooks_active(root: Path) -> bool:
    """Return whether the managed hooks path is active in this clone."""
    result = _git(root, "config", "--get", "core.hooksPath", check=False)
    return result.returncode == 0 and result.stdout.strip() == HOOKS_PATH


def is_git_repository(root: Path) -> bool:
    """Return whether *root* belongs to a Git working tree."""
    return _git(root, "rev-parse", "--is-inside-work-tree", check=False).returncode == 0


def _updated_date_issues(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    today = datetime.now(tz=UTC).astimezone().date()
    for path in _staged_paths(root):
        if path.suffix != ".md":
            continue
        previous = _git_content(root, f"HEAD:{path.as_posix()}")
        current = _git_content(root, f":{path.as_posix()}")
        if previous is None or current is None:
            continue
        previous_source = remove_related_block(previous, path=path)
        current_source = remove_related_block(current, path=path)
        if previous_source == current_source:
            continue
        previous_created = _frontmatter_date(previous_source, "created")
        current_created = _frontmatter_date(current_source, "created")
        if previous_created is not None and current_created != previous_created:
            issues.append(
                Issue(
                    path,
                    "created is immutable after the document is committed",
                ),
            )
        current_updated = _frontmatter_date(current_source, "updated")
        if current_updated is not None and current_updated != today:
            issues.append(
                Issue(
                    path,
                    f"content changed but updated is not today: {today.isoformat()}",
                ),
            )
    return issues


def _staged_paths(root: Path) -> list[Path]:
    result = _git(
        root,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=ACMR",
        "-z",
    )
    return [Path(value) for value in result.stdout.split("\0") if value]


def _git_content(root: Path, object_name: str) -> str | None:
    result = _git(root, "show", object_name, check=False)
    return result.stdout if result.returncode == 0 else None


def _frontmatter_value(source: str, field: str) -> object | None:
    lines = source.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None
    try:
        raw = load_yaml("\n".join(lines[1:closing]))
    except yaml.YAMLError:
        return None
    if not isinstance(raw, dict):
        return None
    return raw.get(field)


def _frontmatter_date(source: str, field: str) -> date | None:
    value = _frontmatter_value(source, field)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        message = "git executable was not found"
        raise FileNotFoundError(message)
    try:
        return subprocess.run(  # noqa: S603
            (executable, "-C", str(root), *arguments),
            check=check,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or "Git command failed"
        raise ValueError(detail) from error
