---
name: process-inbox
description: Review temporary captures and propose safe durable destinations
argument-hint: "Optional date, topic, or maximum number of items"
agent: agent
---

Use the [Inbox triage skill](../skills/inbox-triage/SKILL.md) to inspect the current Inbox.

Start read-only. Report:

1. backlog health;
2. a table of each relevant open item, proposed destination, reason, and uncertainty;
3. questions that block safe classification;
4. the exact changes you recommend.

Do not move, delete, or mark items complete until I approve the proposed changes. If I approve,
apply the changes and run the repository refresh and validation commands.
