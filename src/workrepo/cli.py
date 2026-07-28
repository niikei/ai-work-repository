"""Command-line interface for repository maintenance."""

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from workrepo.creation import (
    DOCUMENT_TYPES,
    CreateRequest,
    capture_inbox,
    create_document,
)
from workrepo.dashboard import generate_dashboard
from workrepo.repository import build_index, check_repository, sync_related_links


def main(argv: Sequence[str] | None = None) -> int:
    """Run a repository maintenance command."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = args.root

    if args.command == "check":
        result = _run_check(root)
    elif args.command == "index":
        result = _run_index(root)
    elif args.command == "links":
        result = _run_links(root)
    elif args.command == "new":
        result = _run_new(
            root,
            CreateRequest(
                document_type=args.document_type,
                slug=args.slug,
                title=args.title,
                related=tuple(args.related),
                document_date=args.date,
            ),
        )
    elif args.command == "capture":
        result = _run_capture(root, args.text, capture_date=args.date)
    elif args.command == "dashboard":
        result = _run_dashboard(root)
    elif args.command == "refresh":
        result = _run_refresh(root)
    else:
        return parser.error(f"unknown command: {args.command}")
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workrepo",
        description="Validate and index an AI-ready work repository.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="validate document structure and metadata")
    subparsers.add_parser("index", help="validate and generate the JSON document index")
    subparsers.add_parser(
        "links",
        help="synchronize Markdown links from canonical related IDs",
    )
    new_parser = subparsers.add_parser(
        "new",
        help="create an entity document from a repository template",
    )
    new_parser.add_argument("document_type", choices=DOCUMENT_TYPES)
    new_parser.add_argument("slug", help="stable lowercase name used in the ID and path")
    new_parser.add_argument("--title", required=True, help="canonical H1 title")
    new_parser.add_argument(
        "--related",
        action="append",
        default=[],
        metavar="ID",
        help="related entity ID; repeat for multiple relationships",
    )
    new_parser.add_argument(
        "--date",
        type=_iso_date,
        help="document date in YYYY-MM-DD format (default: today)",
    )
    capture_parser = subparsers.add_parser(
        "capture",
        help="append a short item to the dated Inbox file",
    )
    capture_parser.add_argument("text", help="text to capture")
    capture_parser.add_argument(
        "--date",
        type=_iso_date,
        help="capture date in YYYY-MM-DD format (default: today)",
    )
    subparsers.add_parser(
        "dashboard",
        help="generate the human-readable current-state dashboard",
    )
    subparsers.add_parser(
        "refresh",
        help="synchronize links, machine index, and dashboard",
    )
    return parser


def _run_check(root: Path) -> int:
    issues = check_repository(root)
    if issues:
        for issue in issues:
            print(f"ERROR {issue}")
        print(f"\n{len(issues)} issue(s) found.")
        return 1
    print("Repository is valid.")
    return 0


def _run_index(root: Path) -> int:
    try:
        output = build_index(root)
    except ValueError as error:
        print(f"ERROR {error}")
        return 1
    print(f"Index written to {output.relative_to(root.resolve())}.")
    return 0


def _run_links(root: Path) -> int:
    try:
        changed = sync_related_links(root)
    except ValueError as error:
        print(f"ERROR {error}")
        return 1
    print(f"Related links synchronized; {changed} document(s) changed.")
    return 0


def _run_new(
    root: Path,
    request: CreateRequest,
) -> int:
    try:
        path = create_document(root, request)
    except (OSError, ValueError) as error:
        print(f"ERROR {error}")
        return 1
    print(f"Created {path.relative_to(root.resolve())}.")
    return 0


def _run_capture(root: Path, text: str, *, capture_date: date | None) -> int:
    try:
        path = capture_inbox(root, text, capture_date=capture_date)
    except (OSError, ValueError) as error:
        print(f"ERROR {error}")
        return 1
    print(f"Captured in {path.relative_to(root.resolve())}.")
    return 0


def _run_dashboard(root: Path) -> int:
    try:
        path = generate_dashboard(root)
    except (OSError, ValueError) as error:
        print(f"ERROR {error}")
        return 1
    print(f"Dashboard written to {path.relative_to(root.resolve())}.")
    return 0


def _run_refresh(root: Path) -> int:
    try:
        changed = sync_related_links(root)
        index_path = build_index(root)
        dashboard_path = generate_dashboard(root)
    except (OSError, ValueError) as error:
        print(f"ERROR {error}")
        return 1
    print(
        "Repository refreshed: "
        f"{changed} linked document(s), "
        f"{index_path.relative_to(root.resolve())}, "
        f"{dashboard_path.relative_to(root.resolve())}.",
    )
    return 0


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        message = f"invalid ISO date: {value}"
        raise argparse.ArgumentTypeError(message) from error
