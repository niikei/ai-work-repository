"""Stable public facade for repository operations."""

from dataclasses import dataclass
from pathlib import Path

from workrepo.dashboard import generate_dashboard
from workrepo.indexing import INDEX_OUTPUT, build_index
from workrepo.navigation import generate_navigation
from workrepo.relations import sync_related_links
from workrepo.validation import check_repository, read_documents, require_repository


@dataclass(frozen=True, slots=True)
class RefreshResult:
    """Outputs from one atomic-input repository refresh."""

    linked_documents: int
    index_path: Path
    dashboard_path: Path
    navigation_path: Path


def refresh_repository(root: Path) -> RefreshResult:
    """Validate once, then refresh all deterministic repository views."""
    state = require_repository(root)
    linked_documents = sync_related_links(root, state=state)
    index_path = build_index(root, state=state)
    dashboard_path = generate_dashboard(root, state=state)
    navigation_path = generate_navigation(root, state=state)
    return RefreshResult(
        linked_documents=linked_documents,
        index_path=index_path,
        dashboard_path=dashboard_path,
        navigation_path=navigation_path,
    )


__all__ = [
    "INDEX_OUTPUT",
    "RefreshResult",
    "build_index",
    "check_repository",
    "read_documents",
    "refresh_repository",
    "sync_related_links",
]
