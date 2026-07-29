---
name: review-change
description: Review a Git commit, range, staged index, or working tree without modifying files
argument-hint: "commit, range, --staged, or working tree"
agent: agent
---

Use the [Change review skill](../skills/change-review/SKILL.md) to review
`${input:target:the current working tree}`.

Start read-only. Resolve the exact comparison, inspect the corresponding Git snapshots, and report:

- actionable findings ordered by severity;
- lost facts, open actions, or contradictory state;
- metadata, deletion, security, and generated-file problems;
- uncertainty or checks that cannot be completed;
- every changed file with its Git status and full repository-relative path.

Do not modify, stage, commit, or push anything.
