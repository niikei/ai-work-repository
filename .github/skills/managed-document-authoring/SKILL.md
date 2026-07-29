---
name: managed-document-authoring
description: Create or update validated Markdown work records with canonical metadata and relationships. Use when asked to add or edit a Log, Project, Area, Catalog entity, Playbook, Knowledge document, Resource, report, analysis, specification, deliverable, or other managed document in this work repository.
---

# Managed document authoring

1. Read the repository classification guide, document contract, and nearest owning `index.md`.
2. Choose the lightest valid representation:
   - Entity for a stable Project or Area.
   - Catalog for a durable system, role, organization, or service.
   - Playbook for a reusable process, procedure, control, or standard.
   - Knowledge for an explanatory concept, guide, or glossary.
   - Resource for a durable pointer to an external original.
   - Log for a dated event, meeting, incident, investigation, or decision.
   - Typed artifact for a durable report, analysis, specification, review, control, deliverable, or
     managed external resource.
   - Frontmatter-free Markdown only for local Project or Area working material.
3. Use `uv run workrepo new` to generate managed paths, IDs, and metadata. Do not handcraft a managed
   file when the CLI supports it.
4. Use only existing stable IDs in `related`; represent cross-Area work with multiple relationships.
5. Keep one H1 as the canonical title and do not add `title` to frontmatter.
6. Preserve `created` after the first commit. Set `updated` to the real editing date. Preserve
   uncertainty and do not fabricate business facts.
7. Keep event history in Logs and current state in Project or Area documents. Replace superseded
   state; do not append text that contradicts the current state.
8. Paste ordinary Word, Excel, PowerPoint, SharePoint, and similar references directly into the
   relevant Markdown. Create an `external-resource` only when a shared original needs durable owner,
   access class, or verification metadata. Never record secrets or signed URLs.
9. Do not edit generated related-link blocks, `DASHBOARD.md`, or `NAVIGATION.md` directly.
10. Run `uv run workrepo refresh` and `uv run workrepo check`.

Ask before deleting, moving, archiving, or broadly rewriting user-owned records.
