"""One-pass discovery state shared by repository operations."""

from dataclasses import dataclass
from pathlib import Path

from workrepo.discovery import discover_artifacts, discover_documents
from workrepo.models import Artifact, Document, Issue
from workrepo.schema import Schema, load_schema


@dataclass(frozen=True, slots=True)
class RepositoryState:
    """Parsed repository content that has not changed on disk."""

    root: Path
    schema: Schema
    documents: tuple[Document, ...]
    artifacts: tuple[Artifact, ...]


def discover_repository(root: Path) -> tuple[RepositoryState, list[Issue]]:
    """Load the schema and parse managed content exactly once."""
    repository_root = root.resolve()
    schema = load_schema(repository_root)
    documents, document_issues = discover_documents(repository_root, schema)
    artifacts, artifact_issues = discover_artifacts(
        repository_root,
        schema,
        documents,
    )
    state = RepositoryState(
        root=repository_root,
        schema=schema,
        documents=tuple(documents),
        artifacts=tuple(artifacts),
    )
    return state, [*document_issues, *artifact_issues]
