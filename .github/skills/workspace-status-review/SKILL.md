---
name: workspace-status-review
description: Perform an evidence-based status review of a work repository for a requested period or scope. Use when asked for a daily, weekly, or monthly review; a Project or Area review; active, overdue, blocked, or stale work; Area health; Project progress; Inbox aging; accomplishments; risks; decisions; or priorities.
user-invocable: false
---

# Workspace status review

1. Establish the requested period and scope. If neither is given, use the current work week across
   the workspace and say so.
2. Start with
   `uv run workrepo review-context --from START --to END --limit 20 --json`.
   Treat its paths as the complete initial discovery set. Do not use memory, editor search,
   `workrepo list`, `workrepo search`, `rg`, `find`, or file globs to rediscover review candidates.
   If a section is truncated, increase `--limit` once instead of changing discovery mechanisms.
3. Inspect only the returned:
   - Inbox files and open items;
   - period Logs;
   - Project and Area candidates selected for period activity, Log relationships, blocked or
     unhealthy state, or review due dates;
   - `DASHBOARD.md` only as a generated overview, never as canonical state.
   Do not automatically open every candidate. Use the returned reasons and metadata first, then
   open only records needed to support a finding in the requested scope.
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
