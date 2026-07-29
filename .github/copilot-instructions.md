# AI-ready work repository instructions

This local-first repository is shared by a human and AI. Its records are user-owned; prioritize
accuracy and traceability.

- Discover with `uv run workrepo list` or `uv run workrepo search`. Open only relevant records and
  the nearest owning `index.md`; do not scan the whole tree or read every guide.
- Preserve uncertainty. Do not invent decisions, owners, deadlines, completion, or relationships.
- Stable IDs and frontmatter `related` values are canonical relationships.
- Use `uv run workrepo capture` for Inbox input and `uv run workrepo new` for managed records.
- Do not edit `DASHBOARD.md`, `NAVIGATION.md`, or `workrepo:related` blocks directly; run
  `uv run workrepo refresh`.
- Do not move, delete, archive, restore, or broadly rewrite records without authorization.
- Never store credentials, tokens, signed URLs, or data that cannot be shared with the configured
  Git or AI. Do not edit external originals unless explicitly requested.
- Run `uv run workrepo refresh` and `uv run workrepo check` after managed-document changes.
- Do not commit or push unless requested.

Load path-specific instructions and Agent Skills only for matching tasks.
Use TermKeeper only through its public CLI, MCP, or HTTP interface.
