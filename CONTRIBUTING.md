# Contributing

Contributions that improve safety, portability, documentation quality, and human or AI usability
are welcome.

## Before making a change

1. Search existing Issues and open one for significant behavioral or schema changes.
2. Never add real workplace records, personal information, credentials, or private links.
3. Keep compatibility with Python 3.12 or newer, Linux, and Windows.
4. Preserve stable document IDs and generated-file conventions.

## Development

```shell
uv sync --locked
uv run workrepo hooks install
uv run workrepo doctor
```

Before submitting a pull request, run:

```shell
uv run workrepo check --strict
uv run workrepo refresh
git diff --exit-code
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## Pull requests

- Keep one focused purpose per pull request.
- Add tests for behavior and boundary cases.
- Explain user-facing and AI-facing effects.
- Update documentation when commands, metadata, or workflows change.
- Do not edit generated relationship blocks, `DASHBOARD.md`, or `NAVIGATION.md` manually.
