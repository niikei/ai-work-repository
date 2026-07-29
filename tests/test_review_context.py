"""Tests for bounded period-review evidence selection."""

import json
from datetime import date
from pathlib import Path

import pytest

from workrepo.cli import main
from workrepo.creation import CreateRequest, capture_inbox, create_document
from workrepo.review_context import build_review_context, review_context_payload
from workrepo.validation import require_repository

PERIOD_START = date(2026, 7, 27)
PERIOD_END = date(2026, 8, 2)
OLD_DATE = date(2026, 7, 1)
REVIEW_LIMIT = 2


def _create(
    repository: Path,
    document_type: str,
    slug: str,
    *,
    document_date: date,
    related: tuple[str, ...] = (),
) -> Path:
    return create_document(
        repository,
        CreateRequest(
            document_type=document_type,
            slug=slug,
            title=slug.replace("-", " ").title(),
            related=related,
            document_date=document_date,
        ),
    )


def _replace(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    assert old in source
    path.write_text(source.replace(old, new), encoding="utf-8")


def test_review_context_selects_period_evidence_and_attention(
    repository: Path,
) -> None:
    """Logs drive relations while attention records remain visible."""
    related = _create(
        repository,
        "project",
        "related-project",
        document_date=OLD_DATE,
    )
    recent = _create(
        repository,
        "project",
        "recent-project",
        document_date=date(2026, 7, 29),
    )
    blocked = _create(
        repository,
        "project",
        "blocked-project",
        document_date=OLD_DATE,
    )
    amber = _create(
        repository,
        "project",
        "amber-project",
        document_date=OLD_DATE,
    )
    inactive_amber = _create(
        repository,
        "project",
        "inactive-amber",
        document_date=OLD_DATE,
    )
    _create(
        repository,
        "project",
        "unrelated-project",
        document_date=OLD_DATE,
    )
    _replace(blocked, "status: planned", "status: blocked")
    _replace(amber, "health: unknown", "health: amber")
    _replace(inactive_amber, "status: planned", "status: completed")
    _replace(inactive_amber, "health: unknown", "health: amber")
    due_area = _create(
        repository,
        "area",
        "due-area",
        document_date=date(2026, 7, 20),
    )
    _replace(due_area, "review_cycle: monthly", "review_cycle: weekly")
    _create(
        repository,
        "log",
        "period-event",
        document_date=date(2026, 7, 29),
        related=("project:related-project",),
    )
    _create(
        repository,
        "log",
        "old-event",
        document_date=date(2026, 7, 10),
    )
    capture_inbox(repository, "Older unresolved item", capture_date=date(2026, 7, 26))

    context = build_review_context(
        require_repository(repository),
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    assert [item.path.name for item in context.inbox_files] == ["2026-07-26.md"]
    assert [item.metadata["id"] for item in context.logs] == ["log:2026-07-29:period-event"]
    candidates = {
        candidate.document.metadata["id"]: candidate.reasons
        for candidate in context.candidates
    }
    assert candidates["project:related-project"] == ("related-to-period-log",)
    assert candidates["project:recent-project"] == ("updated-in-period",)
    assert candidates["project:blocked-project"] == ("blocked",)
    assert candidates["project:amber-project"] == ("health:amber",)
    assert candidates["area:due-area"] == ("review-due-in-period",)
    assert "project:unrelated-project" not in candidates
    assert "project:inactive-amber" not in candidates
    assert recent.is_file()
    assert related.is_file()


def test_review_context_limits_each_section_and_reports_truncation(
    repository: Path,
) -> None:
    for offset in range(3):
        _create(
            repository,
            "log",
            f"event-{offset}",
            document_date=date(2026, 7, 27 + offset),
        )
        capture_inbox(
            repository,
            f"Open item {offset}",
            capture_date=date(2026, 7, 27 + offset),
        )
        project = _create(
            repository,
            "project",
            f"blocked-{offset}",
            document_date=OLD_DATE,
        )
        _replace(project, "status: planned", "status: blocked")

    context = build_review_context(
        require_repository(repository),
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        limit=REVIEW_LIMIT,
    )

    assert len(context.inbox_files) == REVIEW_LIMIT
    assert len(context.logs) == REVIEW_LIMIT
    assert len(context.candidates) == REVIEW_LIMIT
    assert context.inbox_truncated
    assert context.logs_truncated
    assert context.candidates_truncated
    assert [item.metadata["id"] for item in context.logs] == [
        "log:2026-07-28:event-1",
        "log:2026-07-29:event-2",
    ]


def test_review_context_rejects_reversed_period(repository: Path) -> None:
    """An invalid range fails before selecting repository records."""
    with pytest.raises(ValueError, match="start must not be later"):
        build_review_context(
            require_repository(repository),
            period_start=PERIOD_END,
            period_end=PERIOD_START,
        )


def test_review_context_excludes_inbox_captured_after_period(repository: Path) -> None:
    """Historical reviews include older backlog but not later captures."""
    capture_inbox(repository, "Older backlog", capture_date=date(2026, 7, 19))
    capture_inbox(repository, "Later capture", capture_date=date(2026, 7, 26))

    context = build_review_context(
        require_repository(repository),
        period_start=date(2026, 7, 20),
        period_end=date(2026, 7, 25),
    )

    assert [item.path.name for item in context.inbox_files] == ["2026-07-19.md"]


def test_review_context_payload_is_stable_and_json_compatible(repository: Path) -> None:
    """Adapters can reuse one typed application result."""
    _create(
        repository,
        "log",
        "decision",
        document_date=date(2026, 7, 30),
    )
    context = build_review_context(
        require_repository(repository),
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    payload = review_context_payload(context)

    assert payload["version"] == 1
    assert json.loads(json.dumps(payload))["period"] == {
        "from": "2026-07-27",
        "to": "2026-08-02",
    }
    assert payload["truncated"] == {
        "inbox": False,
        "logs": False,
        "candidates": False,
    }


def test_cli_review_context_supports_human_and_json_output(
    repository: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _create(
        repository,
        "log",
        "weekly-event",
        document_date=date(2026, 7, 30),
    )
    arguments = (
        "--root",
        str(repository),
        "review-context",
        "--from",
        "2026-07-27",
        "--to",
        "2026-08-02",
    )

    assert main(arguments) == 0
    human_output = capsys.readouterr().out
    assert "Review period: 2026-07-27 to 2026-08-02" in human_output
    assert "10-log/2026/07/2026-07-27-week/2026-07-30-weekly-event.md" in human_output

    assert main((*arguments, "--json")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["period"]["from"] == "2026-07-27"
    assert payload["logs"][0]["id"] == "log:2026-07-30:weekly-event"
