"""Repository-root discovery for commands run from nested directories."""

from pathlib import Path

from workrepo.schema import SCHEMA_PATH


def find_repository_root(start: Path) -> Path:
    """Find the nearest repository root at or above *start*."""
    resolved = start.resolve()
    candidate = resolved if resolved.is_dir() else resolved.parent
    for directory in (candidate, *candidate.parents):
        if (directory / SCHEMA_PATH).is_file():
            return directory
    message = (
        f"no work repository found from {resolved}; "
        f"expected {SCHEMA_PATH.as_posix()} in this directory or a parent"
    )
    raise ValueError(message)
