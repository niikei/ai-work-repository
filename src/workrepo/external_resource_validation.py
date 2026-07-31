"""Validation for external-resource artifacts."""

from urllib.parse import urlsplit

from workrepo.link_validation import url_security_messages
from workrepo.models import Artifact, Issue

EXTERNAL_RESOURCE_FIELDS = frozenset(
    {"provider", "url", "owner", "access", "last_verified"},
)
EXTERNAL_ACCESS_VALUES = frozenset({"internal", "restricted", "public"})


def validate_external_resource(artifact: Artifact) -> list[Issue]:
    metadata = artifact.metadata
    if metadata.get("kind") != "external-resource":
        unexpected = EXTERNAL_RESOURCE_FIELDS & metadata.keys()
        return [
            Issue(
                artifact.path,
                f"{field} is only valid for external-resource",
            )
            for field in sorted(unexpected)
        ]
    issues = [
        Issue(artifact.path, f"external-resource is missing required field: {field}")
        for field in sorted(EXTERNAL_RESOURCE_FIELDS - metadata.keys())
    ]
    issues.extend(
        Issue(artifact.path, f"{field} must be a non-empty string")
        for field in ("provider", "owner")
        if field in metadata and not _is_nonempty_string(metadata[field])
    )
    issues.extend(_validate_external_access(artifact))
    issues.extend(_validate_external_url(artifact))
    return issues


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_external_access(artifact: Artifact) -> list[Issue]:
    access = artifact.metadata.get("access")
    if access is None or access in EXTERNAL_ACCESS_VALUES:
        return []
    allowed = ", ".join(sorted(EXTERNAL_ACCESS_VALUES))
    return [
        Issue(
            artifact.path,
            f"invalid access {access!r}; expected one of: {allowed}",
        ),
    ]


def _validate_external_url(artifact: Artifact) -> list[Issue]:
    value = artifact.metadata.get("url")
    if value is None:
        return []
    if not isinstance(value, str):
        return [Issue(artifact.path, "url must be an HTTP or HTTPS URL")]
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        return [Issue(artifact.path, "url must be an HTTP or HTTPS URL")]
    return [Issue(artifact.path, message) for message in url_security_messages(parsed)]

