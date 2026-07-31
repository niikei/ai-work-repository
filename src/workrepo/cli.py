"""Command-line interface for repository maintenance."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from workrepo.cli_mutations import run_capture, run_lifecycle, run_new_command
from workrepo.cli_parser import build_parser
from workrepo.dashboard import generate_dashboard
from workrepo.doctor import diagnose
from workrepo.gitops import (
    CheckReport,
    check_ref,
    check_staged,
    check_worktree,
    hooks_active,
    install_hooks,
)
from workrepo.navigation import ContentFilter, display_row, list_content, search_content
from workrepo.obsidian import open_document
from workrepo.repository import (
    build_index,
    refresh_repository,
    sync_related_links,
)
from workrepo.review_cli import run_review_context
from workrepo.root import find_repository_root
from workrepo.validation import inbox_report, require_repository

if TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence

COMMAND_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


def main(argv: Sequence[str] | None = None) -> int:
    """Run a repository maintenance command."""
    parser = build_parser()
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
        return run_new_command(root, args)
    if args.command == "capture":
        return run_capture(root, args.text, capture_date=args.date)
    if args.command in {"archive", "restore"}:
        return run_lifecycle(root, args)
    if args.command in {"list", "search", "review-context"}:
        return (
            run_review_context(root, args)
            if args.command == "review-context"
            else _run_browse(root, args)
        )
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
    if args.command == "open":
        return _run_open(root, args.document_id)
    return parser.error(f"unknown command: {args.command}")


def _dispatch_maintenance(args: argparse.Namespace, root: Path) -> int:
    if args.command == "check":
        return _run_check(root, staged=args.staged, ref=args.ref, strict=args.strict)
    if args.command == "index":
        return _run_index(root)
    if args.command == "links":
        return _run_links(root)
    if args.command == "dashboard":
        return _run_dashboard(root)
    return _run_refresh(root)


def _run_check(
    root: Path,
    *,
    staged: bool,
    ref: str | None,
    strict: bool,
) -> int:
    try:
        if ref is not None:
            ref_report = check_ref(root, ref)
            print(f"Git snapshot: {ref_report.commit}")
            report = ref_report.report
        else:
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
            archive_scope=args.archive_scope,
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


def _run_open(root: Path, document_id: str) -> int:
    try:
        open_document(root, document_id)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Opened {document_id} in Obsidian.")
    return 0
