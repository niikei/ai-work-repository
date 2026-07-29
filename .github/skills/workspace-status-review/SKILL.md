---
name: workspace-status-review
description: Perform an evidence-based status review of a work repository for a requested period or scope. Use when asked for a daily, weekly, or monthly review; a Project or Area review; active, overdue, blocked, or stale work; Area health; Project progress; Inbox aging; accomplishments; risks; decisions; or priorities.
user-invocable: false
---

# Workspace status review

1. Establish the requested period and scope. If neither is given, use the current work week across
   the workspace and say so.
2. Start with `uv run workrepo list`, `uv run workrepo search`, and
   `uv run workrepo inbox status` to narrow the review. Never scan the full tree.
3. Inspect only the relevant:
   - dated Inbox files in the period;
   - Logs in the period;
   - active Project `index.md` files and relevant artifacts;
   - active Area `index.md` files and their review dates;
   - `DASHBOARD.md` only as a generated overview, never as canonical state.
4. Separate findings into completed outcomes, current state, risks or blockers, decisions, and next
   actions. Cite repository-relative source paths.
5. Treat missing evidence as unknown. Never infer completion from silence or convert a proposal into
   a decision.
6. Propose state changes before applying changes that affect multiple documents.
7. When authorized, follow the record-maintenance rules: replace superseded Project or Area state
   without deleting unrelated facts or open actions. Create a typed review or report artifact only
   where durable history is useful.
8. Keep `created` unchanged. Set `updated` when content changes. Change Area `last_reviewed` only
   when that Area was actually reviewed, not merely synchronized.
9. Run `uv run workrepo refresh` and `uv run workrepo check`.

Do not force every event into a report. Link to Logs and canonical state instead of copying large
passages.
