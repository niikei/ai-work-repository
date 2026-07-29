"""Safe, reversible movement of inactive records into the repository archive."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from workrepo.clock import current_date
from workrepo.indexing import INDEX_OUTPUT
from workrepo.markdown import inspect_markdown
from workrepo.repository import refresh_repository
from workrepo.validation import require_repository

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from workrepo.models import Document
    from workrepo.schema import Schema, TypeRule
    from workrepo.state import RepositoryState

ARCHIVABLE_STATUSES = {
    "project": frozenset({"completed", "cancelled"}),
    "area": frozenset({"retired"}),
    "role": frozenset({"retired"}),
    "system": frozenset({"retired"}),
    "process": frozenset({"retired"}),
    "reference": frozenset({"retired"}),
}
IGNORED_DIRECTORIES = frozenset(
    {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv"},
)


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    """One completed archive or restore operation."""

    document_id: str
    source: Path
    destination: Path


@dataclass(frozen=True, slots=True)
class _Move:
    source: Path
    destination: Path
    source_document: Path
    destination_document: Path


@dataclass(frozen=True, slots=True)
class _Relocation:
    root: Path
    source: Path
    destination: Path


def archive_document(
    root: Path,
    document_id: str,
    *,
    operation_date: date | None = None,
) -> LifecycleResult:
    """Move one inactive durable record into its year-based archive."""
    state = require_repository(root)
    document = _document_by_id(state, document_id)
    document_type, rule = _archivable_rule(state.schema, document)
    if document.path.is_relative_to(state.schema.archive_root):
        message = f"document is already archived: {document_id}"
        raise ValueError(message)
    status = document.metadata.get("status")
    allowed = ARCHIVABLE_STATUSES[document_type]
    if status not in allowed:
        expected = ", ".join(sorted(allowed))
        message = f"cannot archive {document_id} with status {status!r}; expected: {expected}"
        raise ValueError(message)
    effective_date = operation_date or current_date(state.policy.timezone)
    destination_document = _archive_document_path(
        state.schema,
        rule,
        document_type,
        document_id,
        effective_date.year,
    )
    move = _move_for_document(document, destination_document)
    return _relocate(state, document_id, move)


def restore_document(root: Path, document_id: str) -> LifecycleResult:
    """Move one archived durable record back to its active type root."""
    state = require_repository(root)
    document = _document_by_id(state, document_id)
    document_type, rule = _archivable_rule(state.schema, document)
    if not document.path.is_relative_to(state.schema.archive_root):
        message = f"document is not archived: {document_id}"
        raise ValueError(message)
    destination_document = _active_document_path(rule, document_type, document_id)
    move = _move_for_document(document, destination_document)
    return _relocate(state, document_id, move)


def is_archived(path: Path, schema: Schema) -> bool:
    """Return whether a repository-relative path lives in the archive."""
    return path.is_relative_to(schema.archive_root)


def _document_by_id(state: RepositoryState, document_id: str) -> Document:
    matches = [
        document for document in state.documents if document.metadata.get("id") == document_id
    ]
    if not matches:
        message = f"document does not exist: {document_id}"
        raise ValueError(message)
    return matches[0]


def _archivable_rule(schema: Schema, document: Document) -> tuple[str, TypeRule]:
    document_type = document.metadata.get("type")
    if not isinstance(document_type, str) or document_type not in ARCHIVABLE_STATUSES:
        message = f"document type cannot be archived: {document_type!r}"
        raise ValueError(message)
    rule = schema.types[document_type]
    if rule.archive is None:
        message = f"document type has no archive destination: {document_type}"
        raise ValueError(message)
    return document_type, rule


def _archive_document_path(
    schema: Schema,
    rule: TypeRule,
    document_type: str,
    document_id: str,
    year: int,
) -> Path:
    slug = _slug(document_id)
    base = schema.archive_root / str(year) / _required_archive(rule)
    if document_type in {"project", "area"}:
        return base / slug / "index.md"
    return base / f"{slug}.md"


def _active_document_path(
    rule: TypeRule,
    document_type: str,
    document_id: str,
) -> Path:
    slug = _slug(document_id)
    if document_type in {"project", "area"}:
        return rule.root / slug / "index.md"
    return rule.root / f"{slug}.md"


def _required_archive(rule: TypeRule) -> Path:
    if rule.archive is None:
        message = "archive destination is required"
        raise ValueError(message)
    return rule.archive


def _slug(document_id: str) -> str:
    _, separator, slug = document_id.partition(":")
    if not separator or not slug:
        message = f"invalid document ID: {document_id}"
        raise ValueError(message)
    return slug


def _move_for_document(document: Document, destination_document: Path) -> _Move:
    if document.metadata.get("type") in {"project", "area"}:
        return _Move(
            source=document.path.parent,
            destination=destination_document.parent,
            source_document=document.path,
            destination_document=destination_document,
        )
    return _Move(
        source=document.path,
        destination=destination_document,
        source_document=document.path,
        destination_document=destination_document,
    )


def _relocate(
    state: RepositoryState,
    document_id: str,
    move: _Move,
) -> LifecycleResult:
    root = state.root
    source = root / move.source
    destination = root / move.destination
    if destination.exists():
        message = f"destination already exists: {move.destination}"
        raise FileExistsError(message)
    snapshots = _snapshots(root)
    replacements = _link_replacements(
        _Relocation(root=root, source=source, destination=destination),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    archive_root = root / state.schema.archive_root
    try:
        source.rename(destination)
    except OSError:
        if destination.is_relative_to(archive_root):
            _prune_empty(destination.parent, stop=archive_root)
        raise
    try:
        _apply_link_replacements(replacements)
        refresh_repository(root)
        require_repository(root)
    except Exception:
        _rollback(
            root,
            source,
            destination,
            snapshots,
            archive_root=archive_root,
        )
        raise
    if source.is_relative_to(archive_root):
        _prune_empty(source.parent, stop=archive_root)
    return LifecycleResult(
        document_id=document_id,
        source=move.source_document,
        destination=move.destination_document,
    )


def _snapshots(root: Path) -> dict[Path, bytes]:
    paths = [*_markdown_paths(root)]
    index = root / INDEX_OUTPUT
    if index.is_file():
        paths.append(index)
    return {path: path.read_bytes() for path in paths}


def _markdown_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not set(path.relative_to(root).parts) & IGNORED_DIRECTORIES
    )


def _link_replacements(move: _Relocation) -> dict[Path, dict[str, str]]:
    result: dict[Path, dict[str, str]] = {}
    for markdown_path in _markdown_paths(move.root):
        post_source = _relocated_path(
            markdown_path,
            move.source,
            move.destination,
        )
        source_text = markdown_path.read_text(encoding="utf-8")
        for link in inspect_markdown(source_text).links:
            replacement = _relocated_link(
                markdown_path,
                post_source,
                link.target,
                move,
            )
            if replacement is not None and replacement != link.target:
                result.setdefault(post_source, {})[link.target] = replacement
    return result


def _relocated_link(
    pre_source: Path,
    post_source: Path,
    target: str,
    move: _Relocation,
) -> str | None:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    decoded = unquote(parsed.path)
    pre_target = (
        move.root / decoded.removeprefix("/")
        if decoded.startswith("/")
        else pre_source.parent / decoded
    ).resolve()
    if not pre_target.is_relative_to(move.root):
        return None
    post_target = _relocated_path(
        pre_target,
        move.source,
        move.destination,
    )
    if post_source == pre_source and post_target == pre_target:
        return None
    if decoded.startswith("/"):
        path = f"/{post_target.relative_to(move.root).as_posix()}"
    else:
        path = posixpath.relpath(
            post_target.as_posix(),
            start=post_source.parent.as_posix(),
        )
    encoded = quote(path, safe="/:@-._~")
    return urlunsplit(("", "", encoded, parsed.query, parsed.fragment))


def _relocated_path(path: Path, source: Path, destination: Path) -> Path:
    try:
        relative = path.relative_to(source)
    except ValueError:
        return path
    return destination / relative


def _apply_link_replacements(replacements: dict[Path, dict[str, str]]) -> None:
    for path, path_replacements in replacements.items():
        source = path.read_text(encoding="utf-8")
        updated = source
        for old, new in sorted(
            path_replacements.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            updated = updated.replace(old, new)
        if updated == source:
            continue
        path.write_text(updated, encoding="utf-8")


def _rollback(
    root: Path,
    source: Path,
    destination: Path,
    snapshots: dict[Path, bytes],
    *,
    archive_root: Path,
) -> None:
    if destination.exists() and not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        destination.rename(source)
    for path, content in snapshots.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    index = root / INDEX_OUTPUT
    if index not in snapshots and index.exists():
        index.unlink()
    if destination.is_relative_to(archive_root):
        _prune_empty(destination.parent, stop=archive_root)


def _prune_empty(path: Path, *, stop: Path) -> None:
    current = path
    while current != stop and current.is_relative_to(stop):
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
