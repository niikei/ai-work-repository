"""Repository validation and indexing tests."""

import json
from datetime import date
from pathlib import Path

import pytest

from workrepo.creation import CreateRequest, create_document
from workrepo.gitops import check_worktree
from workrepo.repository import (
    INDEX_OUTPUT,
    build_index,
    check_repository,
    sync_related_links,
)

PROJECT_ROOT = Path(__file__).parents[1]
DUPLICATE_DOCUMENT_COUNT = 2
INDEX_VERSION = 5
ALLOWED_ROOT_MARKDOWN = frozenset(
    {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "DASHBOARD.md",
        "NAVIGATION.md",
        "README.md",
        "SECURITY.md",
    },
)


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
                "health: unknown",
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


def test_root_markdown_is_limited_to_repository_entry_points() -> None:
    """Guides and reports belong under docs instead of accumulating at the root."""
    root_markdown = {path.name for path in PROJECT_ROOT.glob("*.md")}
    assert root_markdown <= ALLOWED_ROOT_MARKDOWN


def test_check_rejects_unrecognized_root_markdown(repository: Path) -> None:
    """Daily validation prevents miscellaneous root documents from accumulating."""
    (repository / "a.md").write_text("# Temporary note\n", encoding="utf-8")

    messages = [str(issue) for issue in check_repository(repository)]

    assert messages == ["a.md: root Markdown must be moved under docs/"]


def test_build_index_contains_canonical_title(repository: Path) -> None:
    """The index exposes the H1 and normalized date strings."""
    write_document(repository, "20-projects/example/index.md")

    output = build_index(repository)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert output == repository / INDEX_OUTPUT
    assert payload["version"] == INDEX_VERSION
    assert payload["documents"][0]["kind"] == "entity"
    assert payload["documents"][0]["title"] == "Example"
    assert payload["documents"][0]["metadata"]["created"] == "2026-07-28"
    assert payload["documents"][0]["derived"]["archived"] is False


@pytest.mark.parametrize(
    ("relative_path", "document_type", "root"),
    [
        ("20-projects/group/example/index.md", "project", "20-projects"),
        ("30-areas/group/example/index.md", "area", "30-areas"),
    ],
)
def test_check_rejects_nested_entity_indexes(
    repository: Path,
    relative_path: str,
    document_type: str,
    root: str,
) -> None:
    """Physical grouping cannot become an ambiguous ownership hierarchy."""
    nested = repository / relative_path
    nested.parent.mkdir(parents=True)
    nested.write_text("# Nested entity\n", encoding="utf-8")

    messages = [str(issue) for issue in check_repository(repository)]

    assert messages == [
        f"{relative_path}: {document_type} index must be located at {root}/<slug>/index.md",
    ]


def test_deep_project_markdown_is_indexed_as_an_artifact(repository: Path) -> None:
    """A Project may freely organize its supporting content below its root."""
    write_document(repository, "20-projects/example/index.md")
    note = repository / "20-projects/example/analysis/architecture/options.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Architecture options\n", encoding="utf-8")

    assert check_repository(repository) == []
    payload = json.loads(build_index(repository).read_text(encoding="utf-8"))
    artifact = next(item for item in payload["documents"] if item["kind"] == "artifact")
    assert artifact["path"] == "20-projects/example/analysis/architecture/options.md"
    assert artifact["derived"]["parent_id"] == "project:example"


def test_check_rejects_markdown_beside_entity_index(repository: Path) -> None:
    """An Entity directory has one obvious Markdown entry point."""
    write_document(repository, "20-projects/example/index.md")
    memo = repository / "20-projects/example/memo.md"
    memo.write_text("# Memo\n", encoding="utf-8")

    messages = [str(issue) for issue in check_repository(repository)]

    assert messages == [
        "20-projects/example/memo.md: Markdown beside index.md must be moved into a subdirectory",
    ]


