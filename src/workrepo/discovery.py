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
        for pattern in (_content_pattern(document_type, rule),)
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
    """Read non-entity Markdown artifacts inside Projects and Areas."""
    managed_paths = {document.path for document in documents}
    paths = {
        path
        for document_type in INDEX_DOCUMENT_TYPES
        for path in root.glob(f"{schema.types[document_type].root.as_posix()}/**/*.md")
        if path.name not in {README_NAME, "index.md"}
        and path.relative_to(root) not in managed_paths
    }
    artifacts: list[Artifact] = []
    issues: list[Issue] = []
    for path in sorted(paths):
        relative_path = path.relative_to(root)
        try:
            headings = inspect_markdown(path.read_text(encoding="utf-8")).headings
        except (OSError, UnicodeError) as error:
            issues.append(Issue(relative_path, str(error)))
            continue
        if len(headings) != 1:
            issues.append(
                Issue(relative_path, f"expected exactly one H1 heading, found {len(headings)}"),
            )
            continue
        if not headings[0]:
            issues.append(Issue(relative_path, "H1 heading must not be empty"))
            continue
        artifacts.append(Artifact(path=relative_path, title=headings[0]))
    return artifacts, issues


def _content_pattern(document_type: str, rule: TypeRule) -> str:
    suffix = "*/index.md" if document_type in INDEX_DOCUMENT_TYPES else "**/*.md"
    return f"{rule.root.as_posix()}/{suffix}"
