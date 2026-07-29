"""Schema loading for managed work documents."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from workrepo.yamlutil import load_yaml

SCHEMA_PATH = Path(".workspace/schemas/document.schema.yaml")
SUPPORTED_SCHEMA_VERSION = 4


@dataclass(frozen=True, slots=True)
class TypeRule:
    """Placement and field rules for one document type."""

    root: Path
    archive: Path | None
    statuses: frozenset[str]
    required: frozenset[str]
    optional: frozenset[str]
    values: dict[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class ArtifactRule:
    """Placement and field rules for typed artifacts."""

    roots: tuple[Path, ...]
    statuses: frozenset[str]
    kinds: frozenset[str]
    required: frozenset[str]
    optional: frozenset[str]


@dataclass(frozen=True, slots=True)
class Schema:
    """Repository document schema."""

    inbox_root: Path
    templates_root: Path
    archive_root: Path
    required: frozenset[str]
    types: dict[str, TypeRule]
    artifact: ArtifactRule


def load_schema(root: Path) -> Schema:
    """Load and type-check the repository schema."""
    try:
        raw = load_yaml((root / SCHEMA_PATH).read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        message = f"invalid schema YAML: {error}"
        raise ValueError(message) from error
    schema_mapping = _mapping(raw, label="schema")
    version = schema_mapping.get("version")
    if version != SUPPORTED_SCHEMA_VERSION:
        message = f"unsupported schema version {version!r}; expected {SUPPORTED_SCHEMA_VERSION}"
        raise ValueError(message)
    inbox_root = _path(schema_mapping.get("inbox_root"), label="inbox_root")
    templates_root = _path(schema_mapping.get("templates_root"), label="templates_root")
    archive_root = _path(schema_mapping.get("archive_root"), label="archive_root")
    required = frozenset(_string_list(schema_mapping.get("required"), label="required"))
    raw_types = _mapping(schema_mapping.get("types"), label="types")
    type_rules = {
        name: _load_type_rule(name, value)
        for name, value in raw_types.items()
        if isinstance(name, str)
    }
    if len(type_rules) != len(raw_types):
        message = "type names must be strings"
        raise ValueError(message)
    artifact = _load_artifact_rule(schema_mapping.get("artifact"))
    return Schema(
        inbox_root=inbox_root,
        templates_root=templates_root,
        archive_root=archive_root,
        required=required,
        types=type_rules,
        artifact=artifact,
    )


def _load_type_rule(name: str, raw: object) -> TypeRule:
    mapping = _mapping(raw, label=f"type {name}")
    root = mapping.get("root")
    if not isinstance(root, str) or not root:
        message = f"type {name} must define a non-empty root"
        raise ValueError(message)
    archive_raw = mapping.get("archive")
    archive = (
        None
        if archive_raw is None
        else _safe_path(_text(archive_raw, label=f"{name}.archive"), label=f"{name}.archive")
    )
    statuses = frozenset(_string_list(mapping.get("statuses"), label=f"{name}.statuses"))
    required = frozenset(
        _string_list(mapping.get("required", []), label=f"{name}.required"),
    )
    optional = frozenset(
        _string_list(mapping.get("optional", []), label=f"{name}.optional"),
    )
    values = _load_values(mapping.get("values", {}), label=f"{name}.values")
    return TypeRule(
        root=_safe_path(root, label=f"{name}.root"),
        archive=archive,
        statuses=statuses,
        required=required,
        optional=optional,
        values=values,
    )


def _load_artifact_rule(raw: object) -> ArtifactRule:
    mapping = _mapping(raw, label="artifact")
    roots = tuple(
        _safe_path(value, label="artifact.roots")
        for value in _string_list(mapping.get("roots"), label="artifact.roots")
    )
    if not roots:
        message = "artifact.roots must not be empty"
        raise ValueError(message)
    return ArtifactRule(
        roots=roots,
        statuses=frozenset(
            _string_list(mapping.get("statuses"), label="artifact.statuses"),
        ),
        kinds=frozenset(_string_list(mapping.get("kinds"), label="artifact.kinds")),
        required=frozenset(
            _string_list(mapping.get("required"), label="artifact.required"),
        ),
        optional=frozenset(
            _string_list(mapping.get("optional", []), label="artifact.optional"),
        ),
    )


def _load_values(raw: object, *, label: str) -> dict[str, frozenset[str]]:
    mapping = _mapping(raw, label=label)
    values: dict[str, frozenset[str]] = {}
    for field, allowed in mapping.items():
        if not isinstance(field, str):
            message = f"{label} field names must be strings"
            raise TypeError(message)
        values[field] = frozenset(
            _string_list(allowed, label=f"{label}.{field}"),
        )
    return values


def _mapping(raw: object, *, label: str) -> dict[object, object]:
    if not isinstance(raw, dict):
        message = f"{label} must be a mapping"
        raise TypeError(message)
    return raw


def _string_list(raw: object, *, label: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        message = f"{label} must be a list of strings"
        raise ValueError(message)
    return raw


def _path(raw: object, *, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        message = f"{label} must be a non-empty path"
        raise ValueError(message)
    return _safe_path(raw, label=label)


def _text(raw: object, *, label: str) -> str:
    if not isinstance(raw, str) or not raw:
        message = f"{label} must be a non-empty string"
        raise ValueError(message)
    return raw


def _safe_path(raw: str, *, label: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        message = f"{label} must stay inside the repository"
        raise ValueError(message)
    return path
