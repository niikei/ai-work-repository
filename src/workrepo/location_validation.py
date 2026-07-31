"""Schema-defined active and archive location validation."""

from pathlib import Path

from workrepo.models import Artifact, Document, Issue
from workrepo.schema import Schema, TypeRule

ARCHIVE_YEAR_LENGTH = 4
INDEX_DOCUMENT_REMAINDER_PARTS = 2


def validate_document_location(
    document: Document,
    rule: TypeRule,
    schema: Schema,
) -> list[Issue]:
    document_type = document.metadata.get("type")
    if document.path.is_relative_to(rule.root):
        if document_type in {"log", "project", "area"}:
            return []
        if document.path.parent == rule.root:
            return []
        return [
            Issue(
                document.path,
                f"must be located directly under {rule.root}/",
            ),
        ]
    if (
        isinstance(document_type, str)
        and rule.archive is not None
        and _is_archive_location(
            document.path,
            schema.archive_root,
            rule.archive,
            indexed=document_type in {"project", "area"},
        )
    ):
        return []
    return [
        Issue(
            document.path,
            f"must be located under {rule.root}/ or {schema.archive_root}/",
        ),
    ]


def validate_artifact_location(artifact: Artifact, schema: Schema) -> list[Issue]:
    if any(artifact.path.is_relative_to(root) for root in schema.artifact.roots):
        return []
    if _has_archive_year(artifact.path, schema.archive_root):
        return []
    roots = ", ".join(f"{root}/" for root in schema.artifact.roots)
    return [
        Issue(
            artifact.path,
            f"artifact must be located under one of: {roots}, {schema.archive_root}/",
        ),
    ]


def _is_archive_location(
    path: Path,
    archive_root: Path,
    archive_directory: Path,
    *,
    indexed: bool,
) -> bool:
    try:
        relative = path.relative_to(archive_root)
    except ValueError:
        return False
    prefix_size = 1 + len(archive_directory.parts)
    if len(relative.parts) <= prefix_size:
        return False
    year = relative.parts[0]
    if len(year) != ARCHIVE_YEAR_LENGTH or not year.isdigit():
        return False
    if relative.parts[1:prefix_size] != archive_directory.parts:
        return False
    remainder = relative.parts[prefix_size:]
    if indexed:
        return len(remainder) == INDEX_DOCUMENT_REMAINDER_PARTS and remainder[-1] == "index.md"
    return len(remainder) == 1 and remainder[0].endswith(".md")


def _has_archive_year(path: Path, archive_root: Path) -> bool:
    try:
        relative = path.relative_to(archive_root)
    except ValueError:
        return False
    return bool(
        relative.parts
        and len(relative.parts[0]) == ARCHIVE_YEAR_LENGTH
        and relative.parts[0].isdigit()
    )
