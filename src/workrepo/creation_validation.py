"""Validation helpers for safe document creation."""

import re
from pathlib import Path

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOG_DATE_PREFIX_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:-|$)")
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


def validate_slug(slug: str) -> None:
    """Require a portable lowercase slug."""
    if len(slug) > MAX_SLUG_LENGTH:
        message = f"slug must be at most {MAX_SLUG_LENGTH} characters"
        raise ValueError(message)
    if SLUG_PATTERN.fullmatch(slug) is None:
        message = "slug must use lowercase letters, numbers, and single hyphens"
        raise ValueError(message)
    if slug.casefold() in WINDOWS_RESERVED_NAMES:
        message = f"slug is reserved on Windows: {slug}"
        raise ValueError(message)


def validate_log_slug(document_type: str, slug: str) -> None:
    """Reject a redundant date prefix in log slugs."""
    if document_type == "log" and LOG_DATE_PREFIX_PATTERN.match(slug) is not None:
        message = (
            "log slug must omit the date because it is added automatically; "
            "use 'daily', not '2026-07-30-daily'"
        )
        raise ValueError(message)


def normalize_title(title: str) -> str:
    """Normalize whitespace and require a non-empty title."""
    normalized = " ".join(title.split())
    if not normalized:
        message = "title must not be empty"
        raise ValueError(message)
    return normalized


def ensure_path_available(destination: Path, root: Path) -> None:
    """Require a new, case-portable path inside the repository."""
    ensure_inside_repository(destination, root)
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


def ensure_inside_repository(destination: Path, root: Path) -> None:
    """Require a destination that resolves below the repository root."""
    if destination.resolve().is_relative_to(root.resolve()):
        return
    message = f"destination escapes repository: {destination}"
    raise ValueError(message)
