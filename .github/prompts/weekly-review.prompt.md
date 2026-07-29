---
name: weekly-review
description: Review the requested week using repository evidence
argument-hint: "ISO week, date range, or review focus"
agent: agent
---

Use the [Workspace status review skill](../skills/workspace-status-review/SKILL.md) for
`${input:period:the current work week}`.

Start read-only. Produce a concise review with repository-relative evidence for:

- completed outcomes;
- current Project state;
- Area health and overdue reviews;
- risks, blockers, and unresolved decisions;
- Inbox items needing attention;
- recommended priorities for the next week.

Clearly separate recorded facts from recommendations. Ask before applying cross-document changes or
creating a durable weekly-report artifact.
