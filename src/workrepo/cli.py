"""Command-line interface for repository maintenance."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from workrepo.repository import build_index, check_repository, sync_related_links


def main(argv: Sequence[str] | None = None) -> int:
    """Run a repository maintenance command."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = args.root

    if args.command == "check":
        return _run_check(root)
    if args.command == "index":
        return _run_index(root)
    if args.command == "links":
        return _run_links(root)
    return parser.error(f"unknown command: {args.command}")


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