def test_check_rejects_nested_library_entity(repository: Path) -> None:
    """Library hierarchy stops at function, type, and one document."""
    system = create_document(
        repository,
        CreateRequest(
            document_type="system",
            slug="example",
            title="Example",
            document_date=date(2026, 7, 29),
        ),
    )
    nested = system.parent / "sap" / system.name
    nested.parent.mkdir()
    system.rename(nested)

    messages = [str(issue) for issue in check_repository(repository)]

    assert messages == [
        (
            f"{nested.relative_to(repository)}: "
            "must be located directly under 40-library/10-catalog/systems/"
        ),
    ]


def test_check_reports_duplicate_and_missing_related_ids(repository: Path) -> None:
    """Cross-document identifiers and relationships are checked repository-wide."""
    write_document(
        repository,
        "20-projects/first/index.md",
        related="[area:missing]",
    )
    write_document(repository, "20-projects/second/index.md")

    messages = [issue.message for issue in check_repository(repository)]

    assert messages.count("duplicate id: project:example") == DUPLICATE_DOCUMENT_COUNT
    assert "related id does not exist: area:missing" in messages


def test_check_rejects_multiple_h1_headings(repository: Path) -> None:
    """A document cannot have competing canonical titles."""
    path = write_document(repository, "20-projects/example/index.md")
    path.write_text(f"{path.read_text(encoding='utf-8')}# Another title\n", encoding="utf-8")

    issues = check_repository(repository)

    assert len(issues) == 1
    assert issues[0].message == "expected exactly one H1 heading, found 2"


def test_sync_related_links_is_idempotent(repository: Path) -> None:
    """Stable IDs generate portable Markdown links without metadata duplication."""
    source = write_document(
        repository,
        "20-projects/source/index.md",
        identifier="project:source",
        related="[project:target]",
        title="Source",
    )
    write_document(
        repository,
        "20-projects/target/index.md",
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
        "20-projects/source/index.md",
        identifier="project:source",
        related="[project:target]",
    )
    write_document(
        repository,
        "20-projects/target/index.md",
        identifier="project:target",
    )
    source.write_text(
        f"{source.read_text(encoding='utf-8')}<!-- workrepo:related:start -->\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="markers are malformed"):
        sync_related_links(repository)


def test_check_rejects_duplicate_generated_blocks(repository: Path) -> None:
    """Multiple generated sections cannot be ambiguously rewritten."""
    source = write_document(repository, "20-projects/source/index.md")
    block = (
        "\n## Related documents\n\n"
        "<!-- workrepo:related:start -->\n"
        "- stale\n"
        "<!-- workrepo:related:end -->\n"
    )
    source.write_text(f"{source.read_text(encoding='utf-8')}{block}{block}", encoding="utf-8")

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == [
        "20-projects/source/index.md: generated related document markers are malformed",
    ]


def test_sync_repairs_stale_generated_link(repository: Path) -> None:
    """Canonical IDs can repair generated paths after a target is moved."""
    source = write_document(
        repository,
        "20-projects/source/index.md",
        identifier="project:source",
        related="[project:target]",
    )
    target = write_document(
        repository,
        "20-projects/target/index.md",
        identifier="project:target",
        title="Target",
    )
    sync_related_links(repository)
    moved = repository / "20-projects/renamed/index.md"
    moved.parent.mkdir()
    target.rename(moved)

    assert sync_related_links(repository) == 1
    assert "[Target](../renamed/index.md)" in source.read_text(encoding="utf-8")


def test_build_index_includes_project_artifact(repository: Path) -> None:
    """Project Markdown artifacts are discoverable without entity frontmatter."""
    write_document(repository, "20-projects/example/index.md")
    report = repository / "20-projects/example/reports/weekly.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Weekly report\n\nCurrent progress.\n", encoding="utf-8")

    output = build_index(repository)
    payload = json.loads(output.read_text(encoding="utf-8"))
    artifact = next(item for item in payload["documents"] if item["kind"] == "artifact")

    assert artifact["id"] is None
    assert artifact["title"] == "Weekly report"
    assert artifact["path"] == "20-projects/example/reports/weekly.md"
    assert artifact["derived"]["parent_id"] == "project:example"


def test_typed_artifact_metadata_is_validated_and_indexed(repository: Path) -> None:
    """Artifact frontmatter is canonical data and is never silently discarded."""
    write_document(repository, "20-projects/example/index.md")
    report = repository / "20-projects/example/reports/weekly.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        """---
