"""Repository-wide metadata, structure, and Markdown-link validation."""

import re
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

from workrepo.calendar import work_week
from workrepo.discovery import discover_artifacts, discover_documents
from workrepo.markdown import inspect_markdown
from workrepo.models import Document, Issue
from workrepo.schema import Schema, TypeRule, load_schema

ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9][a-z0-9:-]*$")
IGNORED_MARKDOWN_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".workspace",
    },
)


def check_repository(root: Path) -> list[Issue]:
    """Return every validation issue found in a work repository."""
    repository_root = root.resolve()
    schema = load_schema(repository_root)
    documents, issues = discover_documents(repository_root, schema)
    issues.extend(_validate_documents(documents, schema))
    _, artifact_issues = discover_artifacts(repository_root, schema, documents)
    issues.extend(artifact_issues)
    issues.extend(_validate_markdown_links(repository_root))
    return sorted(issues)


def read_documents(root: Path) -> list[Document]:
    """Read every valid entity document from a repository."""
    repository_root = root.resolve()
    issues = check_repository(repository_root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"cannot read documents while validation issues exist:\n{details}"
        raise ValueError(message)
    schema = load_schema(repository_root)
    documents, parse_issues = discover_documents(repository_root, schema)
    if parse_issues:
        message = "documents changed while reading the repository"
        raise RuntimeError(message)
    return documents


def identifier(document: Document) -> str | None:
    """Return a document's string identifier when present."""
    value = document.metadata.get("id")
    return value if isinstance(value, str) else None


def related_ids(document: Document) -> Iterable[str]:
    """Yield well-formed relationship values for a document."""
    raw = document.metadata.get("related")
    if not isinstance(raw, list):
        return ()
    return (item for item in raw if isinstance(item, str))


def _validate_documents(documents: list[Document], schema: Schema) -> list[Issue]:
    issues = [issue for document in documents for issue in _validate_document(document, schema)]
    identifiers = [
        document_id
        for document in documents
        if (document_id := identifier(document)) is not None
    ]
    duplicates = {
        document_id
        for document_id, count in Counter(identifiers).items()
        if count > 1
    }
    issues.extend(
        Issue(document.path, f"duplicate id: {document_id}")
        for document in documents
        if (document_id := identifier(document)) in duplicates
    )

    known_ids = set(identifiers)
    for document in documents:
        issues.extend(
            Issue(document.path, f"related id does not exist: {related_id}")
            for related_id in related_ids(document)
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
    issues.extend(_validate_log_path(document, rule))
    issues.extend(_validate_related(document))
    return issues


def _validate_location(document: Document, rule: TypeRule) -> list[Issue]:
    if document.path.is_relative_to(rule.root):
        return []
    return [Issue(document.path, f"must be located under {rule.root}/")]


def _validate_id(document: Document, document_type: str) -> list[Issue]:
    document_id = document.metadata.get("id")
    if document_id is None:
        return []
    if not isinstance(document_id, str) or ID_PATTERN.fullmatch(document_id) is None:
        return [Issue(document.path, "id must be a lowercase namespaced identifier")]
    if not document_id.startswith(f"{document_type}:"):
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
    document_id = identifier(document)
    if document_id is not None and document_id in raw:
        return [Issue(document.path, "related must not contain the document's own ID")]
    return []


def _validate_log_path(document: Document, rule: TypeRule) -> list[Issue]:
    if document.metadata.get("type") != "log":
        return []
    log_date = _parse_date(document.metadata.get("date"))
    if log_date is None:
        return []
    week = work_week(log_date)
    expected_parent = (
        rule.root
        / f"{week.start:%Y}"
        / f"{week.start:%m}"
        / week.directory_name
    )
    expected_prefix = f"{log_date.isoformat()}-"
    issues: list[Issue] = []
    if document.path.parent != expected_parent:
        issues.append(
            Issue(
                document.path,
                f"log for {log_date.isoformat()} must be located under {expected_parent}/",
            ),
        )
    if document.path.suffix != ".md" or not document.path.name.startswith(expected_prefix):
        issues.append(
            Issue(
                document.path,
                f"log filename must start with {expected_prefix}",
            ),
        )
    return issues


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _validate_markdown_links(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path in _markdown_paths(root):
        relative_path = path.relative_to(root)
        try:
            links = inspect_markdown(path.read_text(encoding="utf-8")).links
        except (OSError, UnicodeError) as error:
            issues.append(Issue(relative_path, str(error)))
            continue
        issues.extend(
            issue
            for link in links
            if (issue := _validate_markdown_link(root, path, link.target, link.line))
            is not None
        )
    return issues


def _markdown_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not set(path.relative_to(root).parts) & IGNORED_MARKDOWN_DIRECTORIES
    )


def _validate_markdown_link(
    root: Path,
    source: Path,
    target: str,
    line: int,
) -> Issue | None:
    try:
        parsed = urlsplit(target)
    except ValueError:
        return Issue(source.relative_to(root), f"line {line}: invalid link: {target}")
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None

    decoded_path = unquote(parsed.path)
    candidate = (
        root / decoded_path.removeprefix("/")
        if decoded_path.startswith("/")
        else source.parent / decoded_path
    ).resolve()
    if not candidate.is_relative_to(root):
        return Issue(
            source.relative_to(root),
            f"line {line}: link escapes repository: {target}",
        )
    if candidate.exists() or (not candidate.suffix and candidate.with_suffix(".md").exists()):
        return None
    return Issue(
        source.relative_to(root),
        f"line {line}: linked path does not exist: {target}",
    )
