"""Synchronization of stable relationship IDs to portable Markdown links."""

import posixpath
import re
from pathlib import Path
from urllib.parse import quote

from workrepo.discovery import discover_documents
from workrepo.models import Document
from workrepo.schema import load_schema
from workrepo.validation import check_repository, identifier, related_ids

RELATED_START = "<!-- workrepo:related:start -->"
RELATED_END = "<!-- workrepo:related:end -->"
RELATED_BLOCK_PATTERN = re.compile(
    rf"\n*## Related documents\n\n{re.escape(RELATED_START)}\n"
    rf".*?{re.escape(RELATED_END)}\n?",
    flags=re.DOTALL,
)


def sync_related_links(root: Path) -> int:
    """Synchronize generated Markdown links from canonical related IDs."""
    repository_root = root.resolve()
    issues = check_repository(repository_root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"cannot synchronize links while validation issues exist:\n{details}"
        raise ValueError(message)

    schema = load_schema(repository_root)
    documents, parse_issues = discover_documents(repository_root, schema)
    if parse_issues:
        message = "documents changed while synchronizing links"
        raise RuntimeError(message)
    documents_by_id = {
        document_id: document
        for document in documents
        if (document_id := identifier(document)) is not None
    }

    changed = 0
    for document in documents:
        path = repository_root / document.path
        source = path.read_text(encoding="utf-8")
        replacement = _related_block(document, documents_by_id)
        updated = _replace_related_block(source, replacement, path=document.path)
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def _related_block(
    document: Document,
    documents_by_id: dict[str, Document],
) -> str:
    links = [
        _related_link(document, documents_by_id[related_id], related_id)
        for related_id in related_ids(document)
    ]
    if not links:
        return ""
    items = "\n".join(f"- {link}" for link in links)
    return f"\n\n## Related documents\n\n{RELATED_START}\n{items}\n{RELATED_END}\n"


def _related_link(source: Document, target: Document, document_id: str) -> str:
    start = source.path.parent.as_posix()
    relative_path = posixpath.relpath(target.path.as_posix(), start=start)
    encoded_path = quote(relative_path, safe="/:@-._~")
    escaped_title = target.title.replace("]", r"\]")
    return f"[{escaped_title}]({encoded_path}) (`{document_id}`)"


def _replace_related_block(source: str, replacement: str, *, path: Path) -> str:
    has_start = RELATED_START in source
    has_end = RELATED_END in source
    match = RELATED_BLOCK_PATTERN.search(source)
    if (has_start or has_end) and match is None:
        message = f"{path}: generated related document markers are malformed"
        raise ValueError(message)
    if match is not None:
        updated = RELATED_BLOCK_PATTERN.sub(replacement, source, count=1)
        return f"{updated.rstrip()}\n"
    if not replacement:
        return source
    return f"{source.rstrip()}{replacement}"
