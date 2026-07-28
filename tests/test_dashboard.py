"""Current-state dashboard generation tests."""

from datetime import date
from pathlib import Path

from workrepo.creation import CreateRequest, capture_inbox, create_document
from workrepo.dashboard import DASHBOARD_PATH, generate_dashboard
from workrepo.repository import check_repository

DOCUMENT_DATE = date(2026, 7, 29)


def test_dashboard_summarizes_inbox_project_and_area(repository: Path) -> None:
    """The generated overview links to canonical state without copying it."""
    create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="erp-upgrade",
            title="ERP更改",
            document_date=DOCUMENT_DATE,
        ),
    )
    create_document(
        repository,
        CreateRequest(
            document_type="area",
            slug="erp-operations",
            title="ERP運用",
            document_date=DOCUMENT_DATE,
        ),
    )
    capture_inbox(repository, "Review interface error", capture_date=DOCUMENT_DATE)

    output = generate_dashboard(repository)
    content = output.read_text(encoding="utf-8")

    assert output == repository / DASHBOARD_PATH
    assert "Open items: **1**" in content
    assert "[ERP更改](20-projects/erp-upgrade/index.md)" in content
    assert "[ERP運用](30-areas/erp-operations/index.md)" in content
    assert check_repository(repository) == []


def test_dashboard_hides_retired_area(repository: Path) -> None:
    """Historical responsibilities stay searchable without crowding the dashboard."""
    path = create_document(
        repository,
        CreateRequest(
            document_type="area",
            slug="legacy-operations",
            title="旧運用",
            document_date=DOCUMENT_DATE,
        ),
    )
    path.write_text(
        path.read_text(encoding="utf-8").replace("status: active", "status: retired"),
        encoding="utf-8",
    )

    content = generate_dashboard(repository).read_text(encoding="utf-8")

    assert "旧運用" not in content
