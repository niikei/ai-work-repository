"""Synchronization of stable relationship IDs to portable Markdown links."""

import posixpath
from pathlib import Path
from urllib.parse import quote

from workrepo.generated import RELATED_END, RELATED_START, replace_related_block
from workrepo.models import ContentDocument
from workrepo.state import RepositoryState
from workrepo.validation import identifier, related_ids, require_repository


def sync_related_links(root: Path, *, state: RepositoryState | None = None) -> int:
    """Synchronize generated Markdown links from canonical related IDs."""
    repository_state = state or require_repository(root)
    repository_root = repository_state.root
    content: list[ContentDocument] = [
        *repository_state.documents,
        *(artifact for artifact in repository_state.artifacts if artifact.typed),
    ]
    documents_by_id = {
        document_id: document
        for document in content
        if (document_id := identifier(document)) is not None
    }

    updates: list[tuple[Path, str]] = []
    for document in content:
        path = repository_root / document.path
        source = path.read_text(encoding="utf-8")
        replacement = _related_block(document, documents_by_id)
        updated = replace_related_block(source, replacement, path=document.path)
        if updated != source:
            updates.append((path, updated))
    for path, updated in updates:
        path.write_text(updated, encoding="utf-8")
    return len(updates)


def _related_block(
    document: ContentDocument,
    documents_by_id: dict[str, ContentDocument],
) -> str:
    links = [
        _related_link(document, documents_by_id[related_id], related_id)
        for related_id in related_ids(document)
    ]
    if not links:
        return ""
    items = "\n".join(f"- {link}" for link in links)
    return f"\n\n## Related documents\n\n{RELATED_START}\n{items}\n{RELATED_END}\n"


def _related_link(
    source: ContentDocument,
    target: ContentDocument,
    document_id: str,
) -> str:
    start = source.path.parent.as_posix()
    relative_path = posixpath.relpath(target.path.as_posix(), start=start)
    encoded_path = quote(relative_path, safe="/:@-._~")
    escaped_title = target.title.replace("]", r"\]")
    return f"[{escaped_title}]({encoded_path}) (`{document_id}`)"
