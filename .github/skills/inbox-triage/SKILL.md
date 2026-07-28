---
name: inbox-triage
description: Safely review and process dated work-repository Inbox checklists. Use when asked to clean, classify, organize, review, or reduce Inbox items; turn rough notes into Logs, Project or Area state, or reusable Library documents; or identify stale and ambiguous captures without losing the original meaning.
---

# Inbox triage

1. Run `uv run workrepo inbox status` and `uv run workrepo inbox review`.
2. Read each relevant dated Inbox file and the nearest candidate Project or Area `index.md`.
3. Classify each open item:
   - Something that happened, a meeting, decision, or incident → Log.
   - Several small calls, messages, or actions from one day → one daily Log.
   - A bounded change with an outcome → Project state or Project artifact.
   - Ongoing responsibility health or next action → Area state.
   - Reusable role, system, process, or reference knowledge → Library.
   - Insufficient context → leave open and state the missing question.
4. Present the proposed destinations before moving, deleting, or broadly rewriting records.
5. Update or create the durable destination before marking the source item complete.
6. Preserve names, dates, uncertainty, and source wording. Do not invent owners, decisions, deadlines,
   completion, or relationships.
7. Remove a completed dated Inbox file only when no useful context would be lost and the user has
   authorized cleanup.
8. Run `uv run workrepo refresh` and `uv run workrepo check`.

When updating current state, replace obsolete wording rather than leaving mutually contradictory
bullets. Preserve useful history in the source Log or a typed review artifact.

Use `uv run workrepo new` for managed documents. Never create `00-inbox/a.md` or another ad hoc
Inbox file; new capture goes through `uv run workrepo capture`.
