---
name: record-maintenance
description: Create or update durable work records with canonical metadata, relationships, and lifecycle state. Use when asked to maintain a Log, Project, Area, Catalog entity, Playbook, Knowledge document, Resource, report, analysis, specification, deliverable, external-resource, or other managed record in this work repository.
---

# Record maintenance

1. Record `git status --short` before editing and preserve pre-existing user changes.
2. Read the nearest owning `index.md`. Consult only the guide needed for an unresolved question:
   classification guide for document purpose, directory contract for placement, or document contract
   for metadata and lifecycle. Do not load all guides by default.
3. Choose the lightest valid representation:
   - Entity for a stable Project or Area.
   - Catalog for a durable system, role, organization, or service.
   - Playbook for a reusable process, procedure, control, or standard.
   - Knowledge for an explanatory concept, guide, or glossary.
   - Resource for a durable pointer to an external original.
   - Log for a dated event, meeting, incident, investigation, or decision.
   - Typed artifact for a durable report, analysis, specification, review, control, deliverable, or
     managed external resource.
   - Frontmatter-free Markdown only for local Project or Area working material.
4. Use `uv run workrepo new` to generate managed paths, IDs, and metadata. Do not handcraft a managed
   file when the CLI supports it.
5. Find relationship candidates with `workrepo list` or `workrepo search`; use only verified IDs and
   represent cross-Area work with multiple relationships.
6. Keep event history in Logs and current state in Project or Area documents. Replace only
   superseded wording; preserve unrelated facts and open actions. Set `updated` when content changes,
   and change `last_reviewed` only when an Area review actually occurred.
7. Paste ordinary Word, Excel, PowerPoint, SharePoint, and similar references directly into the
   relevant Markdown. Create an `external-resource` only when a shared original needs durable owner,
   access class, or verification metadata.
8. Review the focused diff, then run `uv run workrepo refresh` and `uv run workrepo check`.
9. Run `git status --short` after validation. In the final response:
   - Report only files whose content or Git status actually changed during this task as task-touched.
   - Show every task-touched path as visible, full repository-relative text; never use a basename-only
     link label.
   - Copy the final `git status --short` output verbatim into a fenced code block as the current
     worktree state, distinguishing any pre-existing changes recorded in step 1.
   - Do not infer changes from `refresh` output. A regenerated file whose Git status is unchanged is
     not a changed file.

Ask before deleting, moving, archiving, or broadly rewriting user-owned records.
