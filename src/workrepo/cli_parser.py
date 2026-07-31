"""Argument parser construction for the workrepo CLI."""

from __future__ import annotations

import argparse
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from workrepo.creation import ARTIFACT_DIRECTORIES, DOCUMENT_TYPES

PACKAGE_NAME = "ai-work-repository"


def build_parser() -> argparse.ArgumentParser:
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
    check_source = check_parser.add_mutually_exclusive_group()
    check_source.add_argument(
        "--staged",
        action="store_true",
        help="validate the exact Git index snapshot to be committed",
    )
    check_source.add_argument(
        "--ref",
        metavar="REF",
        help="validate and regenerate an isolated Git commit snapshot",
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
    new_parser.add_argument(
        "slug",
        help=(
            "stable lowercase name used in the ID and path; "
            "for logs omit the automatically added date"
        ),
    )
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
    _add_external_resource_arguments(new_parser)
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
    archive_parser = subparsers.add_parser(
        "archive",
        help="move an inactive durable record into the year-based archive",
    )
    archive_parser.add_argument("document_id", metavar="ID", help="stable document ID")
    archive_parser.add_argument(
        "--date",
        type=_iso_date,
        help="archive operation date in YYYY-MM-DD format (default: today)",
    )
    restore_parser = subparsers.add_parser(
        "restore",
        help="move an archived durable record back to its active type root",
    )
    restore_parser.add_argument("document_id", metavar="ID", help="stable document ID")
    subparsers.add_parser(
        "dashboard",
        help="generate the human-readable current-state dashboard",
    )
    subparsers.add_parser(
        "refresh",
        help="synchronize links, indexes, dashboard, and navigation",
    )
    _add_browse_commands(subparsers)
    review_context_parser = subparsers.add_parser(
        "review-context",
        help="select bounded evidence for a period review",
    )
    review_context_parser.add_argument(
        "--from",
        dest="period_start",
        type=_iso_date,
        required=True,
        metavar="DATE",
        help="inclusive review start date in YYYY-MM-DD format",
    )
    review_context_parser.add_argument(
        "--to",
        dest="period_end",
        type=_iso_date,
        required=True,
        metavar="DATE",
        help="inclusive review end date in YYYY-MM-DD format",
    )
    review_context_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="maximum rows per section (default: 20)",
    )
    review_context_parser.add_argument(
        "--json",
        action="store_true",
        help="emit stable machine-readable JSON",
    )
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


def _add_external_resource_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", help="external-resource Artifact URL")
    parser.add_argument(
        "--provider",
        help="external-resource Artifact provider, such as sharepoint",
    )
    parser.add_argument(
        "--owner",
        help="person or team responsible for the external-resource Artifact",
    )
    parser.add_argument(
        "--access",
        choices=("internal", "restricted", "public"),
        help="external-resource Artifact access (default: internal)",
    )
    parser.add_argument(
        "--last-verified",
        type=_iso_date,
        help="external-resource verification date (default: document date)",
    )


def _add_browse_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    list_parser = subparsers.add_parser(
        "list",
        help="list repository content with explicit filters",
    )
    _add_content_filters(list_parser)
    list_archive = list_parser.add_mutually_exclusive_group()
    list_archive.add_argument(
        "--include-archived",
        dest="archive_scope",
        action="store_const",
        const="include",
        default="exclude",
        help="include archived records (default: active locations only)",
    )
    list_archive.add_argument(
        "--archived-only",
        dest="archive_scope",
        action="store_const",
        const="only",
        help="show only archived records",
    )
    search_parser = subparsers.add_parser(
        "search",
        help="search titles, IDs, metadata, and Markdown text",
    )
    search_parser.add_argument("query", help="one or more words; every word must match")
    _add_content_filters(search_parser)
    search_archive = search_parser.add_mutually_exclusive_group()
    search_archive.add_argument(
        "--active-only",
        dest="archive_scope",
        action="store_const",
        const="exclude",
        default="include",
        help="exclude archived records (default: search all)",
    )
    search_archive.add_argument(
        "--archived-only",
        dest="archive_scope",
        action="store_const",
        const="only",
        help="search only archived records",
    )


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
