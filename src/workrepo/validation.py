"""Repository-wide metadata, structure, and Markdown-link validation."""

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from urllib.parse import SplitResult, parse_qsl, unquote, urlsplit

import yaml

from workrepo.calendar import work_week
from workrepo.clock import current_date
from workrepo.creation import WINDOWS_RESERVED_NAMES
from workrepo.generated import remove_related_block
from workrepo.inbox import InboxReport, inspect_inbox
from workrepo.markdown import inspect_markdown
from workrepo.models import Artifact, ContentDocument, Document, Issue
from workrepo.schema import Schema, TypeRule
from workrepo.state import RepositoryState, discover_repository
from workrepo.yamlutil import load_yaml

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
GENERATED_MARKDOWN_FILES = frozenset({"DASHBOARD.md", "NAVIGATION.md"})
EXTERNAL_RESOURCE_FIELDS = frozenset(
    {"provider", "url", "owner", "access", "last_verified"},
)
EXTERNAL_ACCESS_VALUES = frozenset({"internal", "restricted", "public"})
ARCHIVE_YEAR_LENGTH = 4
INDEX_DOCUMENT_REMAINDER_PARTS = 2
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "key",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
        "x-amz-signature",
    },
)


def check_repository(root: Path) -> list[Issue]:
    """Return every validation issue found in a work repository."""
    _, issues = inspect_repository(root)
    return issues


def inspect_repository(root: Path) -> tuple[RepositoryState, list[Issue]]:
    """Return one parsed state and all issues found in that state."""
    state, issues = discover_repository(root)
    issues.extend(
        _validate_content(
            list(state.documents),
            list(state.artifacts),
            state.schema,
            today=current_date(state.policy.timezone),
        ),
    )
    issues.extend(_validate_markdown_links(state.root))
    issues.extend(_validate_index_layout(state))
    issues.extend(_validate_repository_files(state))
    issues.extend(_validate_archive_layout(state))
    issues.extend(inbox_report(state).errors)
    return state, sorted(issues)


def inbox_report(
    state: RepositoryState,
    *,
    today: date | None = None,
) -> InboxReport:
    """Return Inbox health using the same state and policy as validation."""
    effective_today = today or current_date(state.policy.timezone)
    return inspect_inbox(
        state.root,
        state.schema.inbox_root,
        state.policy.inbox,
        today=effective_today,
    )


def repository_warnings(state: RepositoryState) -> list[Issue]:
    """Return non-blocking findings for a valid or invalid repository state."""
    return [*inbox_report(state).warnings, *_empty_directory_warnings(state)]


def _empty_directory_warnings(state: RepositoryState) -> list[Issue]:
    roots = (state.schema.types["project"].root, state.schema.types["area"].root)
    warnings: list[Issue] = []
    for relative_root in roots:
        root = state.root / relative_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_dir():
                continue
            try:
                empty = next(path.iterdir(), None) is None
            except OSError:
                continue
            if empty:
                warnings.append(
                    Issue(
                        path.relative_to(state.root),
                        "empty directory can be removed",
                    ),
                )
    return sorted(warnings)


