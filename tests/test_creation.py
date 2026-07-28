"""Document and Inbox creation tests."""

import json
from datetime import date
from pathlib import Path

import pytest

from workrepo.creation import (
    ArtifactRequest,
    CreateRequest,
    capture_inbox,
    create_artifact,
    create_document,
)
from workrepo.repository import build_index, check_repository

DOCUMENT_DATE = date(2026, 7, 29)


def test_create_project_from_template(repository: Path) -> None:
    """Creation derives a stable ID and schema-defined destination."""
    path = create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="erp-upgrade",
            title="ERP更改",
            document_date=DOCUMENT_DATE,
        ),
    )

    assert path.relative_to(repository) == Path("20-projects/erp-upgrade/index.md")
    content = path.read_text(encoding="utf-8")
    assert "id: project:erp-upgrade" in content
    assert "created: 2026-07-29" in content
    assert "# ERP更改" in content
    assert check_repository(repository) == []


def test_create_log_with_existing_relationship(repository: Path) -> None:
    """Relationships are checked before a new document is written."""
    create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="erp-upgrade",
            title="ERP更改",
            document_date=DOCUMENT_DATE,
        ),
    )

    path = create_document(
        repository,
        CreateRequest(
            document_type="log",
            slug="kickoff",
            title="Kickoff",
            related=("project:erp-upgrade",),
            document_date=DOCUMENT_DATE,
        ),
    )

    assert path.relative_to(repository) == Path(
        "10-log/2026/07/2026-07-27-week/2026-07-29-kickoff.md",
    )
    assert "  - project:erp-upgrade" in path.read_text(encoding="utf-8")
    assert check_repository(repository) == []

    payload = json.loads(build_index(repository).read_text(encoding="utf-8"))
    log_entry = next(item for item in payload["documents"] if item["type"] == "log")
    assert log_entry["derived"] == {
        "backlinks": [],
        "iso_week": "2026-W31",
        "week_start": "2026-07-27",
    }


def test_create_rejects_unknown_relationship(repository: Path) -> None:
    """A typo in a relationship cannot create an invalid document."""
    request = CreateRequest(
        document_type="project",
        slug="example",
        title="Example",
        related=("area:missing",),
        document_date=DOCUMENT_DATE,
    )

    with pytest.raises(ValueError, match="related IDs do not exist"):
        create_document(repository, request)

    assert not (repository / "20-projects/example/index.md").exists()


def test_log_week_stays_together_across_year_boundary(repository: Path) -> None:
    """The directory uses the week start year instead of splitting one week."""
    path = create_document(
        repository,
        CreateRequest(
            document_type="log",
            slug="new-year-incident",
            title="New year incident",
            document_date=date(2027, 1, 1),
        ),
    )

    assert path.relative_to(repository) == Path(
        "10-log/2026/12/2026-12-28-week/2027-01-01-new-year-incident.md",
    )


def test_check_rejects_log_in_month_directory(repository: Path) -> None:
    """Manual files in the old monthly layout receive a precise correction."""
    path = create_document(
        repository,
        CreateRequest(
            document_type="log",
            slug="meeting",
            title="Meeting",
            document_date=DOCUMENT_DATE,
        ),
    )
    incorrect_path = repository / "10-log/2026/07/2026-07-29-meeting.md"
    incorrect_path.parent.mkdir(parents=True, exist_ok=True)
    path.rename(incorrect_path)

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == [
        "log for 2026-07-29 must be located under 10-log/2026/07/2026-07-27-week/",
    ]


def test_capture_appends_normalized_inbox_items(repository: Path) -> None:
    """Repeated capture stays fast and uses one dated Inbox file."""
    path = capture_inbox(repository, "First   thought", capture_date=DOCUMENT_DATE)
    capture_inbox(repository, "Second\nthought", capture_date=DOCUMENT_DATE)

    assert path.relative_to(repository) == Path("00-inbox/2026-07-29.md")
    assert path.read_text(encoding="utf-8") == (
        "# 2026-07-29 Inbox\n\n- [ ] First thought\n- [ ] Second thought\n"
    )


def test_create_typed_artifact_under_its_parent(repository: Path) -> None:
    """Durable output receives an ID and an explicit owning relationship."""
    create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="erp-upgrade",
            title="ERP更改",
            document_date=DOCUMENT_DATE,
        ),
    )

    path = create_artifact(
        repository,
        ArtifactRequest(
            slug="2026-07-27-weekly-report",
            title="ERP更改 2026-07-27週次報告",
            parent_id="project:erp-upgrade",
            kind="weekly-report",
            document_date=DOCUMENT_DATE,
        ),
    )

    assert path.relative_to(repository) == Path(
        "20-projects/erp-upgrade/reports/2026-07-27-weekly-report.md",
    )
    content = path.read_text(encoding="utf-8")
    assert "id: artifact:project:erp-upgrade:2026-07-27-weekly-report" in content
    assert "  - project:erp-upgrade" in content
    assert check_repository(repository) == []


@pytest.mark.parametrize("slug", ["con", "COM1"])
def test_create_rejects_windows_reserved_slug(repository: Path, slug: str) -> None:
    """Generated paths remain portable to Windows workstations."""
    with pytest.raises(ValueError, match=r"reserved on Windows|lowercase"):
        create_document(
            repository,
            CreateRequest(
                document_type="project",
                slug=slug,
                title="Reserved",
                document_date=DOCUMENT_DATE,
            ),
        )


def test_check_rejects_conflated_area_status_and_health(repository: Path) -> None:
    """Lifecycle and operational health use separate controlled vocabularies."""
    path = create_document(
        repository,
        CreateRequest(
            document_type="area",
            slug="erp-operations",
            title="ERP運用",
            document_date=DOCUMENT_DATE,
        ),
    )
    content = path.read_text(encoding="utf-8")
    path.write_text(
        content.replace("status: active", "status: attention").replace(
            "health: unknown",
            "health: attention",
        ),
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert "invalid health 'attention'; expected one of: amber, green, red, unknown" in messages
    assert "invalid status 'attention'; expected one of: active, paused, retired" in messages


def test_create_rejects_case_only_directory_collision(repository: Path) -> None:
    """A path that works on Linux cannot collide after checkout on Windows."""
    existing = repository / "20-projects/Example"
    existing.mkdir(parents=True)

    with pytest.raises(FileExistsError, match="conflicts by letter case"):
        create_document(
            repository,
            CreateRequest(
                document_type="project",
                slug="example",
                title="Example",
                document_date=DOCUMENT_DATE,
            ),
        )
