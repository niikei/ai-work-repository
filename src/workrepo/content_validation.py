"""Document and artifact metadata validation."""

import re
from collections import Counter
from collections.abc import Iterable
from datetime import date

from workrepo.calendar import work_week
from workrepo.external_resource_validation import validate_external_resource
from workrepo.location_validation import validate_artifact_location, validate_document_location
from workrepo.models import Artifact, ContentDocument, Document, Issue
from workrepo.schema import Schema, TypeRule

ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*:[a-z0-9][a-z0-9:-]*$")


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


def validate_content(
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
    issues.extend(validate_document_location(document, rule, schema))
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
    if "owner" in metadata and not _is_nonempty_string(metadata["owner"]):
        issues.append(Issue(document.path, "owner must be a non-empty string"))
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
    issues.extend(validate_artifact_location(artifact, schema))
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
    issues.extend(validate_external_resource(artifact))
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


def _validate_id(document: ContentDocument, document_type: str) -> list[Issue]:
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
    future_limited_fields = {"created", "updated"}
    if document.metadata.get("type") == "area":
        fields.append("last_reviewed")
        future_limited_fields.add("last_reviewed")
    if document.metadata.get("type") == "project":
        fields.append("target_date")
    if document.metadata.get("kind") == "external-resource":
        fields.append("last_verified")
        future_limited_fields.add("last_verified")
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
        if field in future_limited_fields and value > today
    )
    if parsed.keys() >= {"created", "updated"} and parsed["updated"] < parsed["created"]:
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


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


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
