# AI-ready work repository instructions

This repository is a local-first work record shared by a human and AI. Markdown content and original
files are user-owned records; accuracy and traceability are more important than aggressive cleanup.

- Read `README.md` and the nearest Project or Area `index.md` before changing managed content.
- Use the H1 as the canonical title. Do not add `title` to YAML frontmatter.
- Treat stable IDs and frontmatter `related` values as canonical relationships.
- Keep events in `10-log/`; keep current state in the related Project or Area.
- Treat `00-inbox/` as temporary capture. Use `uv run workrepo capture`, not ad hoc Inbox files.
- Prefer `uv run workrepo new` when creating managed content.
- Preserve `created`; update `updated` when changing canonical content.
- Preserve uncertainty. Do not invent decisions, owners, deadlines, completion, or relationships.
- Do not edit `DASHBOARD.md` or `workrepo:related` blocks directly; run `uv run workrepo refresh`.
- Do not move, delete, archive, or broadly rewrite records without explicit authorization.
- Do not edit Word, Excel, PDF, or image originals unless explicitly requested.
- Keep data that cannot be shared with the configured Git or AI physically outside this repository.
- Run `uv run workrepo refresh` and `uv run workrepo check` after managed-document changes.
- Do not commit or push unless the user explicitly requests it.

Use the repository Agent Skills for Inbox triage, weekly review, and managed-document authoring.
Use TermKeeper only through its public CLI, MCP, or HTTP interface.
