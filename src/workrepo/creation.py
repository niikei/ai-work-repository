"""Safe creation of work documents from repository templates."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from workrepo.calendar import work_week
from workrepo.clock import current_date
from workrepo.creation_validation import (
    ensure_inside_repository,
    ensure_path_available,
    normalize_title,
    validate_log_slug,
    validate_slug,
)
from workrepo.discovery import discover_artifacts, discover_documents
from workrepo.models import ContentDocument
from workrepo.policy import load_policy
from workrepo.schema import Schema, TypeRule, load_schema

CATALOG_TYPES = ("system", "role", "organization", "service")
PLAYBOOK_TYPES = ("process", "procedure", "control", "standard")
KNOWLEDGE_TYPES = ("concept", "guide", "glossary")
RESOURCE_TYPES = ("resource",)
DOCUMENT_TYPES = (
    "log",
    "project",
    "area",
    *CATALOG_TYPES,
    *PLAYBOOK_TYPES,
    *KNOWLEDGE_TYPES,
    *RESOURCE_TYPES,
)
TEMPLATE_NAMES = {
    **dict.fromkeys(CATALOG_TYPES, "catalog"),
    **dict.fromkeys(PLAYBOOK_TYPES, "playbook"),
    **dict.fromkeys(KNOWLEDGE_TYPES, "knowledge"),
    **dict.fromkeys(RESOURCE_TYPES, "resource"),
}
ARTIFACT_DIRECTORIES = {
    "weekly-report": "reports",
    "report": "reports",
    "analysis": "analysis",
    "specification": "specifications",
    "deliverable": "deliverables",
    "attachment-note": "assets",
    "note": "notes",
    "review": "reviews",
    "control": "controls",
    "external-resource": "links",
}
H1_PATTERN = re.compile(r"^# .+$", flags=re.MULTILINE)
ID_PATTERN = re.compile(r"^id: .+$", flags=re.MULTILINE)
TYPE_PATTERN = re.compile(r"^type: .+$", flags=re.MULTILINE)
RELATED_PATTERN = re.compile(r"^related: \[\]$", flags=re.MULTILINE)


@dataclass(frozen=True, slots=True)
class CreateRequest:
    """User-supplied values for one new entity document."""

    document_type: str
    slug: str
    title: str
    related: tuple[str, ...] = ()
    document_date: date | None = None
    template_name: str | None = None
    owner: str | None = None
    priority: str | None = None
    target_date: date | None = None


@dataclass(frozen=True, slots=True)
class ExternalResourceMetadata:
    """Metadata required to keep a remote resource usable over time."""

    provider: str
    url: str
    owner: str
    access: str = "internal"
    last_verified: date | None = None


@dataclass(frozen=True, slots=True)
class ArtifactRequest:
    """User-supplied values for one typed Project or Area artifact."""

    slug: str
    title: str
    parent_id: str
    kind: str
    related: tuple[str, ...] = ()
    document_date: date | None = None
    external_resource: ExternalResourceMetadata | None = None


@dataclass(frozen=True, slots=True)
class _ArtifactTemplateValues:
    artifact_id: str
    kind: str
    title: str
    related: tuple[str, ...]
    document_date: date
    external_resource: ExternalResourceMetadata | None


def create_document(
    root: Path,
    request: CreateRequest,
) -> Path:
    """Create one entity document in its schema-defined location."""
    repository_root = root.resolve()
    schema = load_schema(repository_root)
    if request.document_type not in schema.types or request.document_type not in DOCUMENT_TYPES:
        message = f"unsupported document type: {request.document_type}"
        raise ValueError(message)
    validate_slug(request.slug)
    validate_log_slug(request.document_type, request.slug)
    normalized_title = normalize_title(request.title)
    _validate_related_ids(repository_root, schema, request.related)

    effective_date = request.document_date or _repository_today(repository_root)
    destination = _document_path(
        repository_root,
        schema.types[request.document_type],
        request.document_type,
        request.slug,
        effective_date,
    )
    ensure_path_available(destination, repository_root)

    template_name = TEMPLATE_NAMES.get(request.document_type, request.document_type)
    template_path = repository_root / schema.templates_root / f"{template_name}.md"
    if request.template_name is not None:
        if request.document_type != "log" or request.template_name not in {
            "log",
            "meeting",
            "daily",
        }:
            message = "template selection is only supported for log, meeting, and daily"
            raise ValueError(message)
        template_path = repository_root / schema.templates_root / f"{request.template_name}.md"
    template = template_path.read_text(encoding="utf-8")
    rendered = _render_template(
        template,
        request=request,
        title=normalized_title,
        document_date=effective_date,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination


def create_artifact(root: Path, request: ArtifactRequest) -> Path:
    """Create one typed artifact below its owning Project or Area."""
    repository_root = root.resolve()
    schema = load_schema(repository_root)
    validate_slug(request.slug)
    normalized_title = normalize_title(request.title)
    documents, parse_issues = discover_documents(repository_root, schema)
    if parse_issues:
        message = "cannot create an artifact while entity parse issues exist"
        raise ValueError(message)
    parents = {
        document_id: document
        for document in documents
        if document.metadata.get("type") in {"project", "area"}
        and (document_id := _document_id(document)) is not None
    }
    parent = parents.get(request.parent_id)
    if parent is None:
        message = f"Project or Area does not exist: {request.parent_id}"
        raise ValueError(message)
    if request.kind not in schema.artifact.kinds:
        allowed = ", ".join(sorted(schema.artifact.kinds))
        message = f"invalid artifact kind {request.kind!r}; expected one of: {allowed}"
        raise ValueError(message)
    _validate_external_resource_request(request)
    related = tuple(dict.fromkeys((request.parent_id, *request.related)))
    _validate_related_ids(repository_root, schema, related)

    effective_date = request.document_date or _repository_today(repository_root)
    parent_slug = request.parent_id.split(":", maxsplit=1)[1]
    parent_type = str(parent.metadata["type"])
    artifact_id = f"artifact:{parent_type}:{parent_slug}:{request.slug}"
    if artifact_id in _known_ids(repository_root, schema):
        message = f"document ID already exists: {artifact_id}"
        raise FileExistsError(message)
    directory = ARTIFACT_DIRECTORIES[request.kind]
    destination = repository_root / parent.path.parent / directory / f"{request.slug}.md"
    ensure_path_available(destination, repository_root)
    template_name = "external-resource.md" if request.kind == "external-resource" else "artifact.md"
    template = (repository_root / schema.templates_root / template_name).read_text(
        encoding="utf-8",
    )
    rendered = _render_artifact_template(
        template,
        _ArtifactTemplateValues(
            artifact_id=artifact_id,
            kind=request.kind,
            title=normalized_title,
            related=related,
            document_date=effective_date,
            external_resource=request.external_resource,
        ),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination


def capture_inbox(
    root: Path,
    text: str,
    *,
    capture_date: date | None = None,
) -> Path:
    """Append one normalized capture item to today's Inbox file."""
    repository_root = root.resolve()
    schema = load_schema(repository_root)
    normalized_text = " ".join(text.split())
    if not normalized_text:
        message = "capture text must not be empty"
        raise ValueError(message)

    effective_date = capture_date or _repository_today(repository_root)
    path = repository_root / schema.inbox_root / f"{effective_date.isoformat()}.md"
    ensure_inside_repository(path, repository_root)
    item = f"- [ ] {normalized_text}\n"
    if path.exists():
        current = path.read_text(encoding="utf-8")
        path.write_text(f"{current.rstrip()}\n{item}", encoding="utf-8")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {effective_date.isoformat()} Inbox\n\n{item}",
            encoding="utf-8",
        )
    return path


