"""Core immutable values used by repository operations."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Artifact:
    """A Project or Area Markdown artifact without entity frontmatter."""

    path: Path
    title: str


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


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    """A local or external link found in rendered Markdown content."""

    target: str
    line: int
