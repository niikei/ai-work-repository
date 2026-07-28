"""Repository-wide validation and index generation."""

import json
import posixpath
import re
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from urllib.parse import quote

from workrepo.frontmatter import DocumentParseError, parse_document
from workrepo.models import Document, Issue
from workrepo.schema import Schema, TypeRule, load_schema

CONTENT_GLOBS = (
    "log/**/*.md",
    "projects/*/index.md",
    "areas/*/index.md",
    "library/roles/**/*.md",
    "library/systems/**/*.md",
    "library/processes/**/*.md",
    "library/references/**/*.md",
)
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9][a-z0-9:-]*$")
README_NAME = "README.md"
INDEX_OUTPUT = Path(".workspace/indexes/documents.json")
RELATED_START = "<!-- workrepo:related:start -->"
RELATED_END = "<!-- workrepo:related:end -->"
RELATED_BLOCK_PATTERN = re.compile(
    rf"\n*## Related documents\n\n{re.escape(RELATED_START)}\n"
    rf".*?{re.escape(RELATED_END)}\n?",
    flags=re.DOTALL,
)


def check_repository(root: Path) -> list[Issue]:
    """Return every validation issue found in a work repository."""
    repository_root = root.resolve()
    schema = load_schema(repository_root)
    documents, issues = _read_documents(repository_root)
    issues.extend(_validate_documents(documents, schema))
    return sorted(issues)


