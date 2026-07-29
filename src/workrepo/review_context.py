"""Bounded evidence selection for human and AI workspace reviews."""

from dataclasses import dataclass
from datetime import date

from workrepo.inbox import InboxFile
from workrepo.models import Document
from workrepo.review import next_review
from workrepo.state import RepositoryState
from workrepo.validation import inbox_report, related_ids

REVIEW_TYPES = frozenset({"project", "area"})
INACTIVE_STATUSES = frozenset({"completed", "cancelled", "retired"})
REASON_PRIORITY = {
    "related-to-period-log": 0,
    "updated-in-period": 1,
    "blocked": 2,
    "health:red": 3,
    "review-overdue": 4,
    "review-due-in-period": 5,
    "health:amber": 6,
}


@dataclass(frozen=True, slots=True)
class ReviewCandidate:
    """One Project or Area selected for explicit review reasons."""

    document: Document
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewContext:
    """Bounded repository evidence for one inclusive review period."""

    period_start: date
    period_end: date
    inbox_files: tuple[InboxFile, ...]
    logs: tuple[Document, ...]
    candidates: tuple[ReviewCandidate, ...]
    inbox_truncated: bool
    logs_truncated: bool
    candidates_truncated: bool


def build_review_context(
    state: RepositoryState,
    *,
    period_start: date,
    period_end: date,
    limit: int = 20,
) -> ReviewContext:
    """Select review evidence without searching or reading unrelated bodies."""
    if period_start > period_end:
        message = "review period start must not be later than end"
        raise ValueError(message)
    if limit <= 0:
        message = "review context limit must be positive"
        raise ValueError(message)

    report = inbox_report(state)
    inbox_matches = [
        item
        for item in report.files
        if period_start <= item.capture_date <= period_end
        or (item.capture_date < period_start and item.open_items)
    ]
    ordered_inbox = sorted(
        inbox_matches,
        key=lambda item: (
            not bool(item.open_items),
            item.capture_date,
            item.path.as_posix(),
        ),
    )
    selected_inbox = ordered_inbox[:limit]

    period_logs = [
        document
        for document in state.documents
        if document.metadata.get("type") == "log"
        and _in_period(document.metadata.get("date"), period_start, period_end)
    ]
    ordered_logs = sorted(period_logs, key=_dated_document_key)
    selected_logs = ordered_logs[-limit:]

    related = {
        identifier
        for document in selected_logs
        for identifier in related_ids(document)
    }
    candidates = _review_candidates(
        state,
        related=related,
        period_start=period_start,
        period_end=period_end,
    )
    selected_candidates = candidates[:limit]
    return ReviewContext(
        period_start=period_start,
        period_end=period_end,
        inbox_files=tuple(selected_inbox),
        logs=tuple(selected_logs),
        candidates=tuple(selected_candidates),
        inbox_truncated=len(ordered_inbox) > limit,
        logs_truncated=len(ordered_logs) > limit,
        candidates_truncated=len(candidates) > limit,
    )


def review_context_payload(context: ReviewContext) -> dict[str, object]:
    """Return a stable JSON-compatible representation."""
    return {
        "version": 1,
        "period": {
            "from": context.period_start.isoformat(),
            "to": context.period_end.isoformat(),
        },
        "inbox": [
            {
                "path": item.path.as_posix(),
                "capture_date": item.capture_date.isoformat(),
                "open_items": list(item.open_items),
                "completed_items": item.completed_items,
                "age_days": item.age_days,
            }
            for item in context.inbox_files
        ],
        "logs": [_document_payload(document) for document in context.logs],
        "candidates": [
            {
                **_document_payload(candidate.document),
                "reasons": list(candidate.reasons),
            }
            for candidate in context.candidates
        ],
        "truncated": {
            "inbox": context.inbox_truncated,
            "logs": context.logs_truncated,
            "candidates": context.candidates_truncated,
        },
    }


def _review_candidates(
    state: RepositoryState,
    *,
    related: set[str],
    period_start: date,
    period_end: date,
) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    for document in state.documents:
        if document.metadata.get("type") not in REVIEW_TYPES:
            continue
        reasons = _candidate_reasons(
            document,
            related=related,
            period_start=period_start,
            period_end=period_end,
        )
        if reasons:
            candidates.append(ReviewCandidate(document=document, reasons=reasons))
    return sorted(candidates, key=_candidate_key)


def _candidate_reasons(
    document: Document,
    *,
    related: set[str],
    period_start: date,
    period_end: date,
) -> tuple[str, ...]:
    metadata = document.metadata
    reasons: set[str] = set()
    identifier = metadata.get("id")
    if isinstance(identifier, str) and identifier in related:
        reasons.add("related-to-period-log")
    if _in_period(metadata.get("updated"), period_start, period_end):
        reasons.add("updated-in-period")
    if metadata.get("status") == "blocked":
        reasons.add("blocked")
    health = metadata.get("health")
    if health in {"red", "amber"} and metadata.get("status") not in INACTIVE_STATUSES:
        reasons.add(f"health:{health}")
    reasons.update(_review_date_reasons(document, period_start, period_end))
    return tuple(sorted(reasons, key=lambda reason: (REASON_PRIORITY[reason], reason)))


def _review_date_reasons(
    document: Document,
    period_start: date,
    period_end: date,
) -> set[str]:
    if document.metadata.get("type") != "area" or document.metadata.get("status") != "active":
        return set()
    last_reviewed = _date_value(document.metadata.get("last_reviewed"))
    cycle = document.metadata.get("review_cycle")
    if last_reviewed is None or not isinstance(cycle, str):
        return set()
    due = next_review(last_reviewed, cycle)
    if due < period_start:
        return {"review-overdue"}
    if due <= period_end:
        return {"review-due-in-period"}
    return set()


def _document_payload(document: Document) -> dict[str, object]:
    metadata = document.metadata
    return {
        "type": str(metadata.get("type", "")),
        "id": str(metadata.get("id", "")),
        "title": document.title,
        "path": document.path.as_posix(),
        "status": str(metadata.get("status", "")),
        "health": str(metadata.get("health", "")),
        "date": _iso_value(metadata.get("date")),
        "updated": _iso_value(metadata.get("updated")),
        "last_reviewed": _iso_value(metadata.get("last_reviewed")),
        "related": list(related_ids(document)),
    }


def _candidate_key(candidate: ReviewCandidate) -> tuple[int, str, str]:
    priority = min(REASON_PRIORITY[reason] for reason in candidate.reasons)
    document_type = str(candidate.document.metadata.get("type", ""))
    return priority, document_type, candidate.document.path.as_posix()


def _dated_document_key(document: Document) -> tuple[date, str]:
    document_date = _date_value(document.metadata.get("date"))
    if document_date is None:
        message = f"log date is invalid: {document.path}"
        raise ValueError(message)
    return document_date, document.path.as_posix()


def _in_period(value: object, period_start: date, period_end: date) -> bool:
    parsed = _date_value(value)
    return parsed is not None and period_start <= parsed <= period_end


def _iso_value(value: object) -> str | None:
    parsed = _date_value(value)
    return parsed.isoformat() if parsed is not None else None


def _date_value(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
