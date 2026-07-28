"""Inbox structure, backlog health, and review views."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from workrepo.models import Issue
from workrepo.policy import InboxPolicy

INBOX_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
OPEN_ITEM_PATTERN = re.compile(r"^- \[ \] (.+)$", flags=re.MULTILINE)
DONE_ITEM_PATTERN = re.compile(r"^- \[[xX]\] (.+)$", flags=re.MULTILINE)


@dataclass(frozen=True, slots=True)
class InboxFile:
    """Metrics for one dated Inbox file."""

    path: Path
    capture_date: date
    age_days: int
    open_items: tuple[str, ...]
    completed_items: int


@dataclass(frozen=True, slots=True)
class InboxReport:
    """Repository Inbox health at one point in time."""

    files: tuple[InboxFile, ...]
    open_items: int
    overdue_items: int
    oldest_age_days: int | None
    errors: tuple[Issue, ...]
    warnings: tuple[Issue, ...]


def inspect_inbox(
    root: Path,
    inbox_root: Path,
    policy: InboxPolicy,
    *,
    today: date,
) -> InboxReport:
    """Inspect Inbox structure and aging against local policy."""
    directory = root / inbox_root
    files: list[InboxFile] = []
    errors: list[Issue] = []
    warnings: list[Issue] = []
    if not directory.exists():
        errors.append(Issue(inbox_root, "Inbox directory does not exist"))
        return _report(files, errors, warnings, policy, inbox_root)

    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        inbox_relative = path.relative_to(directory)
        if inbox_relative == Path("README.md"):
            continue
        if len(inbox_relative.parts) != 1 or INBOX_FILE_PATTERN.fullmatch(path.name) is None:
            errors.append(
                Issue(
                    relative,
                    "Inbox only allows README.md and top-level YYYY-MM-DD.md files",
                ),
            )
            continue
        inbox_file, file_errors, file_warnings = _inspect_file(
            path,
            relative,
            policy,
            today=today,
        )
        if inbox_file is not None:
            files.append(inbox_file)
        errors.extend(file_errors)
        warnings.extend(file_warnings)
    return _report(files, errors, warnings, policy, inbox_root)


def _inspect_file(
    path: Path,
    relative: Path,
    policy: InboxPolicy,
    *,
    today: date,
) -> tuple[InboxFile | None, list[Issue], list[Issue]]:
    errors: list[Issue] = []
    warnings: list[Issue] = []
    try:
        capture_date = date.fromisoformat(path.stem)
    except ValueError:
        errors.append(Issue(relative, "Inbox filename must contain a valid ISO date"))
        return None, errors, warnings
    if capture_date > today:
        errors.append(Issue(relative, "Inbox capture date must not be in the future"))
    source = path.read_text(encoding="utf-8")
    expected_heading = f"# {capture_date.isoformat()} Inbox"
    if not source.splitlines() or source.splitlines()[0] != expected_heading:
        errors.append(Issue(relative, f"first line must be: {expected_heading}"))
    open_items = tuple(OPEN_ITEM_PATTERN.findall(source))
    completed_items = len(DONE_ITEM_PATTERN.findall(source))
    if not open_items and completed_items == 0:
        errors.append(Issue(relative, "dated Inbox file must contain a checklist item"))
    age_days = max(0, (today - capture_date).days)
    inbox_file = InboxFile(
        path=relative,
        capture_date=capture_date,
        age_days=age_days,
        open_items=open_items,
        completed_items=completed_items,
    )
    if open_items and age_days >= policy.block_after_days:
        errors.append(
            Issue(
                relative,
                f"{len(open_items)} open Inbox item(s) are {age_days} days old",
            ),
        )
    elif open_items and age_days >= policy.warn_after_days:
        warnings.append(
            Issue(
                relative,
                f"{len(open_items)} open Inbox item(s) are {age_days} days old",
            ),
        )
    if not open_items and completed_items:
        warnings.append(
            Issue(relative, "all Inbox items are complete; remove this dated file"),
        )
    return inbox_file, errors, warnings


def _report(
    files: list[InboxFile],
    errors: list[Issue],
    warnings: list[Issue],
    policy: InboxPolicy,
    inbox_root: Path,
) -> InboxReport:
    open_items = sum(len(item.open_items) for item in files)
    if open_items > policy.max_open_items:
        errors.append(
            Issue(
                inbox_root,
                f"open Inbox item limit exceeded: {open_items} > {policy.max_open_items}",
            ),
        )
    overdue_items = sum(
        len(item.open_items) for item in files if item.age_days >= policy.block_after_days
    )
    ages = [item.age_days for item in files if item.open_items]
    return InboxReport(
        files=tuple(files),
        open_items=open_items,
        overdue_items=overdue_items,
        oldest_age_days=max(ages, default=None),
        errors=tuple(sorted(errors)),
        warnings=tuple(sorted(warnings)),
    )
