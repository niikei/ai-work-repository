"""CLI commands that mutate repository content."""

from __future__ import annotations

from typing import TYPE_CHECKING

from workrepo.creation import (
    ArtifactRequest,
    CreateRequest,
    ExternalResourceMetadata,
    capture_inbox,
    create_artifact,
    create_document,
)
from workrepo.lifecycle import archive_document, restore_document

if TYPE_CHECKING:
    import argparse
    from datetime import date
    from pathlib import Path

COMMAND_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


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


def run_new_command(root: Path, args: argparse.Namespace) -> int:
    if args.document_type == "artifact":
        if (option_error := _artifact_option_error(args)) is not None:
            print(f"ERROR {option_error}")
            return 1
        try:
            external_resource = _external_resource_metadata(args)
            path = create_artifact(
                root,
                ArtifactRequest(
                    slug=args.slug,
                    title=args.title,
                    parent_id=args.parent,
                    kind=args.kind,
                    related=tuple(args.related),
                    document_date=args.date,
                    external_resource=external_resource,
                ),
            )
        except COMMAND_ERRORS as error:
            print(f"ERROR {error}")
            return 1
        print(f"Created {path.relative_to(root.resolve())}.")
        return 0
    if (option_error := _entity_option_error(args)) is not None:
        print(f"ERROR {option_error}")
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
            owner=args.owner,
            priority=args.priority,
            target_date=args.target_date,
        ),
    )


def _artifact_option_error(args: argparse.Namespace) -> str | None:
    if args.parent is None or args.kind is None:
        return "artifact requires --parent and --kind"
    if args.template is not None:
        return "--template is only valid for log"
    if args.priority is not None or args.target_date is not None:
        return "--priority and --target-date are only valid for project"
    return None


def _entity_option_error(args: argparse.Namespace) -> str | None:
    if (
        args.parent is not None
        or args.kind is not None
        or _has_external_resource_arguments(args, include_owner=False)
    ):
        return "artifact-only options cannot be used for an entity"
    if args.owner is not None and args.document_type not in {"project", "area"}:
        return "--owner is only valid for project and area entities"
    if (
        args.priority is not None or args.target_date is not None
    ) and args.document_type != "project":
        return "--priority and --target-date are only valid for project"
    return None


def _external_resource_metadata(
    args: argparse.Namespace,
) -> ExternalResourceMetadata | None:
    if args.kind != "external-resource":
        if _has_external_resource_arguments(args):
            message = "external resource options require --kind external-resource"
            raise ValueError(message)
        return None
    missing = [
        option
        for option, value in (
            ("--url", args.url),
            ("--provider", args.provider),
            ("--owner", args.owner),
        )
        if value is None
    ]
    if missing:
        message = f"external-resource requires {', '.join(missing)}"
        raise ValueError(message)
    return ExternalResourceMetadata(
        provider=args.provider,
        url=args.url,
        owner=args.owner,
        access=args.access or "internal",
        last_verified=args.last_verified,
    )


def _has_external_resource_arguments(
    args: argparse.Namespace,
    *,
    include_owner: bool = True,
) -> bool:
    owner = args.owner if include_owner else None
    return any(
        value is not None
        for value in (
            args.url,
            args.provider,
            owner,
            args.access,
            args.last_verified,
        )
    )


def run_capture(root: Path, text: str, *, capture_date: date | None) -> int:
    try:
        path = capture_inbox(root, text, capture_date=capture_date)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Captured in {path.relative_to(root.resolve())}.")
    return 0


def _run_archive(
    root: Path,
    document_id: str,
    *,
    operation_date: date | None,
) -> int:
    try:
        result = archive_document(
            root,
            document_id,
            operation_date=operation_date,
        )
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Archived {result.document_id}: {result.source} -> {result.destination}.")
    return 0


def _run_restore(root: Path, document_id: str) -> int:
    try:
        result = restore_document(root, document_id)
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    print(f"Restored {result.document_id}: {result.source} -> {result.destination}.")
    return 0


def run_lifecycle(root: Path, args: argparse.Namespace) -> int:
    if args.command == "archive":
        return _run_archive(root, args.document_id, operation_date=args.date)
    return _run_restore(root, args.document_id)