def build_index(root: Path) -> Path:
    """Validate the repository and write a deterministic JSON document index."""
    repository_root = root.resolve()
    issues = check_repository(repository_root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"cannot build index while validation issues exist:\n{details}"
        raise ValueError(message)

    documents, parse_issues = _read_documents(repository_root)
    if parse_issues:
        message = "documents changed while building the index"
        raise RuntimeError(message)
    payload = {
        "version": 1,
        "documents": [
            _index_entry(document)
            for document in sorted(documents, key=lambda item: item.path)
        ],
    }
    output = repository_root / INDEX_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    return output


def sync_related_links(root: Path) -> int:
    """Synchronize generated Markdown links from canonical related IDs."""
    repository_root = root.resolve()
    issues = check_repository(repository_root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"cannot synchronize links while validation issues exist:\n{details}"
        raise ValueError(message)

    documents, parse_issues = _read_documents(repository_root)
    if parse_issues:
        message = "documents changed while synchronizing links"
        raise RuntimeError(message)
    documents_by_id = {
        identifier: document
        for document in documents
        if (identifier := _identifier(document)) is not None
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


def _read_documents(root: Path) -> tuple[list[Document], list[Issue]]:
    paths = {
        path
        for pattern in CONTENT_GLOBS
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


def _validate_documents(documents: list[Document], schema: Schema) -> list[Issue]:
    issues = [issue for document in documents for issue in _validate_document(document, schema)]
    identifiers = [
        identifier
        for document in documents
        if (identifier := _identifier(document)) is not None
    ]
    duplicates = {identifier for identifier, count in Counter(identifiers).items() if count > 1}
    for document in documents:
        identifier = _identifier(document)
        if identifier in duplicates:
            issues.append(Issue(document.path, f"duplicate id: {identifier}"))

    known_ids = set(identifiers)
    for document in documents:
        issues.extend(
            Issue(document.path, f"related id does not exist: {related_id}")
            for related_id in _related_ids(document)
            if related_id not in known_ids
        )
    return issues


def _validate_document(document: Document, schema: Schema) -> list[Issue]:
    metadata = document.metadata
    document_type = metadata.get("type")
    if not isinstance(document_type, str) or document_type not in schema.types:
        return [Issue(document.path, f"unknown document type: {document_type!r}")]

    rule = schema.types[document_type]
    required = schema.required | rule.required
    issues = [
        Issue(document.path, f"missing required field: {field}")
        for field in sorted(required - metadata.keys())
    ]
    issues.extend(_validate_location(document, rule))
    issues.extend(_validate_id(document, document_type))
    issues.extend(_validate_status(document, rule))
    issues.extend(_validate_dates(document))
    issues.extend(_validate_related(document))
    return issues


def _validate_location(document: Document, rule: TypeRule) -> list[Issue]:
    if document.path.is_relative_to(rule.root):
        return []
    return [Issue(document.path, f"must be located under {rule.root}/")]


def _validate_id(document: Document, document_type: str) -> list[Issue]:
    identifier = document.metadata.get("id")
    if identifier is None:
        return []
    if not isinstance(identifier, str) or ID_PATTERN.fullmatch(identifier) is None:
        return [Issue(document.path, "id must be a lowercase namespaced identifier")]
    if not identifier.startswith(f"{document_type}:"):
        return [Issue(document.path, f"id must start with {document_type}:")]
    return []


def _validate_status(document: Document, rule: TypeRule) -> list[Issue]:
    status = document.metadata.get("status")
    if status is None:
        return []
    if not isinstance(status, str) or status not in rule.statuses:
        allowed = ", ".join(sorted(rule.statuses))
        return [Issue(document.path, f"invalid status {status!r}; expected one of: {allowed}")]
    return []


def _validate_dates(document: Document) -> list[Issue]:
    fields = ("created", "updated")
    parsed: dict[str, date] = {}
    issues: list[Issue] = []
    for field in fields:
        value = document.metadata.get(field)
        if value is None:
            continue
        parsed_value = _parse_date(value)
        if parsed_value is None:
            issues.append(Issue(document.path, f"{field} must be an ISO date"))
        else:
            parsed[field] = parsed_value
    if parsed.keys() >= set(fields) and parsed["updated"] < parsed["created"]:
        issues.append(Issue(document.path, "updated must not be earlier than created"))
    if (
        document.metadata.get("type") == "log"
        and (log_date := document.metadata.get("date")) is not None
        and _parse_date(log_date) is None
    ):
        issues.append(Issue(document.path, "date must be an ISO date"))
    return issues


def _validate_related(document: Document) -> list[Issue]:
    raw = document.metadata.get("related")
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        return [Issue(document.path, "related must be a list of document IDs")]
    duplicates = [item for item, count in Counter(raw).items() if count > 1]
    if duplicates:
        return [Issue(document.path, f"related contains duplicate IDs: {', '.join(duplicates)}")]
    identifier = _identifier(document)
    if identifier is not None and identifier in raw:
        return [Issue(document.path, "related must not contain the document's own ID")]
    return []


def _identifier(document: Document) -> str | None:
    value = document.metadata.get("id")
    return value if isinstance(value, str) else None


def _related_ids(document: Document) -> Iterable[str]:
    raw = document.metadata.get("related")
    if not isinstance(raw, list):
        return ()
    return (item for item in raw if isinstance(item, str))


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _index_entry(document: Document) -> dict[str, object]:
    metadata = {
        key: _json_value(value)
        for key, value in sorted(document.metadata.items())
    }
    return {
        "id": metadata["id"],
        "type": metadata["type"],
        "title": document.title,
        "path": document.path.as_posix(),
        "metadata": metadata,
    }


def _json_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _related_block(
    document: Document,
    documents_by_id: dict[str, Document],
) -> str:
    links = [
        _related_link(document, documents_by_id[related_id], related_id)
        for related_id in _related_ids(document)
    ]
    if not links:
        return ""
    items = "\n".join(f"- {link}" for link in links)
    return f"\n\n## Related documents\n\n{RELATED_START}\n{items}\n{RELATED_END}\n"


def _related_link(source: Document, target: Document, identifier: str) -> str:
    start = source.path.parent.as_posix()
    relative_path = posixpath.relpath(target.path.as_posix(), start=start)
    encoded_path = quote(relative_path, safe="/:@-._~")
    escaped_title = target.title.replace("]", r"\]")
    return f"[{escaped_title}]({encoded_path}) (`{identifier}`)"


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