type: artifact
id: artifact:project:example:weekly
kind: weekly-report
status: final
created: 2026-07-28
updated: 2026-07-28
related: [project:example]
---

# Weekly report
""",
        encoding="utf-8",
    )

    payload = json.loads(build_index(repository).read_text(encoding="utf-8"))
    artifact = next(item for item in payload["documents"] if item["kind"] == "artifact")
    project = next(item for item in payload["documents"] if item["kind"] == "entity")

    assert artifact["id"] == "artifact:project:example:weekly"
    assert artifact["metadata"]["kind"] == "weekly-report"
    assert project["derived"]["backlinks"] == ["artifact:project:example:weekly"]


def test_artifact_frontmatter_cannot_masquerade_as_an_entity(repository: Path) -> None:
    """Any frontmatter below a Project must follow the artifact contract."""
    write_document(repository, "20-projects/example/index.md")
    report = repository / "20-projects/example/reports/report.md"
    report.parent.mkdir()
    report.write_text(
        "---\ntype: report\n---\n\n# Report\n",
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == ["frontmatter in an artifact must declare type: artifact"]


def test_artifact_frontmatter_after_blank_line_is_not_ignored(repository: Path) -> None:
    """Misplaced YAML produces a correction instead of becoming lightweight data."""
    write_document(repository, "20-projects/example/index.md")
    report = repository / "20-projects/example/reports/report.md"
    report.parent.mkdir()
    report.write_text(
        "\n---\ntype: artifact\n---\n\n# Report\n",
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == ["YAML frontmatter must start on the first line"]


def test_schema_version_is_enforced(repository: Path) -> None:
    """An incompatible schema cannot be interpreted with silent defaults."""
    schema_path = repository / ".workspace/schemas/document.schema.yaml"
    schema_path.write_text(
        schema_path.read_text(encoding="utf-8").replace("version: 4", "version: 99"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported schema version 99"):
        check_repository(repository)


def test_project_health_uses_the_controlled_vocabulary(repository: Path) -> None:
    """Near-miss health labels do not create fragmented dashboard states."""
    path = write_document(repository, "20-projects/example/index.md")
    path.write_text(
        path.read_text(encoding="utf-8").replace("health: unknown", "health: ambre"),
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == [
        "invalid health 'ambre'; expected one of: amber, green, red, unknown",
    ]


def test_frontmatter_rejects_duplicate_keys(repository: Path) -> None:
    """A repeated key cannot be silently overwritten by the YAML loader."""
    path = write_document(repository, "20-projects/example/index.md")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "status: active",
            "status: planned\nstatus: active",
        ),
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert len(messages) == 1
    assert "found duplicate key 'status'" in messages[0]


def test_unknown_frontmatter_field_requires_extension_prefix(repository: Path) -> None:
    """Typos fail while explicitly namespaced extension fields remain available."""
    path = write_document(repository, "20-projects/example/index.md")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "updated: 2026-07-28",
            "udpated: 2026-07-28\nupdated: 2026-07-28\nx-owner: finance",
        ),
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == [
        "unknown frontmatter field: udpated; use x-* for custom fields",
    ]


def test_empty_project_subdirectory_is_a_non_blocking_warning(
    repository: Path,
) -> None:
    """Explorer clutter is reported without making an in-progress edit invalid."""
    empty = repository / "20-projects/example/reports"
    empty.mkdir(parents=True)

    report = check_worktree(repository)

    assert report.errors == ()
    assert [str(issue) for issue in report.warnings] == [
        "20-projects/example/reports: empty directory can be removed",
    ]


def test_external_resource_rejects_sensitive_query_parameter(
    repository: Path,
) -> None:
    """Copied share links cannot persist credentials or access tokens."""
    write_document(repository, "20-projects/example/index.md")
    resource = repository / "20-projects/example/links/scope.md"
    resource.parent.mkdir()
    resource.write_text(
        """---
