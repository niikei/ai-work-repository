---
name: inbox-triage
description: Safely review and process dated work-repository Inbox checklists. Use when asked to clean, classify, organize, review, or reduce Inbox items; turn rough notes into Logs, Project or Area state, or reusable Library documents; or identify stale and ambiguous captures without losing the original meaning.
---

# Inbox triage

1. Run `uv run workrepo inbox status` and `uv run workrepo inbox review`.
2. Read each relevant dated Inbox file. During proposal-only triage, discover current-state
   candidates only with commands shaped like:
   `uv run workrepo search "<distinctive terms>" --type project --active-only --limit 5` and the
   equivalent Area query. Do not use editor search, `rg`, `find`, file globs, or workspace scans.
   Do not search Logs for precedents. If bounded discovery fails, report the failure instead of
   changing search mechanisms.
3. Open only records returned by bounded discovery. By default, inspect at most one primary Project
   and one Area per item. Exceed that only when the Inbox text explicitly names multiple
   responsibilities or an opened canonical record verifies the relationships. A related record is
   not automatically a destination.
4. Classify each item on separate axes; one item may require both evidence and state synchronization:
   - Evidence: if something happened—a meeting, call, decision, incident, observed metric, or
     proposal—preserve it in a Log. Combine several small events from one day into one daily Log.
   - Current state: synchronize a bounded outcome or action to its Project, or ongoing health and
     responsibility to its Area. Do not use Project or Area state as a substitute for event evidence.
   - Durable material: use Catalog for a stable subject, Playbooks for a settled reusable standard,
     Knowledge for explanation, and Resources for a durable external pointer. Do not update a
     Playbook merely because changing the standard is still an open action or proposal.
   - Insufficient context: leave the item open and state only the questions whose answers are not
     already present.
5. Treat explicit negatives as facts: “not approved”, “owner not agreed”, and “date not confirmed”
   are known states, not missing information. Preserve proposals as proposals; never promote them
   to decisions, approved work, or established relationships.
6. For proposal-only output, list only records that would be changed if the user approved the
   triage now:
   - `Evidence now`: the dated Log when the item records an event.
   - `Synchronize now`: canonical Project or Area state that the present facts actually change.
   - `Keep open`: whether the Inbox item must remain and why.
   - `Unresolved questions`: only genuinely missing answers.
   Do not list a possible future destination. Do not list an existing Playbook, Process, Area, or
   Project merely to show topical relevance. An insufficient request may be logged as a call while
   remaining open, but it does not update an intake Process or Area.
7. Update or create every required destination before marking the source item complete.
8. Preserve names, dates, uncertainty, and source wording. Do not invent owners, decisions, deadlines,
   completion, or relationships.
9. Remove a completed dated Inbox file only when no useful context would be lost and the user has
   authorized cleanup.
10. Run `uv run workrepo refresh` and `uv run workrepo check`.

When updating current state, replace obsolete wording rather than leaving mutually contradictory
bullets. Preserve useful history in the source Log or a typed review artifact.

Use `uv run workrepo new` for managed documents. Never create `00-inbox/a.md` or another ad hoc
Inbox file; new capture goes through `uv run workrepo capture`.
