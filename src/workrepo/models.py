"""Core immutable values used by repository operations."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Document:
    """A Markdown document with parsed frontmatter and its canonical title."""

    path: Path
    title: str
    metadata: dict[str, object]


@dataclass(frozen=True, slots=True, order=True)
class Issue:
    """A validation problem tied to a repository-relative path."""

    path: Path
    message: str

    def __str__(self) -> str:
        """Render an issue for command-line output."""
        return f"{self.path}: {self.message}"
