# AI-ready work repository instructions

This repository is a local-first work record shared by a human and AI. Markdown content and original
files are user-owned records; accuracy and traceability are more important than aggressive cleanup.

- Read `README.md` and the nearest Project or Area `index.md` before changing managed content.
- Use the H1 as the canonical title. Do not add `title` to YAML frontmatter.
- Treat stable IDs and frontmatter `related` values as canonical relationships.
- Keep events and superseded states in `10-log/` or typed review artifacts; keep only current state
  in the related Project or Area.
- Treat `00-inbox/` as temporary capture. Use `uv run workrepo capture`, not ad hoc Inbox files.
- Prefer `uv run workrepo new` when creating managed content.
- Preserve `created`; update `updated` when changing canonical content.
- Preserve uncertainty. Do not invent decisions, owners, deadlines, completion, or relationships.
- Use `uv run workrepo list` and `uv run workrepo search` before scanning large directory trees.
- Do not maintain a manual Project list in an Area; `related` and generated navigation are canonical.
- Allow ordinary Word, Excel, PowerPoint, and SharePoint URLs to be pasted directly into relevant
  Markdown. Promote only durable shared originals needing owner, access, or verification metadata
  to `external-resource`. Never record credentials, access tokens, or signed URLs.
- Do not edit `DASHBOARD.md`, `NAVIGATION.md`, or `workrepo:related` blocks directly; run
  `uv run workrepo refresh`.
- Treat Project and Area indexes as concise current-state dashboards. Put events in Log and durable
  detail in typed artifacts instead of growing the index indefinitely.
- Keep Project and Area entities flat at `<root>/<slug>/index.md`. Supporting content may be nested
  inside an entity directory, but do not create nested entities or another `index.md`. Do not place
  another Markdown file beside the Entity `index.md`; use a purpose-specific subdirectory.
- Classify reusable context by purpose: Catalog for durable subjects, Playbooks for normative
  methods, Knowledge for explanations, and Resources for durable pointers to external originals.
- Do not move, delete, archive, restore, or broadly rewrite records without explicit authorization.
  When authorized, use `uv run workrepo archive ID` or `uv run workrepo restore ID`; never move
  managed lifecycle records manually.
- Do not edit Word, Excel, PDF, or image originals unless explicitly requested.
- Keep data that cannot be shared with the configured Git or AI physically outside this repository.
- Run `uv run workrepo refresh` and `uv run workrepo check` after managed-document changes.
- Do not commit or push unless the user explicitly requests it.

Use the repository Agent Skills for Inbox triage, weekly review, and managed-document authoring.
Use TermKeeper only through its public CLI, MCP, or HTTP interface.
