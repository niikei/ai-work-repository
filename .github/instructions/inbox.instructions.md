---
name: Inbox records
description: Rules for temporary dated Inbox capture
applyTo: "00-inbox/**/*.md"
---

- Allow only `README.md` and top-level `YYYY-MM-DD.md` files.
- Keep dated files as `# YYYY-MM-DD Inbox` checklists without YAML frontmatter.
- Preserve the captured wording until its durable destination has been verified.
- Leave ambiguous items open and state what context is missing.
- Mark an item complete only after it is reflected in a durable destination or intentionally dismissed.
- Use `uv run workrepo capture` for new items and the `inbox-triage` skill for cleanup.
