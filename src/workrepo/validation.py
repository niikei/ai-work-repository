"""Repository-wide metadata, structure, and Markdown-link validation."""

from collections.abc import Iterable
from datetime import date
from pathlib import Path

from workrepo.clock import current_date
from workrepo.content_validation import (
    identifier as _identifier,
)
from workrepo.content_validation import (
    related_ids as _related_ids,
)
from workrepo.content_validation import (
    validate_content,
)
from workrepo.inbox import InboxReport, inspect_inbox
from workrepo.link_validation import validate_markdown_links
from workrepo.models import ContentDocument, Document, Issue
from workrepo.state import RepositoryState, discover_repository
from workrepo.structure_validation import validate_repository_structure


def check_repository(root: Path) -> list[Issue]:
    """Return every validation issue found in a work repository."""
    _, issues = inspect_repository(root)
    return issues


def inspect_repository(root: Path) -> tuple[RepositoryState, list[Issue]]:
    """Return one parsed state and all issues found in that state."""
    state, issues = discover_repository(root)
    issues.extend(
        validate_content(
            list(state.documents),
            list(state.artifacts),
            state.schema,
            today=current_date(state.policy.timezone),
        ),
    )
    issues.extend(validate_markdown_links(state.root))
    issues.extend(validate_repository_structure(state))
    issues.extend(inbox_report(state).errors)
    return state, sorted(issues)


def inbox_report(
    state: RepositoryState,
    *,
    today: date | None = None,
) -> InboxReport:
    """Return Inbox health using the same state and policy as validation."""
    effective_today = today or current_date(state.policy.timezone)
    return inspect_inbox(
        state.root,
        state.schema.inbox_root,
        state.policy.inbox,
        today=effective_today,
    )


def repository_warnings(state: RepositoryState) -> list[Issue]:
    """Return non-blocking findings for a valid or invalid repository state."""
    return [*inbox_report(state).warnings, *_empty_directory_warnings(state)]


def _empty_directory_warnings(state: RepositoryState) -> list[Issue]:
    roots = (state.schema.types["project"].root, state.schema.types["area"].root)
    warnings: list[Issue] = []
    for relative_root in roots:
        root = state.root / relative_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_dir():
                continue
            try:
                empty = next(path.iterdir(), None) is None
            except OSError:
                continue
            if empty:
                warnings.append(
                    Issue(
                        path.relative_to(state.root),
                        "empty directory can be removed",
                    ),
                )
    return sorted(warnings)


def require_repository(root: Path) -> RepositoryState:
    """Return a valid parsed state or raise with every validation issue."""
    state, issues = inspect_repository(root)
    if issues:
        details = "\n".join(str(issue) for issue in issues)
        message = f"repository validation failed:\n{details}"
        raise ValueError(message)
    return state


def read_documents(root: Path) -> list[Document]:
    """Read every valid entity document from a repository."""
    return list(require_repository(root).documents)


def identifier(document: ContentDocument) -> str | None:
    """Return a document's string identifier when present."""
    return _identifier(document)


def related_ids(document: ContentDocument) -> Iterable[str]:
    """Yield well-formed relationship values for a document."""
    return _related_ids(document)
