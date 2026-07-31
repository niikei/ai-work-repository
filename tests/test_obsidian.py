"""Obsidian URI integration tests."""

from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from workrepo.creation import CreateRequest, create_document
from workrepo.obsidian import document_uri, open_document


def test_document_uri_resolves_stable_id(repository: Path) -> None:
    """URI paths remain correct even when filenames are not known by the caller."""
    path = create_document(
        repository,
        CreateRequest(
            document_type="project",
            slug="erp-upgrade",
            title="ERP Upgrade",
            document_date=date(2026, 7, 29),
        ),
    )

    parsed = urlsplit(document_uri(repository, "project:erp-upgrade"))

    assert parsed.scheme == "obsidian"
    assert parsed.netloc == "open"
    assert unquote(parsed.query.removeprefix("path=")) == str(path.resolve())


def test_open_document_dispatches_uri(repository: Path) -> None:
    """Opening is injectable so tests do not launch the desktop app."""
    create_document(
        repository,
        CreateRequest(
            document_type="area",
            slug="operations",
            title="Operations",
            document_date=date(2026, 7, 29),
        ),
    )
    opened: list[str] = []

    uri = open_document(
        repository,
        "area:operations",
        opener=lambda value: not opened.append(value),
    )

    assert opened == [uri]


def test_document_uri_rejects_unknown_id(repository: Path) -> None:
    with pytest.raises(ValueError, match="document does not exist: project:missing"):
        document_uri(repository, "project:missing")
