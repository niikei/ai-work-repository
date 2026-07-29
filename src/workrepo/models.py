"""Core immutable values used by repository operations."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Artifact:
    """A Markdown artifact nested below a Project or Area."""

    path: Path
    title: str
    metadata: dict[str, object]
    parent_id: str | None

    @property
    def typed(self) -> bool:
        """Return whether the artifact declares managed metadata."""
        return bool(self.metadata)


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
        return f"{self.path.as_posix()}: {self.message}"


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    """A local or external link found in rendered Markdown content."""

    target: str
    line: int
    label: str


ContentDocument = Document | Artifact
