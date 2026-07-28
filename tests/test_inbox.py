"""Inbox policy boundary tests."""

from datetime import date
from pathlib import Path

from workrepo.inbox import inspect_inbox
from workrepo.policy import InboxPolicy

TODAY = date(2026, 7, 29)
POLICY = InboxPolicy(
    warn_after_days=7,
    block_after_days=30,
    max_open_items=2,
)


def _write_inbox(root: Path, filename: str, body: str) -> None:
    inbox = root / "00-inbox"
    inbox.mkdir(exist_ok=True)
    (inbox / filename).write_text(body, encoding="utf-8")


def test_rejects_arbitrary_inbox_filename(repository: Path) -> None:
    _write_inbox(repository, "a.md", "# Temporary\n")

    report = inspect_inbox(repository, Path("00-inbox"), POLICY, today=TODAY)

    assert len(report.errors) == 1
    assert "top-level YYYY-MM-DD.md" in report.errors[0].message


def test_warns_at_warning_age_and_blocks_at_blocking_age(repository: Path) -> None:
    _write_inbox(repository, "2026-07-22.md", "# 2026-07-22 Inbox\n\n- [ ] Review\n")
    _write_inbox(repository, "2026-06-29.md", "# 2026-06-29 Inbox\n\n- [ ] Escalate\n")

    report = inspect_inbox(repository, Path("00-inbox"), POLICY, today=TODAY)

    assert len(report.warnings) == 1
    assert "7 days old" in report.warnings[0].message
    assert len(report.errors) == 1
    assert "30 days old" in report.errors[0].message
    assert report.overdue_items == 1
    assert report.oldest_age_days == POLICY.block_after_days


def test_warns_when_completed_file_should_be_removed(repository: Path) -> None:
    _write_inbox(repository, "2026-07-29.md", "# 2026-07-29 Inbox\n\n- [x] Filed\n")

    report = inspect_inbox(repository, Path("00-inbox"), POLICY, today=TODAY)

    assert not report.errors
    assert len(report.warnings) == 1
    assert "remove this dated file" in report.warnings[0].message


def test_rejects_future_capture_and_open_item_overflow(repository: Path) -> None:
    _write_inbox(
        repository,
        "2026-07-30.md",
        "# 2026-07-30 Inbox\n\n- [ ] One\n- [ ] Two\n- [ ] Three\n",
    )

    report = inspect_inbox(repository, Path("00-inbox"), POLICY, today=TODAY)

    messages = {issue.message for issue in report.errors}
    assert "Inbox capture date must not be in the future" in messages
    assert "open Inbox item limit exceeded: 3 > 2" in messages
