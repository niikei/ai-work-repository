"""Current-state dashboard generation tests."""

from datetime import date
from pathlib import Path

from workrepo.creation import CreateRequest, capture_inbox, create_document
from workrepo.dashboard import DASHBOARD_PATH, generate_dashboard
from workrepo.repository import check_repository, refresh_repository

DOCUMENT_DATE = date(2026, 7, 29)


def test_empty_dashboard_uses_compact_table_cells(repository: Path) -> None:
    """Generated empty rows agree with the repository's MD060 style."""
    content = generate_dashboard(repository).read_text(encoding="utf-8")

    assert "| _None_ | | | | | | |" in content
    assert "| _None_ | | | | |" in content
    assert "|  |" not in content
    assert "<!--" not in content


def test_dashboard_embeds_available_cockpit_bases(repository: Path) -> None:
    """The unified operational Base renders inline without being mandatory."""
    views = repository / "40-library/40-resources/views"
    views.mkdir(parents=True)
    (views / "cockpit.base").write_text("views: []\n", encoding="utf-8")

    content = generate_dashboard(repository).read_text(encoding="utf-8")

    assert "## Operational cockpit" in content
    assert "![[40-library/40-resources/views/cockpit.base#Attention]]" in content
    assert "markdownlint-disable" not in content


def test_dashboard_places_cockpit_before_markdown_summary(repository: Path) -> None:
    """Obsidian opens on interactive views instead of static fallback tables."""
    views = repository / "40-library/40-resources/views"
    views.mkdir(parents=True)
    (views / "cockpit.base").write_text("views: []\n", encoding="utf-8")

    content = generate_dashboard(repository).read_text(encoding="utf-8")

    assert content.index("## Operational cockpit") < content.index("## Markdown summary")
    assert content.index("## Markdown summary") < content.index("## Inbox")


def test_dashboard_links_to_available_reference_bases(repository: Path) -> None:
    """Less frequent management views remain easy to open."""
    views = repository / "40-library/40-resources/views"
    views.mkdir(parents=True)
    (views / "library.base").write_text("views: []\n", encoding="utf-8")

    content = generate_dashboard(repository).read_text(encoding="utf-8")

    assert "### Reference views" in content
    assert "[Library](40-library/40-resources/views/library.base)" in content


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


def test_refresh_repairs_dashboard_after_canonical_document_is_deleted(
    repository: Path,
) -> None:
    """A stale generated link must not prevent the command that repairs it."""
    project = create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="temporary",
            title="Temporary project",
            document_date=DOCUMENT_DATE,
        ),
    )
    generate_dashboard(repository)
    assert "temporary/index.md" in (repository / DASHBOARD_PATH).read_text(encoding="utf-8")
    project.unlink()

    refresh_repository(repository)

    assert "temporary/index.md" not in (repository / DASHBOARD_PATH).read_text(encoding="utf-8")
    assert check_repository(repository) == []
