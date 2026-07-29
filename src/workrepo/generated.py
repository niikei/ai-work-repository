"""Safe handling of generated Markdown sections."""

import re
from pathlib import Path

RELATED_START = "<!-- workrepo:related:start -->"
RELATED_END = "<!-- workrepo:related:end -->"
RELATED_BLOCK_PATTERN = re.compile(
    rf"\n*## Related documents\n\n{re.escape(RELATED_START)}\n"
    rf".*?{re.escape(RELATED_END)}\n?",
    flags=re.DOTALL,
)


def replace_related_block(source: str, replacement: str, *, path: Path) -> str:
    """Replace one valid generated relationship block."""
    match = _related_match(source, path)
    if match is not None:
        updated = RELATED_BLOCK_PATTERN.sub(replacement, source, count=1)
        return f"{updated.rstrip()}\n"
    if not replacement:
        return source
    return f"{source.rstrip()}{replacement}"


def remove_related_block(source: str, *, path: Path) -> str:
    """Remove generated links before validating user-authored links."""
    match = _related_match(source, path)
    if match is None:
        return source
    blank_lines = "\n" * match.group().count("\n")
    return f"{source[: match.start()]}{blank_lines}{source[match.end() :]}"


def _related_match(source: str, path: Path) -> re.Match[str] | None:
    start_count = source.count(RELATED_START)
    end_count = source.count(RELATED_END)
    match = RELATED_BLOCK_PATTERN.search(source)
    if start_count != end_count or start_count > 1 or (start_count == 1 and match is None):
        message = f"{path.as_posix()}: generated related document markers are malformed"
        raise ValueError(message)
    return match
