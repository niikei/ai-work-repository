"""Safe creation of work documents from repository templates."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from workrepo.calendar import work_week
from workrepo.frontmatter import DocumentParseError, parse_document
from workrepo.schema import Schema, TypeRule, load_schema

DOCUMENT_TYPES = ("log", "project", "area", "role", "system", "process", "reference")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
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
    if destination.exists():
        message = f"document already exists: {destination.relative_to(repository_root)}"
        raise FileExistsError(message)

    template_path = repository_root / schema.templates_root / f"{request.document_type}.md"
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
        else "related:\n"
        + "\n".join(f"  - {related_id}" for related_id in request.related)
    )
    rendered = RELATED_PATTERN.sub(related_yaml, rendered, count=1)
    return f"{rendered.rstrip()}\n"


def _validate_slug(slug: str) -> None:
    if SLUG_PATTERN.fullmatch(slug) is None:
        message = "slug must use lowercase letters, numbers, and single hyphens"
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
    identifiers: set[str] = set()
    for document_type, rule in schema.types.items():
        suffix = "*/index.md" if document_type in {"project", "area"} else "**/*.md"
        for path in root.glob(f"{rule.root.as_posix()}/{suffix}"):
            if path.name == "README.md":
                continue
            try:
                document = parse_document(path, root=root)
            except (DocumentParseError, OSError, UnicodeError):
                continue
            identifier = document.metadata.get("id")
            if isinstance(identifier, str):
                identifiers.add(identifier)
    return identifiers


def _today() -> date:
    return datetime.now(tz=UTC).astimezone().date()