def _document_path(
    root: Path,
    rule: TypeRule,
    document_type: str,
    slug: str,
    document_date: date,
) -> Path:
    type_root = root / rule.root
    if document_type == "log":
        week = work_week(document_date)
        return (
            type_root
            / f"{week.start:%Y}"
            / f"{week.start:%m}"
            / week.directory_name
            / f"{document_date.isoformat()}-{slug}.md"
        )
    if document_type in {"project", "area"}:
        return type_root / slug / "index.md"
    return type_root / f"{slug}.md"


def _render_template(
    template: str,
    *,
    request: CreateRequest,
    title: str,
    document_date: date,
) -> str:
    identifier = (
        f"log:{document_date.isoformat()}:{request.slug}"
        if request.document_type == "log"
        else f"{request.document_type}:{request.slug}"
    )
    rendered = template.replace("YYYY-MM-DD", document_date.isoformat())
    rendered = TYPE_PATTERN.sub(f"type: {request.document_type}", rendered, count=1)
    rendered = ID_PATTERN.sub(f"id: {identifier}", rendered, count=1)
    rendered = H1_PATTERN.sub(f"# {title}", rendered, count=1)
    related_yaml = (
        "related: []"
        if not request.related
        else "related:\n" + "\n".join(f"  - {related_id}" for related_id in request.related)
    )
    rendered = RELATED_PATTERN.sub(related_yaml, rendered, count=1)
    optional_metadata: list[str] = []
    if request.owner is not None:
        optional_metadata.append(f"owner: {_yaml_string(request.owner)}")
    if request.priority is not None:
        optional_metadata.append(f"priority: {request.priority}")
    if request.target_date is not None:
        optional_metadata.append(f"target_date: {request.target_date.isoformat()}")
    if optional_metadata:
        rendered = rendered.replace(
            "created:",
            f"{'\n'.join(optional_metadata)}\ncreated:",
            1,
        )
    return f"{rendered.rstrip()}\n"