def require_repository(root: Path) -> RepositoryState:
    """Return a valid parsed state or raise with every validation issue."""
    state, issues = inspect_repository(root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"repository validation failed:\n{details}"
        raise ValueError(message)
    return state


def read_documents(root: Path) -> list[Document]:
    """Read every valid entity document from a repository."""
    return list(require_repository(root).documents)


def identifier(document: ContentDocument) -> str | None:
    """Return a document's string identifier when present."""
    value = document.metadata.get("id")
    return value if isinstance(value, str) else None


def related_ids(document: ContentDocument) -> Iterable[str]:
    """Yield well-formed relationship values for a document."""
    raw = document.metadata.get("related")
    if not isinstance(raw, list):
        return ()
    return (item for item in raw if isinstance(item, str))


def _validate_repository_files(state: RepositoryState) -> list[Issue]:
    issues: list[Issue] = []
    paths = [
        path
        for path in state.root.rglob("*")
        if path.is_file() and not _is_ignored(path.relative_to(state.root))
    ]
    normalized_paths: dict[str, list[Path]] = {}
    for path in paths:
        relative = path.relative_to(state.root)
        normalized_paths.setdefault(relative.as_posix().casefold(), []).append(relative)
        issues.extend(_validate_portable_path(relative, state.policy.files.max_path_length))
        try:
            size = path.stat().st_size
        except OSError as error:
            issues.append(Issue(relative, f"cannot inspect file: {error}"))
            continue
        if size > state.policy.files.max_attachment_bytes:
            issues.append(
                Issue(
                    relative,
                    "file exceeds configured size limit: "
                    f"{size} > {state.policy.files.max_attachment_bytes} bytes",
                ),
            )
        if path.suffix.casefold() in {".yaml", ".yml"}:
            issues.extend(_validate_yaml_file(path, relative))
        if path.is_symlink():
            try:
                path.resolve().relative_to(state.root)
            except ValueError:
                issues.append(Issue(relative, "symbolic link points outside the repository"))
    issues.extend(
        Issue(path, "path differs from another path only by letter case")
        for duplicates in normalized_paths.values()
        if len(duplicates) > 1
        for path in duplicates
    )
    return issues


def _validate_index_layout(state: RepositoryState) -> list[Issue]:
    issues: list[Issue] = []
    for document_type in ("project", "area"):
        relative_root = state.schema.types[document_type].root
        root = state.root / relative_root
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("index.md")):
            remainder = path.relative_to(root)
            if len(remainder.parts) != INDEX_DOCUMENT_REMAINDER_PARTS:
                issues.append(
                    Issue(
                        path.relative_to(state.root),
                        f"{document_type} index must be located at "
                        f"{relative_root.as_posix()}/<slug>/index.md",
                    ),
                )
    for document in state.documents:
        if document.metadata.get("type") not in {"project", "area"}:
            continue
        directory = state.root / document.path.parent
        issues.extend(
            Issue(
                sibling.relative_to(state.root),
                f"Markdown beside {document.path.name} must be moved into a subdirectory",
            )
            for sibling in sorted(directory.glob("*.md"))
            if sibling.name != document.path.name
        )
    return issues


def _validate_archive_layout(state: RepositoryState) -> list[Issue]:
    archive = state.root / state.schema.archive_root
    if not archive.is_dir():
        return []
    known = {
        *(document.path for document in state.documents),
        *(artifact.path for artifact in state.artifacts),
    }
    return [
        Issue(relative, "document is not in a schema-defined archive location")
        for path in sorted(archive.rglob("*.md"))
        if path.name != "README.md" and (relative := path.relative_to(state.root)) not in known
    ]


def _validate_portable_path(path: Path, max_length: int) -> list[Issue]:
    issues: list[Issue] = []
    if len(path.as_posix()) > max_length:
        issues.append(Issue(path, f"path exceeds configured length limit: {max_length}"))
    for component in path.parts:
        if component != unicodedata.normalize("NFC", component):
            issues.append(Issue(path, "path must use Unicode NFC normalization"))
        if component.endswith((" ", ".")):
            issues.append(Issue(path, "path component must not end with a space or period"))
        if Path(component).stem.casefold() in WINDOWS_RESERVED_NAMES:
            issues.append(Issue(path, f"path component is reserved on Windows: {component}"))
    return issues


def _validate_yaml_file(path: Path, relative: Path) -> list[Issue]:
    try:
        load_yaml(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        return [Issue(relative, f"invalid YAML: {error}")]
    return []


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_MARKDOWN_DIRECTORIES for part in path.parts)


def _validate_content(
    documents: list[Document],
    artifacts: list[Artifact],
    schema: Schema,
    *,
    today: date,
) -> list[Issue]:
    typed_artifacts = [artifact for artifact in artifacts if artifact.typed]
    content: list[ContentDocument] = [*documents, *typed_artifacts]
    issues = [
        issue
        for document in documents
        for issue in _validate_document(document, schema, today=today)
    ]
    issues.extend(
        issue
        for artifact in typed_artifacts
        for issue in _validate_artifact(artifact, schema, today=today)
    )
    identifiers = [
        document_id for document in content if (document_id := identifier(document)) is not None
    ]
    duplicates = {document_id for document_id, count in Counter(identifiers).items() if count > 1}
    issues.extend(
        Issue(document.path, f"duplicate id: {document_id}")
        for document in content
        if (document_id := identifier(document)) in duplicates
    )

    known_ids = set(identifiers)
    for document in content:
        issues.extend(
            Issue(document.path, f"related id does not exist: {related_id}")
            for related_id in related_ids(document)
            if related_id not in known_ids
        )
    return issues


def _validate_document(
    document: Document,
    schema: Schema,
    *,
    today: date,
) -> list[Issue]:
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
    issues.extend(_validate_location(document, rule, schema))
    issues.extend(_validate_id(document, document_type))
    issues.extend(_validate_status(document, rule))
    issues.extend(_validate_allowed_values(document, rule))
    issues.extend(
        _validate_known_fields(
            document,
            schema.required | rule.required | rule.optional | rule.values.keys(),
        ),
    )
    issues.extend(_validate_dates(document, today=today))
    issues.extend(_validate_log_path(document, rule))
    issues.extend(_validate_related(document))
    return issues


