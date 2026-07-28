---
name: Managed work records
description: Metadata and lifecycle rules for canonical Markdown records
applyTo: "{10-log,20-projects,30-areas,40-library}/**/*.md"
---

- Read the nearest Project or Area `index.md` before editing content below it.
- Keep exactly one H1 and do not duplicate it as a YAML `title`.
- Preserve unknown `x-*` metadata unless the requested change owns it.
- Never change `created` after the document is committed.
- Set `updated` to the actual edit date; never use a future date.
- Use existing stable IDs in `related`; do not guess relationships from similar names.
- Keep historical events in Logs and current state in Project or Area documents.
- Do not edit generated related-link blocks manually.
- Validate with `uv run workrepo refresh` and `uv run workrepo check`.
