"""CLI presentation for bounded review context."""

import argparse
import json
from pathlib import Path

from workrepo.navigation import display_row
from workrepo.review_context import build_review_context, review_context_payload
from workrepo.validation import require_repository

COMMAND_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


def run_review_context(root: Path, args: argparse.Namespace) -> int:
    """Build and print review evidence selected by CLI arguments."""
    try:
        context = build_review_context(
            require_repository(root),
            period_start=args.period_start,
            period_end=args.period_end,
            limit=args.limit,
        )
    except COMMAND_ERRORS as error:
        print(f"ERROR {error}")
        return 1
    if args.json:
        print(json.dumps(review_context_payload(context), ensure_ascii=False, indent=2))
        return 0

    print(f"Review period: {context.period_start} to {context.period_end}")
    print("\nInbox:")
    if not context.inbox_files:
        print("  none")
    for item in context.inbox_files:
        print(
            f"  {item.path}  open={len(item.open_items)} "
            f"completed={item.completed_items} age={item.age_days}d",
        )
        for text in item.open_items:
            print(f"    - {text}")
    _print_truncated(truncated=context.inbox_truncated)

    print("\nLogs:")
    if not context.logs:
        print("  none")
    for document in context.logs:
        print(f"  {display_row(document)}")
    _print_truncated(truncated=context.logs_truncated)

    print("\nProject and Area candidates:")
    if not context.candidates:
        print("  none")
    for candidate in context.candidates:
        reasons = ", ".join(candidate.reasons)
        print(f"  [{reasons}] {display_row(candidate.document)}")
    _print_truncated(truncated=context.candidates_truncated)
    return 0


def _print_truncated(*, truncated: bool) -> None:
    if truncated:
        print("  ... truncated; increase --limit to inspect more")
