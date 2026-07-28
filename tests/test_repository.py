"""Repository validation and indexing tests."""

import json
import shutil
from pathlib import Path

import pytest

from workrepo.repository import (
    INDEX_OUTPUT,
    build_index,
    check_repository,
    sync_related_links,
)
from workrepo.schema import SCHEMA_PATH

PROJECT_ROOT = Path(__file__).parents[1]
DUPLICATE_DOCUMENT_COUNT = 2


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a minimal work repository with the production schema."""
    schema_target = tmp_path / SCHEMA_PATH
    schema_target.parent.mkdir(parents=True)
    shutil.copy(PROJECT_ROOT / SCHEMA_PATH, schema_target)
    return tmp_path


def write_document(
    root: Path,
    relative_path: str,
    *,
    identifier: str = "project:example",
    related: str = "[]",
    title: str = "Example",
) -> Path:
    """Write a valid Project document, with selected fields configurable."""
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "---",
                "type: project",
                f"id: {identifier}",
                "status: active",
                "created: 2026-07-28",
                "updated: 2026-07-28",
                f"related: {related}",
                "---",
                "",
                f"# {title}",
                "",
            ),
        ),
        encoding="utf-8",
    )
    return path


def test_template_repository_is_valid() -> None:
    """The committed template must satisfy its own rules."""
    assert check_repository(PROJECT_ROOT) == []


def test_build_index_contains_canonical_title(repository: Path) -> None:
    """The index exposes the H1 and normalized date strings."""
    write_document(repository, "projects/example/index.md")

    output = build_index(repository)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert output == repository / INDEX_OUTPUT
    assert payload["documents"][0]["title"] == "Example"
    assert payload["documents"][0]["metadata"]["created"] == "2026-07-28"


def test_check_reports_duplicate_and_missing_related_ids(repository: Path) -> None:
    """Cross-document identifiers and relationships are checked repository-wide."""
    write_document(
        repository,
        "projects/first/index.md",
        related="[area:missing]",
    )
    write_document(repository, "projects/second/index.md")

    messages = [issue.message for issue in check_repository(repository)]

    assert messages.count("duplicate id: project:example") == DUPLICATE_DOCUMENT_COUNT
    assert "related id does not exist: area:missing" in messages


def test_check_rejects_multiple_h1_headings(repository: Path) -> None:
    """A document cannot have competing canonical titles."""
    path = write_document(repository, "projects/example/index.md")
    path.write_text(f"{path.read_text(encoding='utf-8')}# Another title\n", encoding="utf-8")

    issues = check_repository(repository)

    assert len(issues) == 1
    assert issues[0].message == "expected exactly one H1 heading, found 2"


def test_sync_related_links_is_idempotent(repository: Path) -> None:
    """Stable IDs generate portable Markdown links without metadata duplication."""
    source = write_document(
        repository,
        "projects/source/index.md",
        identifier="project:source",
        related="[project:target]",
        title="Source",
    )
    write_document(
        repository,
        "projects/target/index.md",
        identifier="project:target",
        title="Target",
    )

    assert sync_related_links(repository) == 1
    assert sync_related_links(repository) == 0

    source_text = source.read_text(encoding="utf-8")
    assert "- [Target](../target/index.md) (`project:target`)" in source_text
    assert "related: [project:target]" in source_text


def test_sync_related_links_rejects_malformed_markers(repository: Path) -> None:
    """Generated sections fail safely instead of overwriting ambiguous content."""
    source = write_document(
        repository,
        "projects/source/index.md",
        identifier="project:source",
        related="[project:target]",
    )
    write_document(
        repository,
        "projects/target/index.md",
        identifier="project:target",
    )
    source.write_text(
        f"{source.read_text(encoding='utf-8')}<!-- workrepo:related:start -->\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="markers are malformed"):
        sync_related_links(repository)
