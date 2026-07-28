"""Command-line interface for repository maintenance."""

import argparse
from collections.abc import Sequence
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from workrepo.creation import (
    ARTIFACT_DIRECTORIES,
    DOCUMENT_TYPES,
    ArtifactRequest,
    CreateRequest,
    capture_inbox,
    create_artifact,
    create_document,
)
from workrepo.dashboard import generate_dashboard
from workrepo.repository import (
    build_index,
    check_repository,
    refresh_repository,
    sync_related_links,
)
from workrepo.root import find_repository_root

PACKAGE_NAME = "ai-work-repository"
COMMAND_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


def main(argv: Sequence[str] | None = None) -> int:
    """Run a repository maintenance command."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        root = find_repository_root(args.root or Path.cwd())
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1

    if args.command == "check":
        result = _run_check(root)
    elif args.command == "index":
        result = _run_index(root)
    elif args.command == "links":
        result = _run_links(root)
    elif args.command == "new":
        result = _run_new_command(root, args)
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
        help="repository root or a path inside it (default: auto-detect)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
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
        help="create an entity or typed artifact from a repository template",
    )
    new_parser.add_argument("document_type", choices=(*DOCUMENT_TYPES, "artifact"))
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
        "--parent",
        metavar="ID",
        help="owning Project or Area ID (required for artifact)",
    )
    new_parser.add_argument(
        "--kind",
        choices=tuple(ARTIFACT_DIRECTORIES),
        help="artifact kind (required for artifact)",
    )
    new_parser.add_argument(
        "--template",
        choices=("log", "meeting"),
        help="content template for a log (default: log)",
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
    try:
        issues = check_repository(root)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
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
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Index written to {output.relative_to(root.resolve())}.")
    return 0


def _run_links(root: Path) -> int:
    try:
        changed = sync_related_links(root)
    except COMMAND_ERRORS as error:
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
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Created {path.relative_to(root.resolve())}.")
    return 0


def _run_new_command(root: Path, args: argparse.Namespace) -> int:
    if args.document_type == "artifact":
        if args.parent is None or args.kind is None:
            print("ERROR artifact requires --parent and --kind")
            return 1
        if args.template is not None:
            print("ERROR --template is only valid for log")
            return 1
        try:
            path = create_artifact(
                root,
                ArtifactRequest(
                    slug=args.slug,
                    title=args.title,
                    parent_id=args.parent,
                    kind=args.kind,
                    related=tuple(args.related),
                    document_date=args.date,
                ),
            )
        except COMMAND_ERRORS as error:
            print(f"ERROR {error}")
            return 1
        print(f"Created {path.relative_to(root.resolve())}.")
        return 0
    if args.parent is not None or args.kind is not None:
        print("ERROR --parent and --kind are only valid for artifact")
        return 1
    return _run_new(
        root,
        CreateRequest(
            document_type=args.document_type,
            slug=args.slug,
            title=args.title,
            related=tuple(args.related),
            document_date=args.date,
            template_name=args.template,
        ),
    )


def _run_capture(root: Path, text: str, *, capture_date: date | None) -> int:
    try:
        path = capture_inbox(root, text, capture_date=capture_date)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Captured in {path.relative_to(root.resolve())}.")
    return 0


def _run_dashboard(root: Path) -> int:
    try:
        path = generate_dashboard(root)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Dashboard written to {path.relative_to(root.resolve())}.")
    return 0


def _run_refresh(root: Path) -> int:
    try:
        result = refresh_repository(root)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(
        "Repository refreshed: "
        f"{result.linked_documents} linked document(s), "
        f"{result.index_path.relative_to(root.resolve())}, "
        f"{result.dashboard_path.relative_to(root.resolve())}.",
    )
    return 0


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        message = f"invalid ISO date: {value}"
        raise argparse.ArgumentTypeError(message) from error


def _package_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"