type: artifact
id: artifact:project:example:scope
kind: external-resource
status: active
created: 2026-07-28
updated: 2026-07-28
provider: sharepoint
url: https://example.com/scope.docx?token=secret
owner: ERP Team
access: restricted
last_verified: 2026-07-28
related: [project:example]
---

# Scope
""",
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == ["url contains sensitive query parameter: token"]


def test_direct_external_link_is_indexed_without_promotion(repository: Path) -> None:
    """Pasting a normal link is enough for AI discovery."""
    project = write_document(repository, "20-projects/example/index.md")
    project.write_text(
        f"{project.read_text(encoding='utf-8')}"
        "\n## Important documents\n\n"
        "- [SaaS access register]"
        "(https://tenant.sharepoint.com/sites/it/register.xlsx)\n",
        encoding="utf-8",
    )

    payload = json.loads(build_index(repository).read_text(encoding="utf-8"))
    entry = payload["documents"][0]

    assert entry["derived"]["external_links"] == [
        {
            "label": "SaaS access register",
            "url": "https://tenant.sharepoint.com/sites/it/register.xlsx",
            "provider": "sharepoint",
            "line": 15,
        },
    ]


def test_direct_external_link_rejects_sensitive_query_parameter(
    repository: Path,
) -> None:
    """Low-friction pasted links still receive local secret checks."""
    project = write_document(repository, "20-projects/example/index.md")
    project.write_text(
        f"{project.read_text(encoding='utf-8')}"
        "\n[Temporary share](https://example.com/file.xlsx?access_token=secret)\n",
        encoding="utf-8",
    )

    messages = [issue.message for issue in check_repository(repository)]

    assert messages == [
        "line 13: url contains sensitive query parameter: access_token",
    ]


def test_check_reports_broken_markdown_link(repository: Path) -> None:
    """Normal relative links are validated with a useful source line."""
    write_document(repository, "20-projects/example/index.md")
    report = repository / "20-projects/example/reports/report.md"
    report.parent.mkdir()
    report.write_text("# Report\n\n[Missing](missing.md)\n", encoding="utf-8")

    issues = check_repository(repository)

    assert len(issues) == 1
    assert issues[0].message == "line 3: linked path does not exist: missing.md"


def test_check_ignores_links_in_code_blocks(repository: Path) -> None:
    """Documentation examples do not create false-positive broken links."""
    write_document(repository, "20-projects/example/index.md")
    report = repository / "20-projects/example/reports/report.md"
    report.parent.mkdir()
    report.write_text(
        "# Report\n\n```markdown\n[Example](missing.md)\n```\n",
        encoding="utf-8",
    )

    assert check_repository(repository) == []


@pytest.mark.parametrize("filename", ["settings.yaml", "views/projects.base"])
def test_rejects_duplicate_keys_in_repository_yaml(repository: Path, filename: str) -> None:
    config = repository / filename
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("mode: safe\nmode: fast\n", encoding="utf-8")

    issues = check_repository(repository)

    assert any(
        issue.path == Path(filename) and "duplicate key" in issue.message for issue in issues
    )


def test_rejects_windows_reserved_path_component(repository: Path) -> None:
    reserved = repository / "CON.txt"
    reserved.write_text("portable content\n", encoding="utf-8")

    issues = check_repository(repository)

    assert any("reserved on Windows" in issue.message for issue in issues)


def test_rejects_file_over_configured_size(repository: Path) -> None:
    policy = repository / ".workspace/policy.yaml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            "max_attachment_bytes: 26214400",
            "max_attachment_bytes: 10",
        ),
        encoding="utf-8",
    )
    attachment = repository / "attachment.bin"
    attachment.write_bytes(b"01234567890")

    issues = check_repository(repository)

    assert any(
        issue.path == Path("attachment.bin") and "size limit" in issue.message for issue in issues
    )


def test_rejects_future_metadata_date(repository: Path) -> None:
    path = write_document(repository, "20-projects/example/index.md")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "updated: 2026-07-28",
            "updated: 2999-01-01",
        ),
        encoding="utf-8",
    )

    issues = check_repository(repository)

    assert any(issue.message == "updated must not be in the future" for issue in issues)
