"""Deterministic machine-readable index generation."""

import json
from datetime import date
from pathlib import Path

from workrepo.calendar import work_week
from workrepo.discovery import discover_artifacts, discover_documents
from workrepo.models import Artifact, Document
from workrepo.schema import load_schema
from workrepo.validation import check_repository

INDEX_OUTPUT = Path(".workspace/indexes/documents.json")


def build_index(root: Path) -> Path:
    """Validate the repository and write its entity and artifact index."""
    repository_root = root.resolve()
    issues = check_repository(repository_root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"cannot build index while validation issues exist:\n{details}"
        raise ValueError(message)

    schema = load_schema(repository_root)
    documents, parse_issues = discover_documents(repository_root, schema)
    if parse_issues:
        message = "documents changed while building the index"
        raise RuntimeError(message)
    artifacts, artifact_issues = discover_artifacts(repository_root, schema, documents)
    if artifact_issues:
        message = "artifacts changed while building the index"
        raise RuntimeError(message)
    entries = [
        *(_entity_entry(document) for document in documents),
        *(_artifact_entry(artifact) for artifact in artifacts),
    ]
    payload = {
        "version": 2,
        "documents": sorted(entries, key=lambda item: str(item["path"])),
    }
    output = repository_root / INDEX_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    return output


def _entity_entry(document: Document) -> dict[str, object]:
    metadata = {
        key: _json_value(value)
        for key, value in sorted(document.metadata.items())
    }
    return {
        "kind": "entity",
        "id": metadata["id"],
        "type": metadata["type"],
        "title": document.title,
        "path": document.path.as_posix(),
        "metadata": metadata,
        "derived": _derived_values(document),
    }


def _artifact_entry(artifact: Artifact) -> dict[str, object]:
    return {
        "kind": "artifact",
        "id": None,
        "type": "artifact",
        "title": artifact.title,
        "path": artifact.path.as_posix(),
        "metadata": {},
        "derived": {},
    }


def _json_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _derived_values(document: Document) -> dict[str, object]:
    if document.metadata.get("type") != "log":
        return {}
    log_date = _date_value(document.metadata.get("date"))
    if log_date is None:
        return {}
    week = work_week(log_date)
    return {
        "iso_week": week.iso_label,
        "week_start": week.start.isoformat(),
    }


def _date_value(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
