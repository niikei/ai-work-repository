"""Local environment diagnostics."""

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from workrepo.gitops import hooks_active, is_git_repository
from workrepo.schema import SUPPORTED_SCHEMA_VERSION
from workrepo.validation import inspect_repository


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One local setup diagnostic."""

    name: str
    ok: bool
    detail: str


def diagnose(root: Path) -> tuple[Diagnostic, ...]:
    """Inspect local prerequisites without changing configuration."""
    diagnostics = [
        Diagnostic(
            name="Python",
            ok=sys.version_info >= (3, 12),
            detail=platform.python_version(),
        ),
        Diagnostic(
            name="Git repository",
            ok=is_git_repository(root),
            detail=str(root.resolve()),
        ),
        Diagnostic(
            name="Git hooks",
            ok=hooks_active(root),
            detail="active" if hooks_active(root) else "run: workrepo hooks install",
        ),
        Diagnostic(
            name="Schema",
            ok=True,
            detail=f"version {SUPPORTED_SCHEMA_VERSION}",
        ),
    ]
    try:
        _, issues = inspect_repository(root)
    except (OSError, TypeError, ValueError) as error:
        diagnostics.append(
            Diagnostic(name="Repository", ok=False, detail=str(error)),
        )
    else:
        diagnostics.append(
            Diagnostic(
                name="Repository",
                ok=not issues,
                detail="valid" if not issues else f"{len(issues)} error(s)",
            ),
        )
    return tuple(diagnostics)
