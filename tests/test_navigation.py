"""Repository navigation and discovery tests."""

from datetime import date
from pathlib import Path

from workrepo.creation import CreateRequest, create_document
from workrepo.navigation import ContentFilter, generate_navigation, list_content, search_content
from workrepo.validation import require_repository

DOCUMENT_DATE = date(2026, 7, 29)


def _create_area_and_projects(repository: Path) -> None:
    create_document(
        repository,
        CreateRequest(
            document_type="area",
            slug="erp-operations",
            title="ERP Operations",
            document_date=DOCUMENT_DATE,
        ),
    )
    create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="sap-upgrade",
            title="SAP Upgrade",
            related=("area:erp-operations",),
            document_date=DOCUMENT_DATE,
        ),
    )
    create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="unassigned",
            title="Unassigned Project",
            document_date=DOCUMENT_DATE,
        ),
    )


def test_list_filters_projects_by_related_area(repository: Path) -> None:
    """Area membership is a relation, so cross-Area Projects stay discoverable."""
    _create_area_and_projects(repository)
    state = require_repository(repository)

    results = list_content(
        state,
        filters=ContentFilter(
            document_type="project",
            area_id="area:erp-operations",
        ),
    )

    assert [item.title for item in results] == ["SAP Upgrade"]


def test_search_uses_title_metadata_and_body_with_and_semantics(repository: Path) -> None:
    """One shared search covers both structured metadata and human prose."""
    _create_area_and_projects(repository)
    project = repository / "20-projects/sap-upgrade/index.md"
    project.write_text(
        project.read_text(encoding="utf-8").replace(
            "## Outcome",
            "## Outcome\n\nProduction cutover runbook",
        ),
        encoding="utf-8",
    )
    state = require_repository(repository)

    results = search_content(
        state,
        "SAP runbook",
        filters=ContentFilter(document_type="project"),
    )

    assert [item.title for item in results] == ["SAP Upgrade"]
    assert search_content(state, "SAP missing") == []


def test_navigation_groups_projects_without_moving_canonical_files(
    repository: Path,
) -> None:
    """Generated navigation supplies hierarchy while paths remain stable."""
    _create_area_and_projects(repository)

    output = generate_navigation(repository)
    content = output.read_text(encoding="utf-8")

    assert "## Active projects by Area" in content
    assert "### [ERP Operations](30-areas/erp-operations/index.md)" in content
    assert "[SAP Upgrade](20-projects/sap-upgrade/index.md)" in content
    assert "### No Area assigned" in content
    assert "[Unassigned Project](20-projects/unassigned/index.md)" in content
    assert "\n\n\n" not in content
    assert "|  |" not in content


def test_navigation_summarizes_library_without_listing_every_record(
    repository: Path,
) -> None:
    """Library navigation remains compact as type directories grow."""
    for document_type, slug in (
        ("system", "erp"),
        ("system", "m365"),
        ("process", "incident-management"),
        ("guide", "classification"),
    ):
        create_document(
            repository,
            CreateRequest(
                document_type=document_type,
                slug=slug,
                title=slug,
                document_date=DOCUMENT_DATE,
            ),
        )

    content = generate_navigation(repository).read_text(encoding="utf-8")

    assert "## Library" in content
    assert (
        "| Catalog | system | 2 | [40-library/10-catalog/systems](40-library/10-catalog/systems/) |"
    ) in content
    assert (
        "| Playbooks | process | 1 | "
        "[40-library/20-playbooks/processes](40-library/20-playbooks/processes/) |"
    ) in content
    assert (
        "| Knowledge | guide | 1 | "
        "[40-library/30-knowledge/guides](40-library/30-knowledge/guides/) |"
    ) in content
    assert "system:erp" not in content