def _validate_artifact(
    artifact: Artifact,
    schema: Schema,
    *,
    today: date,
) -> list[Issue]:
    metadata = artifact.metadata
    if metadata.get("type") != "artifact":
        return [
            Issue(
                artifact.path,
                "frontmatter in an artifact must declare type: artifact",
            ),
        ]
    required = schema.artifact.required
    issues = [
        Issue(artifact.path, f"missing required field: {field}")
        for field in sorted(required - metadata.keys())
    ]
    issues.extend(_validate_artifact_location(artifact, schema))
    issues.extend(_validate_id(artifact, "artifact"))
    issues.extend(
        _validate_enum(
            artifact,
            "status",
            schema.artifact.statuses,
        ),
    )
    issues.extend(_validate_enum(artifact, "kind", schema.artifact.kinds))
    issues.extend(
        _validate_known_fields(
            artifact,
            schema.artifact.required | schema.artifact.optional,
        ),
    )
    issues.extend(_validate_dates(artifact, today=today))
    issues.extend(_validate_artifact_period(artifact))
    issues.extend(_validate_external_resource(artifact))
    issues.extend(_validate_related(artifact))
    if artifact.parent_id is None:
        issues.append(Issue(artifact.path, "artifact has no owning Project or Area"))
    elif artifact.parent_id not in set(related_ids(artifact)):
        issues.append(
            Issue(
                artifact.path,
                f"typed artifact must relate to its owner: {artifact.parent_id}",
            ),
        )
    return issues