def _validate_related_ids(root: Path, schema: Schema, related: tuple[str, ...]) -> None:
    if len(related) != len(set(related)):
        message = "related IDs must not contain duplicates"
        raise ValueError(message)
    known_ids = _known_ids(root, schema)
    missing = sorted(set(related) - known_ids)
    if missing:
        message = f"related IDs do not exist: {', '.join(missing)}"
        raise ValueError(message)


def _known_ids(root: Path, schema: Schema) -> set[str]:
    documents, _ = discover_documents(root, schema)
    artifacts, _ = discover_artifacts(root, schema, documents)
    content: list[ContentDocument] = [*documents, *artifacts]
    return {
        document_id for document in content if (document_id := _document_id(document)) is not None
    }


def _document_id(document: ContentDocument) -> str | None:
    value = document.metadata.get("id")
    return value if isinstance(value, str) else None


def _render_artifact_template(
    template: str,
    values: _ArtifactTemplateValues,
) -> str:
    rendered = template.replace("YYYY-MM-DD", values.document_date.isoformat())
    rendered = ID_PATTERN.sub(f"id: {values.artifact_id}", rendered, count=1)
    rendered = rendered.replace("kind: note", f"kind: {values.kind}", 1)
    rendered = H1_PATTERN.sub(f"# {values.title}", rendered, count=1)
    related_yaml = "related:\n" + "\n".join(f"  - {related_id}" for related_id in values.related)
    rendered = RELATED_PATTERN.sub(related_yaml, rendered, count=1)
    if values.external_resource is not None:
        resource = values.external_resource
        verified = resource.last_verified or values.document_date
        rendered = rendered.replace("PROVIDER_VALUE", _yaml_string(resource.provider), 1)
        rendered = rendered.replace("URL_VALUE", _yaml_string(resource.url), 1)
        rendered = rendered.replace("OWNER_VALUE", _yaml_string(resource.owner), 1)
        rendered = rendered.replace("ACCESS_VALUE", _yaml_string(resource.access), 1)
        rendered = rendered.replace("LAST_VERIFIED", verified.isoformat(), 1)
    return f"{rendered.rstrip()}\n"


def _validate_external_resource_request(request: ArtifactRequest) -> None:
    if request.kind == "external-resource" and request.external_resource is None:
        message = "external-resource requires provider, URL, owner, and access metadata"
        raise ValueError(message)
    if request.kind != "external-resource" and request.external_resource is not None:
        message = "external resource metadata is only valid for external-resource"
        raise ValueError(message)
    resource = request.external_resource
    if resource is None:
        return
    for field, value in (("provider", resource.provider), ("owner", resource.owner)):
        if not value.strip():
            message = f"external-resource {field} must not be empty"
            raise ValueError(message)
    parsed = urlsplit(resource.url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        message = "external-resource URL must use HTTP or HTTPS"
        raise ValueError(message)
    if resource.access not in {"internal", "restricted", "public"}:
        message = "external-resource access must be internal, restricted, or public"
        raise ValueError(message)


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _repository_today(root: Path) -> date:
    return current_date(load_policy(root).timezone)
