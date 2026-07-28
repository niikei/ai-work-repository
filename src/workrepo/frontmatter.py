"""Markdown frontmatter parsing without mutating source documents."""

from pathlib import Path

import yaml

from workrepo.markdown import inspect_markdown
from workrepo.models import Document

FRONTMATTER_MARKER = "---"


class DocumentParseError(ValueError):
    """Raised when a managed Markdown document cannot be parsed."""


def parse_document(path: Path, *, root: Path) -> Document:
    """Parse one managed Markdown document."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    relative_path = path.relative_to(root)
    if not lines or lines[0] != FRONTMATTER_MARKER:
        message = "YAML frontmatter must start on the first line"
        raise DocumentParseError(message)

    try:
        closing_index = lines.index(FRONTMATTER_MARKER, 1)
    except ValueError as error:
        message = "YAML frontmatter has no closing marker"
        raise DocumentParseError(message) from error

    metadata = _load_metadata("\n".join(lines[1:closing_index]))
    headings = inspect_markdown("\n".join(lines[closing_index + 1 :])).headings
    if len(headings) != 1:
        message = f"expected exactly one H1 heading, found {len(headings)}"
        raise DocumentParseError(message)
    if not headings[0]:
        message = "H1 heading must not be empty"
        raise DocumentParseError(message)
    if "title" in metadata:
        message = "frontmatter must not contain title; the H1 is canonical"
        raise DocumentParseError(message)

    return Document(path=relative_path, title=headings[0], metadata=metadata)


def _load_metadata(source: str) -> dict[str, object]:
    raw: object = yaml.safe_load(source)
    if not isinstance(raw, dict):
        message = "frontmatter must be a YAML mapping"
        raise DocumentParseError(message)
    if not all(isinstance(key, str) for key in raw):
        message = "frontmatter keys must be strings"
        raise DocumentParseError(message)
    return {key: value for key, value in raw.items() if isinstance(key, str)}
