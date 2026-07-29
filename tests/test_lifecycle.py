"""Durable-record archive and restore lifecycle tests."""

import json
from datetime import date
from pathlib import Path

import pytest

import workrepo.lifecycle
from workrepo.creation import ArtifactRequest, CreateRequest, create_artifact, create_document
from workrepo.indexing import INDEX_OUTPUT
from workrepo.lifecycle import archive_document, restore_document
from workrepo.navigation import ContentFilter, list_content, search_content
from workrepo.repository import refresh_repository
from workrepo.validation import check_repository, require_repository

DOCUMENT_DATE = date(2026, 7, 29)


def _completed_project(repository: Path) -> Path:
    create_document(
        repository,
        CreateRequest(
            document_type="area",
            slug="erp-operations",
            title="ERP Operations",
            document_date=DOCUMENT_DATE,
        ),
    )
    project = create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="finished-project",
            title="Finished Project",
            related=("area:erp-operations",),
            document_date=DOCUMENT_DATE,
        ),
    )
    project.write_text(
        project.read_text(encoding="utf-8")
        .replace("status: planned", "status: completed")
        .replace(
            "## Important documents",
            (
                "## Important documents\n\n"
                "[Scope](analysis/scope.md)\n\n"
                "[Area](../../30-areas/erp-operations/index.md)"
            ),
        ),
        encoding="utf-8",
    )
    create_artifact(
        repository,
        ArtifactRequest(
            slug="scope",
            title="Scope",
            parent_id="project:finished-project",
            kind="analysis",
            document_date=DOCUMENT_DATE,
        ),
    )
    create_document(
        repository,
        CreateRequest(
            document_type="log",
            slug="completion",
            title="Completion",
            related=("project:finished-project",),
            document_date=DOCUMENT_DATE,
        ),
    )
    notes = repository / "notes.md"
    notes.write_text(
        "# Notes\n\n[Finished Project](20-projects/finished-project/index.md)\n",
        encoding="utf-8",
    )
    refresh_repository(repository)
    return project


def test_archive_and_restore_project_preserve_links_and_artifacts(
    repository: Path,
) -> None:
    """A whole Project moves atomically while IDs and local links stay valid."""
    project = _completed_project(repository)

    archived = archive_document(
        repository,
        "project:finished-project",
        operation_date=DOCUMENT_DATE,
    )

    archived_project = repository / "80-archive/2026/projects/finished-project/index.md"
    archived_artifact = repository / "80-archive/2026/projects/finished-project/analysis/scope.md"
    assert archived.source == Path("20-projects/finished-project/index.md")
    assert archived.destination == Path(
        "80-archive/2026/projects/finished-project/index.md",
    )
    assert not project.exists()
    assert archived_project.is_file()
    assert archived_artifact.is_file()
    assert "[Scope](analysis/scope.md)" in archived_project.read_text(encoding="utf-8")
    assert "[Area](../../../../30-areas/erp-operations/index.md)" in (
        archived_project.read_text(encoding="utf-8")
    )
    assert "[Finished Project](80-archive/2026/projects/finished-project/index.md)" in (
        repository / "notes.md"
    ).read_text(encoding="utf-8")
    assert check_repository(repository) == []

    state = require_repository(repository)
    assert (
        list_content(
            state,
            filters=ContentFilter(document_type="project"),
        )
        == []
    )
    assert [
        item.title
        for item in list_content(
            state,
            filters=ContentFilter(
                document_type="project",
                archive_scope="only",
            ),
        )
    ] == ["Finished Project"]
    assert [
        item.title
        for item in search_content(
            state,
            "Finished Project",
            filters=ContentFilter(archive_scope="include"),
        )
        if item.metadata.get("type") == "project"
    ] == ["Finished Project"]

    payload = json.loads(
        (repository / INDEX_OUTPUT).read_text(encoding="utf-8"),
    )
    entries = {item["id"]: item for item in payload["documents"] if item["id"] is not None}
    assert entries["project:finished-project"]["derived"]["archived"] is True
    assert entries["artifact:project:finished-project:scope"]["derived"]["archived"] is True

    restored = restore_document(repository, "project:finished-project")

    assert restored.destination == Path("20-projects/finished-project/index.md")
    assert project.is_file()
    assert "[Area](../../30-areas/erp-operations/index.md)" in project.read_text(
        encoding="utf-8",
    )
    assert "[Finished Project](20-projects/finished-project/index.md)" in (
        repository / "notes.md"
    ).read_text(encoding="utf-8")
    assert not (repository / "80-archive/2026").exists()
    assert check_repository(repository) == []


