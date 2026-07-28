---
name: Repository Python
description: Engineering rules for repository-maintenance Python
applyTo: "{src,tests}/**/*.py"
---

- Target Python 3.12 or newer and preserve strict typing.
- Keep domain decisions independent from CLI rendering and filesystem plumbing.
- Add focused pytest coverage for behavior and boundary cases.
- Avoid hidden writes and process-wide mutable state.
- Preserve user files and unrelated worktree changes.
- Run `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`, and
  `uv run pytest` after changes.
