"""Schema-driven discovery of entity documents and Markdown artifacts."""

from pathlib import Path

from workrepo.frontmatter import DocumentParseError, parse_document
from workrepo.markdown import inspect_markdown
from workrepo.models import Artifact, Document, Issue
from workrepo.schema import Schema, TypeRule

INDEX_DOCUMENT_TYPES = frozenset({"project", "area"})
README_NAME = "README.md"


def discover_documents(root: Path, schema: Schema) -> tuple[list[Document], list[Issue]]:
    """Parse entity documents selected by schema placement rules."""
    paths = {
        path
        for document_type, rule in schema.types.items()
        for pattern in _content_patterns(document_type, rule, schema)
        for path in root.glob(pattern)
        if path.name != README_NAME
    }
    documents: list[Document] = []
    issues: list[Issue] = []
    for path in sorted(paths):
        try:
            documents.append(parse_document(path, root=root))
        except (DocumentParseError, OSError, UnicodeError) as error:
            issues.append(Issue(path=path.relative_to(root), message=str(error)))
    return documents, issues


def discover_artifacts(
    root: Path,
    schema: Schema,
    documents: list[Document],
) -> tuple[list[Artifact], list[Issue]]:
    """Read typed and lightweight artifacts inside Projects and Areas."""
    managed_paths = {document.path for document in documents}
    paths = {
        path
        for document_type in INDEX_DOCUMENT_TYPES
        for pattern in _artifact_patterns(schema.types[document_type], schema)
        for path in root.glob(pattern)
        if path.name not in {README_NAME, "index.md"}
        and path.relative_to(root) not in managed_paths
    }
    artifacts: list[Artifact] = []
    issues: list[Issue] = []
    for path in sorted(paths):
        relative_path = path.relative_to(root)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(Issue(relative_path, str(error)))
            continue
        parent_id = _parent_identifier(relative_path, documents)
        lines = source.splitlines()
        if lines and lines[0] == "---":
            try:
                document = parse_document(path, root=root)
            except (DocumentParseError, OSError, UnicodeError) as error:
                issues.append(Issue(relative_path, str(error)))
                continue
            artifacts.append(
                Artifact(
                    path=document.path,
                    title=document.title,
                    metadata=document.metadata,
                    parent_id=parent_id,
                ),
            )
            continue
        if source.lstrip("\ufeff \t\r\n").startswith("---\n"):
            issues.append(
                Issue(
                    relative_path,
                    "YAML frontmatter must start on the first line",
                ),
            )
            continue
        headings = inspect_markdown(source).headings
        if len(headings) != 1:
            issues.append(
                Issue(relative_path, f"expected exactly one H1 heading, found {len(headings)}"),
            )
            continue
        if not headings[0]:
            issues.append(Issue(relative_path, "H1 heading must not be empty"))
            continue
        artifacts.append(
            Artifact(
                path=relative_path,
                title=headings[0],
                metadata={},
                parent_id=parent_id,
            ),
        )
    return artifacts, issues


def _parent_identifier(path: Path, documents: list[Document]) -> str | None:
    candidates = (
        document
        for document in documents
        if document.metadata.get("type") in INDEX_DOCUMENT_TYPES
        and path.is_relative_to(document.path.parent)
    )
    parent = max(candidates, key=lambda item: len(item.path.parts), default=None)
    if parent is None:
        return None
    value = parent.metadata.get("id")
    return value if isinstance(value, str) else None


def _content_patterns(
    document_type: str,
    rule: TypeRule,
    schema: Schema,
) -> tuple[str, ...]:
    active_suffix = "*/index.md" if document_type in INDEX_DOCUMENT_TYPES else "**/*.md"
    active = f"{rule.root.as_posix()}/{active_suffix}"
    if rule.archive is None:
        return (active,)
    archive_suffix = "*/index.md" if document_type in INDEX_DOCUMENT_TYPES else "*.md"
    archived = f"{schema.archive_root.as_posix()}/*/{rule.archive.as_posix()}/{archive_suffix}"
    return active, archived


def _artifact_patterns(rule: TypeRule, schema: Schema) -> tuple[str, ...]:
    active = f"{rule.root.as_posix()}/**/*.md"
    if rule.archive is None:
        return (active,)
    archived = f"{schema.archive_root.as_posix()}/*/{rule.archive.as_posix()}/**/*.md"
    return active, archived
