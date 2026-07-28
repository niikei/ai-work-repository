"""Local-first repository policy loading."""

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from workrepo.yamlutil import load_yaml

POLICY_PATH = Path(".workspace/policy.yaml")
SUPPORTED_POLICY_VERSION = 1


@dataclass(frozen=True, slots=True)
class InboxPolicy:
    """Limits that keep temporary capture from becoming permanent storage."""

    warn_after_days: int
    block_after_days: int
    max_open_items: int


@dataclass(frozen=True, slots=True)
class FilePolicy:
    """Cross-platform and attachment safety limits."""

    max_attachment_bytes: int
    max_path_length: int


@dataclass(frozen=True, slots=True)
class Policy:
    """Repository-local operational policy."""

    inbox: InboxPolicy
    files: FilePolicy
    timezone: str


def load_policy(root: Path) -> Policy:
    """Load and type-check repository-local policy."""
    try:
        raw = load_yaml((root / POLICY_PATH).read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        message = f"invalid policy YAML: {error}"
        raise ValueError(message) from error
    mapping = _mapping(raw, "policy")
    version = mapping.get("version")
    if version != SUPPORTED_POLICY_VERSION:
        message = f"unsupported policy version {version!r}; expected {SUPPORTED_POLICY_VERSION}"
        raise ValueError(message)
    inbox = _mapping(mapping.get("inbox"), "policy.inbox")
    files = _mapping(mapping.get("files"), "policy.files")
    timezone = _timezone(mapping.get("timezone"))
    inbox_policy = InboxPolicy(
        warn_after_days=_positive_int(inbox.get("warn_after_days"), "warn_after_days"),
        block_after_days=_positive_int(
            inbox.get("block_after_days"),
            "block_after_days",
        ),
        max_open_items=_positive_int(inbox.get("max_open_items"), "max_open_items"),
    )
    if inbox_policy.block_after_days <= inbox_policy.warn_after_days:
        message = "block_after_days must be greater than warn_after_days"
        raise ValueError(message)
    return Policy(
        inbox=inbox_policy,
        files=FilePolicy(
            max_attachment_bytes=_positive_int(
                files.get("max_attachment_bytes"),
                "max_attachment_bytes",
            ),
            max_path_length=_positive_int(
                files.get("max_path_length"),
                "max_path_length",
            ),
        ),
        timezone=timezone,
    )


def _mapping(raw: object, label: str) -> dict[object, object]:
    if not isinstance(raw, dict):
        message = f"{label} must be a mapping"
        raise TypeError(message)
    return raw


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        message = f"{label} must be a positive integer"
        raise ValueError(message)
    return raw


def _timezone(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        message = "policy.timezone must be a non-empty IANA timezone"
        raise ValueError(message)
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError as error:
        message = f"unknown policy.timezone: {raw}"
        raise ValueError(message) from error
    return raw
