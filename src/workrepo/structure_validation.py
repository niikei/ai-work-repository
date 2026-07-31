"""Repository file and directory structure validation."""

import unicodedata
from pathlib import Path

import yaml

from workrepo.creation_validation import WINDOWS_RESERVED_NAMES
from workrepo.models import Issue
from workrepo.state import RepositoryState
from workrepo.yamlutil import load_yaml

IGNORED_REPOSITORY_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".workspace",
    },
)
ALLOWED_ROOT_MARKDOWN_FILES = frozenset(
    {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "DASHBOARD.md",
        "NAVIGATION.md",
        "README.md",
        "SECURITY.md",
    },
)
INDEX_DOCUMENT_REMAINDER_PARTS = 2


def validate_repository_structure(state: RepositoryState) -> list[Issue]:
    """Return file and layout issues for a discovered repository."""
    return [
        *_validate_root_markdown(state.root),
        *_validate_index_layout(state),
        *_validate_repository_files(state),
        *_validate_archive_layout(state),
    ]


def _validate_repository_files(state: RepositoryState) -> list[Issue]:
    issues: list[Issue] = []
    paths = [
        path
        for path in state.root.rglob("*")
        if path.is_file() and not _is_ignored(path.relative_to(state.root))
    ]
    normalized_paths: dict[str, list[Path]] = {}
    for path in paths:
        relative = path.relative_to(state.root)
        normalized_paths.setdefault(relative.as_posix().casefold(), []).append(relative)
        issues.extend(_validate_portable_path(relative, state.policy.files.max_path_length))
        try:
            size = path.stat().st_size
        except OSError as error:
            issues.append(Issue(relative, f"cannot inspect file: {error}"))
            continue
        if size > state.policy.files.max_attachment_bytes:
            issues.append(
                Issue(
                    relative,
                    "file exceeds configured size limit: "
                    f"{size} > {state.policy.files.max_attachment_bytes} bytes",
                ),
            )
        if path.suffix.casefold() in {".base", ".yaml", ".yml"}:
            issues.extend(_validate_yaml_file(path, relative))
        if path.is_symlink():
            try:
                path.resolve().relative_to(state.root)
            except ValueError:
                issues.append(Issue(relative, "symbolic link points outside the repository"))
    issues.extend(
        Issue(path, "path differs from another path only by letter case")
        for duplicates in normalized_paths.values()
        if len(duplicates) > 1
        for path in duplicates
    )
    return issues


def _validate_root_markdown(root: Path) -> list[Issue]:
    return [
        Issue(path.relative_to(root), "root Markdown must be moved under docs/")
        for path in sorted(root.glob("*.md"))
        if path.name not in ALLOWED_ROOT_MARKDOWN_FILES
    ]


def _validate_index_layout(state: RepositoryState) -> list[Issue]:
    issues: list[Issue] = []
    for document_type in ("project", "area"):
        relative_root = state.schema.types[document_type].root
        root = state.root / relative_root
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("index.md")):
            remainder = path.relative_to(root)
            if len(remainder.parts) != INDEX_DOCUMENT_REMAINDER_PARTS:
                issues.append(
                    Issue(
                        path.relative_to(state.root),
                        f"{document_type} index must be located at "
                        f"{relative_root.as_posix()}/<slug>/index.md",
                    ),
                )
    for document in state.documents:
        if document.metadata.get("type") not in {"project", "area"}:
            continue
        directory = state.root / document.path.parent
        issues.extend(
            Issue(
                sibling.relative_to(state.root),
                f"Markdown beside {document.path.name} must be moved into a subdirectory",
            )
            for sibling in sorted(directory.glob("*.md"))
            if sibling.name != document.path.name
        )
    return issues


def _validate_archive_layout(state: RepositoryState) -> list[Issue]:
    archive = state.root / state.schema.archive_root
    if not archive.is_dir():
        return []
    known = {
        *(document.path for document in state.documents),
        *(artifact.path for artifact in state.artifacts),
    }
    return [
        Issue(relative, "document is not in a schema-defined archive location")
        for path in sorted(archive.rglob("*.md"))
        if path.name != "README.md" and (relative := path.relative_to(state.root)) not in known
    ]


def _validate_portable_path(path: Path, max_length: int) -> list[Issue]:
    issues: list[Issue] = []
    if len(path.as_posix()) > max_length:
        issues.append(Issue(path, f"path exceeds configured length limit: {max_length}"))
    for component in path.parts:
        if component != unicodedata.normalize("NFC", component):
            issues.append(Issue(path, "path must use Unicode NFC normalization"))
        if component.endswith((" ", ".")):
            issues.append(Issue(path, "path component must not end with a space or period"))
        if Path(component).stem.casefold() in WINDOWS_RESERVED_NAMES:
            issues.append(Issue(path, f"path component is reserved on Windows: {component}"))
    return issues


def _validate_yaml_file(path: Path, relative: Path) -> list[Issue]:
    try:
        load_yaml(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        return [Issue(relative, f"invalid YAML: {error}")]
    return []


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_REPOSITORY_DIRECTORIES for part in path.parts)
