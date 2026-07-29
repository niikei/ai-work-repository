"""Local Git integration without requiring a hosted remote."""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from workrepo.clock import current_date, use_date
from workrepo.generated import remove_related_block
from workrepo.models import Issue
from workrepo.policy import load_policy
from workrepo.repository import refresh_repository
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


@dataclass(frozen=True, slots=True)
class RefCheckReport:
    """Validation result for one isolated Git commit snapshot."""

    commit: str
    report: CheckReport


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


def check_ref(root: Path, ref: str) -> RefCheckReport:
    """Validate and regenerate one Git commit without touching the working tree."""
    repository_root = root.resolve()
    commit = _resolve_commit(repository_root, ref)
    with ref_tree(repository_root, commit) as snapshot:
        review_date = _commit_date(repository_root, commit, snapshot)
        with use_date(review_date):
            state, errors = inspect_repository(snapshot)
            warnings = repository_warnings(state)
            if not errors:
                refresh_repository(snapshot)
                errors.extend(_generated_drift(snapshot, commit))
    report = CheckReport(tuple(sorted(errors)), tuple(sorted(warnings)))
    return RefCheckReport(commit=commit, report=report)


@contextmanager
def staged_tree(root: Path) -> Iterator[Path]:
    """Materialize the Git index in a temporary directory."""
    _git(root, "rev-parse", "--git-dir")
    with tempfile.TemporaryDirectory(prefix="workrepo-staged-") as temporary:
        staged_root = Path(temporary)
        prefix = f"{staged_root}{os.sep}"
        _git(root, "checkout-index", "--all", f"--prefix={prefix}")
        yield staged_root


@contextmanager
def ref_tree(root: Path, commit: str) -> Iterator[Path]:
    """Materialize one detached commit and remove all worktree metadata afterward."""
    _git(root, "rev-parse", "--git-dir")
    with tempfile.TemporaryDirectory(prefix="workrepo-ref-") as temporary:
        snapshot = Path(temporary) / "snapshot"
        added = False
        try:
            _git(root, "worktree", "add", "--quiet", "--detach", str(snapshot), commit)
            added = True
            yield snapshot
        finally:
            if added:
                _git(root, "worktree", "remove", "--force", str(snapshot), check=False)
            _git(root, "worktree", "prune", check=False)


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


def _resolve_commit(root: Path, ref: str) -> str:
    if not ref.strip():
        message = "Git ref must not be empty"
        raise ValueError(message)
    try:
        result = _git(
            root,
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{ref}^{{commit}}",
        )
    except ValueError as error:
        message = f"Git ref does not resolve to a commit: {ref}"
        raise ValueError(message) from error
    commit = result.stdout.strip()
    if not commit:
        message = f"Git ref did not resolve to a commit: {ref}"
        raise ValueError(message)
    return commit


def _commit_date(root: Path, commit: str, snapshot: Path) -> date:
    result = _git(root, "show", "--no-patch", "--format=%cI", commit)
    timestamp = datetime.fromisoformat(result.stdout.strip())
    timezone = ZoneInfo(load_policy(snapshot).timezone)
    return timestamp.astimezone(timezone).date()


def _generated_drift(snapshot: Path, commit: str) -> list[Issue]:
    result = _git(snapshot, "diff", "--name-only", "-z", "--")
    paths = sorted(Path(value) for value in result.stdout.split("\0") if value)
    short_commit = commit[:12]
    return [
        Issue(path, f"generated content is stale at Git snapshot {short_commit}")
        for path in paths
    ]


def _updated_date_issues(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    today = current_date(load_policy(root).timezone)
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
