"""Markdown link and external URL security validation."""

from pathlib import Path
from urllib.parse import SplitResult, parse_qsl, unquote, urlsplit

from workrepo.generated import remove_related_block
from workrepo.markdown import inspect_markdown
from workrepo.models import Issue

IGNORED_MARKDOWN_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".workspace",
    },
)
GENERATED_MARKDOWN_FILES = frozenset({"DASHBOARD.md", "NAVIGATION.md"})
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "key",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
        "x-amz-signature",
    },
)


def validate_markdown_links(root: Path) -> list[Issue]:
    """Return issues for broken, unsafe, or malformed Markdown links."""
    issues: list[Issue] = []
    for path in _markdown_paths(root):
        relative_path = path.relative_to(root)
        try:
            source = path.read_text(encoding="utf-8")
            source = remove_related_block(source, path=relative_path)
            links = inspect_markdown(source).links
        except (OSError, UnicodeError, ValueError) as error:
            issues.append(Issue(relative_path, str(error)))
            continue
        issues.extend(
            issue
            for link in links
            if (issue := _validate_markdown_link(root, path, link.target, link.line)) is not None
        )
    return issues


def url_security_messages(parsed: SplitResult) -> list[str]:
    """Return security findings for a parsed external URL."""
    messages: list[str] = []
    if parsed.username is not None or parsed.password is not None:
        messages.append("url must not contain embedded credentials")
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
    sensitive = sorted(query_keys & SENSITIVE_QUERY_KEYS)
    if sensitive:
        messages.append(f"url contains sensitive query parameter: {', '.join(sensitive)}")
    return messages


def _markdown_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.relative_to(root).as_posix() not in GENERATED_MARKDOWN_FILES
        and not set(path.relative_to(root).parts) & IGNORED_MARKDOWN_DIRECTORIES
    )


def _validate_markdown_link(
    root: Path,
    source: Path,
    target: str,
    line: int,
) -> Issue | None:
    try:
        parsed = urlsplit(target)
    except ValueError:
        return Issue(source.relative_to(root), f"line {line}: invalid link: {target}")
    if parsed.scheme in {"http", "https"}:
        return _external_markdown_issue(root, source, parsed, line)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None

    decoded_path = unquote(parsed.path)
    candidate = (
        root / decoded_path.removeprefix("/")
        if decoded_path.startswith("/")
        else source.parent / decoded_path
    ).resolve()
    if not candidate.is_relative_to(root):
        return Issue(source.relative_to(root), f"line {line}: link escapes repository: {target}")
    if candidate.exists() or (not candidate.suffix and candidate.with_suffix(".md").exists()):
        return None
    return Issue(source.relative_to(root), f"line {line}: linked path does not exist: {target}")


def _external_markdown_issue(
    root: Path,
    source: Path,
    parsed: SplitResult,
    line: int,
) -> Issue | None:
    if parsed.hostname is None:
        return Issue(source.relative_to(root), f"line {line}: external URL has no hostname")
    messages = url_security_messages(parsed)
    if not messages:
        return None
    return Issue(source.relative_to(root), f"line {line}: {messages[0]}")
