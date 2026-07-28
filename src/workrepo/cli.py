"""Command-line interface for repository maintenance."""

from __future__ import annotations

import argparse
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING

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
from workrepo.doctor import diagnose
from workrepo.gitops import (
    CheckReport,
    check_staged,
    check_worktree,
    hooks_active,
    install_hooks,
)
from workrepo.navigation import ContentFilter, display_row, list_content, search_content
from workrepo.repository import (
    build_index,
    refresh_repository,
    sync_related_links,
)
from workrepo.root import find_repository_root
from workrepo.validation import inbox_report, require_repository

if TYPE_CHECKING:
    from collections.abc import Sequence

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

    return _dispatch(parser, args, root)


def _dispatch(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    root: Path,
) -> int:
    if args.command in {"check", "index", "links", "dashboard", "refresh"}:
        return _dispatch_maintenance(args, root)
    if args.command == "new":
        return _run_new_command(root, args)
    if args.command == "capture":
        return _run_capture(root, args.text, capture_date=args.date)
    if args.command in {"list", "search"}:
        return _run_browse(root, args)
    return _dispatch_auxiliary(parser, args, root)


def _dispatch_auxiliary(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    root: Path,
) -> int:
    if args.command == "inbox":
        return _run_inbox(root, args)
    if args.command == "hooks":
        return _run_hooks(root, args.hooks_command)
    if args.command == "doctor":
        return _run_doctor(root)
    return parser.error(f"unknown command: {args.command}")


def _dispatch_maintenance(args: argparse.Namespace, root: Path) -> int:
    if args.command == "check":
        return _run_check(root, staged=args.staged, strict=args.strict)
    if args.command == "index":
        return _run_index(root)
    if args.command == "links":
        return _run_links(root)
    if args.command == "dashboard":
        return _run_dashboard(root)
    return _run_refresh(root)


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
    check_parser = subparsers.add_parser(
        "check",
        help="validate document structure and metadata",
    )
    check_parser.add_argument(
        "--staged",
        action="store_true",
        help="validate the exact Git index snapshot to be committed",
    )
    check_parser.add_argument(
        "--strict",
        action="store_true",
        help="treat non-blocking warnings as errors",
    )
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
        choices=("log", "meeting", "daily"),
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
        help="synchronize links, indexes, dashboard, and navigation",
    )
    _add_browse_commands(subparsers)
    inbox_parser = subparsers.add_parser(
        "inbox",
        help="inspect and review temporary capture",
    )
    inbox_subparsers = inbox_parser.add_subparsers(
        dest="inbox_command",
        required=True,
    )
    inbox_subparsers.add_parser("status", help="show Inbox backlog health")
    review_parser = inbox_subparsers.add_parser(
        "review",
        help="show the oldest open Inbox items",
    )
    review_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="maximum items to show (default: 20)",
    )
    hooks_parser = subparsers.add_parser(
        "hooks",
        help="manage local repository Git hooks",
    )
    hooks_subparsers = hooks_parser.add_subparsers(
        dest="hooks_command",
        required=True,
    )
    hooks_subparsers.add_parser("install", help="activate managed hooks locally")
    hooks_subparsers.add_parser("status", help="show whether managed hooks are active")
    subparsers.add_parser("doctor", help="diagnose local repository setup")
    return parser


def _add_browse_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    list_parser = subparsers.add_parser(
        "list",
        help="list repository content with explicit filters",
    )
    _add_content_filters(list_parser)
    search_parser = subparsers.add_parser(
        "search",
        help="search titles, IDs, metadata, and Markdown text",
    )
    search_parser.add_argument("query", help="one or more words; every word must match")
    _add_content_filters(search_parser)


def _add_content_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--type",
        dest="document_type",
        choices=(*DOCUMENT_TYPES, "artifact"),
        help="only this content type",
    )
    parser.add_argument("--status", help="only this lifecycle status")
    parser.add_argument("--health", help="only this health value")
    parser.add_argument("--area", dest="area_id", help="only content related to this Area ID")
    parser.add_argument("--group", help="only Areas in this group")
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help="maximum rows (default: 50)",
    )


def _run_check(root: Path, *, staged: bool, strict: bool) -> int:
    try:
        report = check_staged(root) if staged else check_worktree(root)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    return _print_check_report(report, strict=strict)


def _print_check_report(report: CheckReport, *, strict: bool) -> int:
    if report.errors:
        for issue in report.errors:
            print(f"ERROR {issue}")
    for warning in report.warnings:
        print(f"WARNING {warning}")
    if report.errors or (strict and report.warnings):
        count = len(report.errors) + (len(report.warnings) if strict else 0)
        print(f"\n{count} blocking issue(s) found.")
        return 1
    suffix = f" ({len(report.warnings)} warning(s))" if report.warnings else ""
    print(f"Repository is valid{suffix}.")
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
        f"{result.dashboard_path.relative_to(root.resolve())}, "
        f"{result.navigation_path.relative_to(root.resolve())}.",
    )
    return 0


def _run_browse(root: Path, args: argparse.Namespace) -> int:
    try:
        state = require_repository(root)
        filters = ContentFilter(
            document_type=args.document_type,
            status=args.status,
            health=args.health,
            area_id=args.area_id,
            group=args.group,
        )
        items = (
            search_content(state, args.query, filters=filters, limit=args.limit)
            if args.command == "search"
            else list_content(state, filters=filters, limit=args.limit)
        )
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    if not items:
        print("No matching content.")
        return 0
    for item in items:
        print(display_row(item))
    return 0


def _run_inbox(root: Path, args: argparse.Namespace) -> int:
    try:
        report = inbox_report(require_repository(root))
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    if args.inbox_command == "status":
        oldest = (
            f"{report.oldest_age_days} day(s)" if report.oldest_age_days is not None else "none"
        )
        print(f"Open items: {report.open_items}")
        print(f"Overdue items: {report.overdue_items}")
        print(f"Oldest open item: {oldest}")
        print(f"Dated files: {len(report.files)}")
        return 0
    items = [(item.age_days, item.path, text) for item in report.files for text in item.open_items]
    for age, path, text in sorted(items, key=lambda item: (-item[0], item[1]))[: args.limit]:
        print(f"{age:>3}d  {path}: {text}")
    if not items:
        print("Inbox is clear.")
    return 0


def _run_hooks(root: Path, command: str) -> int:
    try:
        if command == "install":
            install_hooks(root)
            print("Managed Git hooks installed.")
            return 0
        active = hooks_active(root)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print("Managed Git hooks are active." if active else "Managed Git hooks are not active.")
    return 0 if active else 1


def _run_doctor(root: Path) -> int:
    diagnostics = diagnose(root)
    for diagnostic in diagnostics:
        label = "OK" if diagnostic.ok else "ERROR"
        print(f"{label:<5} {diagnostic.name}: {diagnostic.detail}")
    return 0 if all(item.ok for item in diagnostics) else 1


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        message = f"invalid ISO date: {value}"
        raise argparse.ArgumentTypeError(message) from error


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        message = "value must be a positive integer"
        raise argparse.ArgumentTypeError(message)
    return parsed


def _package_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"
