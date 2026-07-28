"""Schema loading for managed work documents."""

from dataclasses import dataclass
from pathlib import Path

import yaml

SCHEMA_PATH = Path(".workspace/schemas/document.schema.yaml")


@dataclass(frozen=True, slots=True)
class TypeRule:
    """Placement and field rules for one document type."""

    root: Path
    statuses: frozenset[str]
    required: frozenset[str]


@dataclass(frozen=True, slots=True)
class Schema:
    """Repository document schema."""

    required: frozenset[str]
    types: dict[str, TypeRule]


def load_schema(root: Path) -> Schema:
    """Load and type-check the repository schema."""
    raw: object = yaml.safe_load((root / SCHEMA_PATH).read_text(encoding="utf-8"))
    schema_mapping = _mapping(raw, label="schema")
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
    return Schema(required=required, types=type_rules)


def _load_type_rule(name: str, raw: object) -> TypeRule:
    mapping = _mapping(raw, label=f"type {name}")
    root = mapping.get("root")
    if not isinstance(root, str) or not root:
        message = f"type {name} must define a non-empty root"
        raise ValueError(message)
    statuses = frozenset(_string_list(mapping.get("statuses"), label=f"{name}.statuses"))
    required = frozenset(
        _string_list(mapping.get("required", []), label=f"{name}.required"),
    )
    return TypeRule(root=Path(root), statuses=statuses, required=required)


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
