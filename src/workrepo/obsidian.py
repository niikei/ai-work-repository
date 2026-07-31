"""Obsidian URI integration for canonical repository content."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote
from webbrowser import open as open_uri

from workrepo.content_validation import identifier
from workrepo.validation import require_repository

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from workrepo.models import ContentDocument


def document_uri(root: Path, document_id: str) -> str:
    """Return an Obsidian URI for a document selected by stable ID."""
    state = require_repository(root)
    content: tuple[ContentDocument, ...] = (*state.documents, *state.artifacts)
    document = next((item for item in content if identifier(item) == document_id), None)
    if document is None:
        message = f"document does not exist: {document_id}"
        raise ValueError(message)
    absolute_path = (state.root / document.path).resolve()
    return f"obsidian://open?path={quote(str(absolute_path), safe='')}"


def open_document(
    root: Path,
    document_id: str,
    *,
    opener: Callable[[str], bool] = open_uri,
) -> str:
    """Open a canonical document in Obsidian and return the dispatched URI."""
    uri = document_uri(root, document_id)
    if not opener(uri):
        message = "operating system did not accept the Obsidian URI"
        raise RuntimeError(message)
    return uri
