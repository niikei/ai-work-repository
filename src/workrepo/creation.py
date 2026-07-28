"""Safe creation of work documents from repository templates."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from workrepo.calendar import work_week
from workrepo.discovery import discover_artifacts, discover_documents
from workrepo.models import ContentDocument
from workrepo.schema import Schema, TypeRule, load_schema

DOCUMENT_TYPES = ("log", "project", "area", "role", "system", "process", "reference")
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
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LENGTH = 64
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    },
)
H1_PATTERN = re.compile(r"^# .+$", flags=re.MULTILINE)
ID_PATTERN = re.compile(r"^id: .+$", flags=re.MULTILINE)
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
    _validate_slug(request.slug)
    normalized_title = _normalize_title(request.title)
    _validate_related_ids(repository_root, schema, request.related)

    effective_date = request.document_date or _today()
    destination = _document_path(
        repository_root,
        schema.types[request.document_type],
        request.document_type,
        request.slug,
        effective_date,
    )
    _ensure_path_available(destination, repository_root)

    template_path = repository_root / schema.templates_root / f"{request.document_type}.md"
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
    _validate_slug(request.slug)
    normalized_title = _normalize_title(request.title)
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

    effective_date = request.document_date or _today()
    parent_slug = request.parent_id.split(":", maxsplit=1)[1]
    parent_type = str(parent.metadata["type"])
    artifact_id = f"artifact:{parent_type}:{parent_slug}:{request.slug}"
    if artifact_id in _known_ids(repository_root, schema):
        message = f"document ID already exists: {artifact_id}"
        raise FileExistsError(message)
    directory = ARTIFACT_DIRECTORIES[request.kind]
    destination = repository_root / parent.path.parent / directory / f"{request.slug}.md"
    _ensure_path_available(destination, repository_root)
    template_name = (
        "external-resource.md" if request.kind == "external-resource" else "artifact.md"
    )
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

    effective_date = capture_date or _today()
    path = repository_root / schema.inbox_root / f"{effective_date.isoformat()}.md"
    _ensure_inside_repository(path, repository_root)
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
    rendered = ID_PATTERN.sub(f"id: {identifier}", rendered, count=1)
    rendered = H1_PATTERN.sub(f"# {title}", rendered, count=1)
    related_yaml = (
        "related: []"
        if not request.related
        else "related:\n" + "\n".join(f"  - {related_id}" for related_id in request.related)
    )
    rendered = RELATED_PATTERN.sub(related_yaml, rendered, count=1)
    return f"{rendered.rstrip()}\n"


def _validate_slug(slug: str) -> None:
    if len(slug) > MAX_SLUG_LENGTH:
        message = f"slug must be at most {MAX_SLUG_LENGTH} characters"
        raise ValueError(message)
    if SLUG_PATTERN.fullmatch(slug) is None:
        message = "slug must use lowercase letters, numbers, and single hyphens"
        raise ValueError(message)
    if slug.casefold() in WINDOWS_RESERVED_NAMES:
        message = f"slug is reserved on Windows: {slug}"
        raise ValueError(message)


def _normalize_title(title: str) -> str:
    normalized = " ".join(title.split())
    if not normalized:
        message = "title must not be empty"
        raise ValueError(message)
    return normalized


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


def _ensure_path_available(destination: Path, root: Path) -> None:
    _ensure_inside_repository(destination, root)
    if destination.exists():
        message = f"document already exists: {destination.relative_to(root)}"
        raise FileExistsError(message)
    current = root
    for component in destination.relative_to(root).parts:
        if not current.is_dir():
            break
        conflicting = next(
            (
                child
                for child in current.iterdir()
                if child.name.casefold() == component.casefold() and child.name != component
            ),
            None,
        )
        if conflicting is not None:
            message = f"document path conflicts by letter case: {destination.relative_to(root)}"
            raise FileExistsError(message)
        current /= component


def _ensure_inside_repository(destination: Path, root: Path) -> None:
    if destination.resolve().is_relative_to(root.resolve()):
        return
    message = f"destination escapes repository: {destination}"
    raise ValueError(message)


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


def _today() -> date:
    return datetime.now(tz=UTC).astimezone().date()
