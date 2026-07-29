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
- Replace superseded Project or Area state instead of appending contradictory bullets. Preserve the
  prior state in a Log or review artifact when its history matters.
- Keep historical events in Logs and current state in Project or Area documents.
- Keep `index.md` as the only Markdown file directly inside a Project or Area Entity directory.
- Put reusable subjects in Catalog, normative methods in Playbooks, explanations in Knowledge, and
  durable pointers to external originals in Resources.
- Paste ordinary external references directly. Use typed `external-resource` only when an original
  needs durable owner, access, or verification metadata; never copy credentials or tokens.
- Do not edit generated related-link blocks manually.
- Validate with `uv run workrepo refresh` and `uv run workrepo check`.
