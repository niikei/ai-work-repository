---
name: inbox-triage
description: Safely review and process dated work-repository Inbox checklists. Use when asked to clean, classify, organize, review, or reduce Inbox items; turn rough notes into Logs, Project or Area state, or reusable Library documents; or identify stale and ambiguous captures without losing the original meaning.
---

# Inbox triage

1. Run `uv run workrepo inbox status` and `uv run workrepo inbox review`.
2. Read each relevant dated Inbox file. Find candidates with `uv run workrepo list` or
   `uv run workrepo search`, then open only the nearest relevant records. Do not glob all
   `index.md` files or scan whole Project or Area trees. If discovery fails, report it and use an
   exact, bounded lookup rather than broadening to a workspace scan.
3. Classify each item on separate axes; one item may require both evidence and state synchronization:
   - Evidence: if something happened—a meeting, call, decision, incident, observed metric, or
     proposal—preserve it in a Log. Combine several small events from one day into one daily Log.
   - Current state: synchronize a bounded outcome or action to its Project, or ongoing health and
     responsibility to its Area. Do not use Project or Area state as a substitute for event evidence.
   - Durable material: use Catalog for a stable subject, Playbooks for a settled reusable standard,
     Knowledge for explanation, and Resources for a durable external pointer. Do not update a
     Playbook merely because changing the standard is still an open action or proposal.
   - Insufficient context: leave the item open and state only the questions whose answers are not
     already present.
4. Treat explicit negatives as facts: “not approved”, “owner not agreed”, and “date not confirmed”
   are known states, not missing information. Preserve proposals as proposals; never promote them
   to decisions, approved work, or established relationships.
5. Present the evidence destination, state synchronization, durable destination, and unresolved
   questions before moving, deleting, or broadly rewriting records. Omit axes that do not apply.
6. Update or create every required destination before marking the source item complete.
7. Preserve names, dates, uncertainty, and source wording. Do not invent owners, decisions, deadlines,
   completion, or relationships.
8. Remove a completed dated Inbox file only when no useful context would be lost and the user has
   authorized cleanup.
9. Run `uv run workrepo refresh` and `uv run workrepo check`.

When updating current state, replace obsolete wording rather than leaving mutually contradictory
bullets. Preserve useful history in the source Log or a typed review artifact.

Use `uv run workrepo new` for managed documents. Never create `00-inbox/a.md` or another ad hoc
Inbox file; new capture goes through `uv run workrepo capture`.