def test_archive_rejects_active_project(repository: Path) -> None:
    """Current work cannot disappear from the active Project directory."""
    project = create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="active-project",
            title="Active Project",
            document_date=DOCUMENT_DATE,
        ),
    )

    with pytest.raises(ValueError, match=r"cannot archive.*status 'planned'"):
        archive_document(
            repository,
            "project:active-project",
            operation_date=DOCUMENT_DATE,
        )

    assert project.is_file()
    assert not (repository / "80-archive/2026/projects/active-project").exists()


def test_archive_rolls_back_move_and_generated_files_on_failure(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An error after movement restores the exact pre-operation repository."""
    project = _completed_project(repository)
    notes = repository / "notes.md"
    before_project = project.read_bytes()
    before_notes = notes.read_bytes()
    before_index = (repository / INDEX_OUTPUT).read_bytes()

    def fail_refresh(root: Path) -> object:
        raise RuntimeError(root)

    monkeypatch.setattr(workrepo.lifecycle, "refresh_repository", fail_refresh)

    with pytest.raises(RuntimeError):
        archive_document(
            repository,
            "project:finished-project",
            operation_date=DOCUMENT_DATE,
        )

    assert project.read_bytes() == before_project
    assert notes.read_bytes() == before_notes
    assert (repository / INDEX_OUTPUT).read_bytes() == before_index
    assert not (repository / "80-archive/2026/projects/finished-project").exists()


@pytest.mark.parametrize(
    ("document_type", "archive_directory"),
    [
        ("system", "library/catalog/systems"),
        ("role", "library/catalog/roles"),
        ("organization", "library/catalog/organizations"),
        ("service", "library/catalog/services"),
        ("process", "library/playbooks/processes"),
        ("procedure", "library/playbooks/procedures"),
        ("control", "library/playbooks/controls"),
        ("standard", "library/playbooks/standards"),
        ("concept", "library/knowledge/concepts"),
        ("guide", "library/knowledge/guides"),
        ("glossary", "library/knowledge/glossary"),
        ("resource", "library/resources"),
    ],
)
def test_archive_and_restore_retired_library_entity(
    repository: Path,
    document_type: str,
    archive_directory: str,
) -> None:
    """Retired reusable knowledge uses its type-specific archive directory."""
    document = create_document(
        repository,
        CreateRequest(
            document_type=document_type,
            slug="legacy-record",
            title="Legacy record",
            document_date=DOCUMENT_DATE,
        ),
    )
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "status: active",
            "status: retired",
        ),
        encoding="utf-8",
    )

    archive_document(
        repository,
        f"{document_type}:legacy-record",
        operation_date=DOCUMENT_DATE,
    )

    archived = repository / "80-archive/2026" / archive_directory / "legacy-record.md"
    assert archived.is_file()
    assert not document.exists()
    assert check_repository(repository) == []

    restore_document(repository, f"{document_type}:legacy-record")

    assert document.is_file()
    assert not archived.exists()
    assert not (repository / "80-archive/2026").exists()
    assert check_repository(repository) == []


def test_archive_rejects_non_lifecycle_document(repository: Path) -> None:
    """Chronological Log records remain in their year-month-week hierarchy."""
    create_document(
        repository,
        CreateRequest(
            document_type="log",
            slug="event",
            title="Event",
            document_date=DOCUMENT_DATE,
        ),
    )

    with pytest.raises(ValueError, match="document type cannot be archived"):
        archive_document(
            repository,
            "log:2026-07-29:event",
            operation_date=DOCUMENT_DATE,
        )


def test_check_rejects_manually_misplaced_archive_document(
    repository: Path,
) -> None:
    """Manual moves cannot silently remove managed records from discovery."""
    misplaced = repository / "80-archive/2026/wrong/example/index.md"
    misplaced.parent.mkdir(parents=True)
    misplaced.write_text(
        """---
type: project
id: project:example
status: completed
health: green
created: 2026-07-29
updated: 2026-07-29
related: []
---

# Example
""",
        encoding="utf-8",
    )

    assert [str(issue) for issue in check_repository(repository)] == [
        (
            "80-archive/2026/wrong/example/index.md: "
            "document is not in a schema-defined archive location"
        ),
    ]
