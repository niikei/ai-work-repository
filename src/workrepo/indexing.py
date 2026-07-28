"""Deterministic machine-readable index generation."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from workrepo.calendar import work_week
from workrepo.models import Artifact, ContentDocument, Document
from workrepo.review import next_review
from workrepo.state import RepositoryState
from workrepo.validation import require_repository

INDEX_OUTPUT = Path(".workspace/indexes/documents.json")


def build_index(root: Path, *, state: RepositoryState | None = None) -> Path:
    """Validate the repository and write its entity and artifact index."""
    repository_state = state or require_repository(root)
    repository_root = repository_state.root
    documents = repository_state.documents
    artifacts = repository_state.artifacts
    backlinks = _backlinks([*documents, *artifacts])
    entries = [
        *(_entity_entry(document, backlinks) for document in documents),
        *(_artifact_entry(artifact, backlinks) for artifact in artifacts),
    ]
    payload = {
        "version": 3,
        "documents": sorted(entries, key=lambda item: str(item["path"])),
    }
    output = repository_root / INDEX_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    return output


def _entity_entry(
    document: Document,
    backlinks: dict[str, list[str]],
) -> dict[str, object]:
    metadata = {key: _json_value(value) for key, value in sorted(document.metadata.items())}
    return {
        "kind": "entity",
        "id": metadata["id"],
        "type": metadata["type"],
        "title": document.title,
        "path": document.path.as_posix(),
        "metadata": metadata,
        "derived": {
            **_derived_values(document),
            "backlinks": backlinks.get(str(metadata["id"]), []),
        },
    }


def _artifact_entry(
    artifact: Artifact,
    backlinks: dict[str, list[str]],
) -> dict[str, object]:
    metadata = {key: _json_value(value) for key, value in sorted(artifact.metadata.items())}
    artifact_id = metadata.get("id")
    return {
        "kind": "artifact",
        "id": artifact_id,
        "type": "artifact",
        "title": artifact.title,
        "path": artifact.path.as_posix(),
        "metadata": metadata,
        "derived": {
            "parent_id": artifact.parent_id,
            "backlinks": backlinks.get(str(artifact_id), []) if artifact_id is not None else [],
        },
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
    document_type = document.metadata.get("type")
    if document_type == "log":
        log_date = _date_value(document.metadata.get("date"))
        if log_date is None:
            return {}
        week = work_week(log_date)
        return {
            "iso_week": week.iso_label,
            "week_start": week.start.isoformat(),
        }
    if document_type == "area":
        last_reviewed = _date_value(document.metadata.get("last_reviewed"))
        cycle = document.metadata.get("review_cycle")
        if last_reviewed is None or not isinstance(cycle, str):
            return {}
        review_date = next_review(last_reviewed, cycle)
        return {
            "next_review": review_date.isoformat(),
            "review_overdue": review_date < datetime.now(tz=UTC).astimezone().date(),
        }
    return {}


def _backlinks(content: list[ContentDocument]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for document in content:
        source_id = document.metadata.get("id")
        related = document.metadata.get("related")
        if not isinstance(source_id, str) or not isinstance(related, list):
            continue
        for target_id in related:
            if isinstance(target_id, str):
                result.setdefault(target_id, []).append(source_id)
    return {target_id: sorted(source_ids) for target_id, source_ids in result.items()}


def _date_value(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