def _validate_location(
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


def _validate_id(document: ContentDocument, document_type: str) -> list[Issue]:
    document_id = document.metadata.get("id")
    if document_id is None:
        return []
    if not isinstance(document_id, str) or ID_PATTERN.fullmatch(document_id) is None:
        return [Issue(document.path, "id must be a lowercase namespaced identifier")]
    if not document_id.startswith(f"{document_type}:"):
        return [Issue(document.path, f"id must start with {document_type}:")]
    return []


def _validate_artifact_location(artifact: Artifact, schema: Schema) -> list[Issue]:
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


def _validate_status(document: Document, rule: TypeRule) -> list[Issue]:
    status = document.metadata.get("status")
    if status is None:
        return []
    if not isinstance(status, str) or status not in rule.statuses:
        allowed = ", ".join(sorted(rule.statuses))
        return [Issue(document.path, f"invalid status {status!r}; expected one of: {allowed}")]
    return []


def _validate_allowed_values(document: Document, rule: TypeRule) -> list[Issue]:
    return [
        issue
        for field, allowed in rule.values.items()
        if (issue := _enum_issue(document, field, allowed)) is not None
    ]


def _validate_enum(
    document: ContentDocument,
    field: str,
    allowed: frozenset[str],
) -> list[Issue]:
    issue = _enum_issue(document, field, allowed)
    return [] if issue is None else [issue]


def _validate_known_fields(
    document: ContentDocument,
    allowed: Iterable[str],
) -> list[Issue]:
    allowed_fields = set(allowed)
    return [
        Issue(
            document.path,
            f"unknown frontmatter field: {field}; use x-* for custom fields",
        )
        for field in sorted(document.metadata)
        if field not in allowed_fields and not field.startswith("x-")
    ]


def _enum_issue(
    document: ContentDocument,
    field: str,
    allowed: frozenset[str],
) -> Issue | None:
    value = document.metadata.get(field)
    if value is None:
        return None
    if isinstance(value, str) and value in allowed:
        return None
    expected = ", ".join(sorted(allowed))
    return Issue(
        document.path,
        f"invalid {field} {value!r}; expected one of: {expected}",
    )


def _validate_dates(document: ContentDocument, *, today: date) -> list[Issue]:
    fields = ["created", "updated"]
    if document.metadata.get("type") == "area":
        fields.append("last_reviewed")
    if document.metadata.get("kind") == "external-resource":
        fields.append("last_verified")
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
    issues.extend(
        Issue(document.path, f"{field} must not be in the future")
        for field, value in parsed.items()
        if value > today
    )
    if parsed.keys() >= set(fields) and parsed["updated"] < parsed["created"]:
        issues.append(Issue(document.path, "updated must not be earlier than created"))
    if (
        "last_reviewed" in parsed
        and "updated" in parsed
        and parsed["last_reviewed"] > parsed["updated"]
    ):
        issues.append(Issue(document.path, "last_reviewed must not be later than updated"))
    if (
        document.metadata.get("type") == "log"
        and (log_date := document.metadata.get("date")) is not None
        and _parse_date(log_date) is None
    ):
        issues.append(Issue(document.path, "date must be an ISO date"))
    return issues


def _validate_artifact_period(artifact: Artifact) -> list[Issue]:
    fields = ("period_start", "period_end")
    present = [field for field in fields if field in artifact.metadata]
    if not present:
        return []
    if len(present) != len(fields):
        missing = next(field for field in fields if field not in artifact.metadata)
        return [Issue(artifact.path, f"missing paired period field: {missing}")]
    start = _parse_date(artifact.metadata["period_start"])
    end = _parse_date(artifact.metadata["period_end"])
    issues = [
        Issue(artifact.path, f"{field} must be an ISO date")
        for field, value in (
            ("period_start", start),
            ("period_end", end),
        )
        if value is None
    ]
    if start is not None and end is not None and end < start:
        issues.append(Issue(artifact.path, "period_end must not be earlier than period_start"))
    return issues


def _validate_external_resource(artifact: Artifact) -> list[Issue]:
    metadata = artifact.metadata
    if metadata.get("kind") != "external-resource":
        unexpected = EXTERNAL_RESOURCE_FIELDS & metadata.keys()
        return [
            Issue(
                artifact.path,
                f"{field} is only valid for external-resource",
            )
            for field in sorted(unexpected)
        ]
    issues = [
        Issue(artifact.path, f"external-resource is missing required field: {field}")
        for field in sorted(EXTERNAL_RESOURCE_FIELDS - metadata.keys())
    ]
    issues.extend(
        Issue(artifact.path, f"{field} must be a non-empty string")
        for field in ("provider", "owner")
        if field in metadata and not _is_nonempty_string(metadata[field])
    )
    issues.extend(_validate_external_access(artifact))
    issues.extend(_validate_external_url(artifact))
    return issues


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_external_access(artifact: Artifact) -> list[Issue]:
    access = artifact.metadata.get("access")
    if access is None or access in EXTERNAL_ACCESS_VALUES:
        return []
    allowed = ", ".join(sorted(EXTERNAL_ACCESS_VALUES))
    return [
        Issue(
            artifact.path,
            f"invalid access {access!r}; expected one of: {allowed}",
        ),
    ]


def _validate_external_url(artifact: Artifact) -> list[Issue]:
    value = artifact.metadata.get("url")
    if value is None:
        return []
    if not isinstance(value, str):
        return [Issue(artifact.path, "url must be an HTTP or HTTPS URL")]
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        return [Issue(artifact.path, "url must be an HTTP or HTTPS URL")]
    return [Issue(artifact.path, message) for message in _url_security_messages(parsed)]


def _validate_related(document: ContentDocument) -> list[Issue]:
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
    expected_parent = rule.root / f"{week.start:%Y}" / f"{week.start:%m}" / week.directory_name
    expected_prefix = f"{log_date.isoformat()}-"
    issues: list[Issue] = []
    if document.path.parent != expected_parent:
        issues.append(
            Issue(
                document.path,
                "log for "
                f"{log_date.isoformat()} must be located under {expected_parent.as_posix()}/",
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
            source = path.read_text(encoding="utf-8")
            source = remove_related_block(source, path=relative_path)
            links = inspect_markdown(source).links
        except (OSError, UnicodeError, ValueError) as error:
            issues.append(Issue(relative_path, str(error)))
            continue
        issues.extend(
            issue
            for link in links
            if (issue := _validate_markdown_link(root, path, link.target, link.line)) is not None
        )
    return issues


def _markdown_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.relative_to(root).as_posix() not in GENERATED_MARKDOWN_FILES
        and not set(path.relative_to(root).parts) & IGNORED_MARKDOWN_DIRECTORIES
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
    if parsed.scheme in {"http", "https"}:
        return _external_markdown_issue(root, source, parsed, line)
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


def _external_markdown_issue(
    root: Path,
    source: Path,
    parsed: SplitResult,
    line: int,
) -> Issue | None:
    if parsed.hostname is None:
        return Issue(source.relative_to(root), f"line {line}: external URL has no hostname")
    messages = _url_security_messages(parsed)
    if not messages:
        return None
    return Issue(source.relative_to(root), f"line {line}: {messages[0]}")


def _url_security_messages(parsed: SplitResult) -> list[str]:
    messages: list[str] = []
    if parsed.username is not None or parsed.password is not None:
        messages.append("url must not contain embedded credentials")
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
    sensitive = sorted(query_keys & SENSITIVE_QUERY_KEYS)
    if sensitive:
        messages.append(f"url contains sensitive query parameter: {', '.join(sensitive)}")
    return messages
