"""CommonMark inspection used for titles and local-link validation."""

from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from workrepo.models import MarkdownLink

_PARSER = MarkdownIt("commonmark")


@dataclass(frozen=True, slots=True)
class MarkdownInfo:
    """Structural information extracted from rendered Markdown."""

    headings: tuple[str, ...]
    links: tuple[MarkdownLink, ...]


def inspect_markdown(source: str) -> MarkdownInfo:
    """Extract H1 headings and links while naturally ignoring code blocks."""
    tokens = _PARSER.parse(source)
    headings: list[str] = []
    links: list[MarkdownLink] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1":
            headings.append(_heading_text(tokens, index))
        if token.type == "inline":
            links.extend(_inline_links(token))
    return MarkdownInfo(headings=tuple(headings), links=tuple(links))


def _heading_text(tokens: list[Token], opening_index: int) -> str:
    content_index = opening_index + 1
    if content_index >= len(tokens):
        return ""
    content = tokens[content_index]
    return content.content.strip() if content.type == "inline" else ""


def _inline_links(token: Token) -> list[MarkdownLink]:
    if token.children is None:
        return []
    line = token.map[0] + 1 if token.map is not None else 1
    links: list[MarkdownLink] = []
    for index, child in enumerate(token.children):
        attribute = "href" if child.type == "link_open" else "src"
        if child.type not in {"link_open", "image"}:
            continue
        target = child.attrGet(attribute)
        if isinstance(target, str):
            label = (
                child.content.strip()
                if child.type == "image"
                else _link_label(token.children, index)
            )
            links.append(MarkdownLink(target=target, line=line, label=label))
    return links


def _link_label(children: list[Token], opening_index: int) -> str:
    parts: list[str] = []
    for child in children[opening_index + 1 :]:
        if child.type == "link_close":
            break
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
    return "".join(parts).strip()
