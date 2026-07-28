---
name: weekly-review
description: Perform an evidence-based weekly review of a work repository. Use when asked for a weekly status, weekly report, review of active work, overdue or blocked work, Area health, Project progress, Inbox aging, accomplishments, risks, decisions, or next-week priorities.
---

# Weekly review

1. Establish the requested review period. If none is given, use the current work week and say so.
2. Run `uv run workrepo inbox status`, then inspect:
   - dated Inbox files in the period;
   - Logs in the period;
   - active Project `index.md` files and relevant artifacts;
   - active Area `index.md` files and their review dates;
   - `DASHBOARD.md` only as a generated overview, never as canonical state.
3. Separate findings into completed outcomes, current state, risks or blockers, decisions, and next
   actions. Cite repository-relative source paths.
4. Treat missing evidence as unknown. Never infer completion from silence or convert a proposal into
   a decision.
5. Propose state changes before applying changes that affect multiple documents.
6. When authorized, update canonical Project or Area state and create a typed weekly-report artifact
   only where a durable report is useful.
7. Keep `created` unchanged. Set `updated` and Area `last_reviewed` to the actual review date.
8. Run `uv run workrepo refresh` and `uv run workrepo check`.

Do not force every event into a weekly report. Link to Logs and canonical state instead of copying
large passages.
