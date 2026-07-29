---
name: change-review
description: Review Git changes without modifying files. Use when asked to review a commit, branch, pull request diff, staged changes, or working-tree changes for regressions, lost information, metadata errors, unsafe deletions, generated-file mistakes, or repository rule violations.
---

# Change review

1. Resolve the exact target before reviewing. State whether it is a commit, merge commit, range,
   staged index, or working tree.
2. Compare a normal commit with its first parent. For a merge commit, state that first-parent
   semantics are being used unless the user requests another parent. Use `git diff-tree --root` only
   for a root commit.
3. List the complete change set before opening files. Preserve rename, creation, modification, and
   deletion status. For a working-tree review, include untracked files reported by `git status`.
4. For historical review, inspect the target and parent snapshots with `git show REF:path` and
   `git show REF^1:path`. Never substitute the current worktree for historical content.
5. Read only changed files and directly relevant records. Use `workrepo list` or
   `workrepo search` for current repository context; do not scan `**/*.md` or the full tree. Clearly
   distinguish current context from historical evidence.
6. Check for lost facts or open actions, contradictory Project or Area state, incorrect `created`,
   `updated`, or `last_reviewed`, unsafe deletion, duplicated external originals, secret exposure,
   and direct edits to generated files.
7. Report actionable findings first, ordered by severity, with full repository-relative paths and
   line references where possible. Then list every changed path with its Git status.
8. Do not modify files, stage changes, commit, or push unless the user separately requests it.

Useful commands:

```shell
git diff --name-status --find-renames REF^1 REF
git diff --find-renames REF^1 REF -- path/to/file
git show REF:path/to/file
git show REF^1:path/to/file
git diff-tree --root --no-commit-id --name-status -r --find-renames ROOT_REF
git diff --cached --name-status
git status --short
git diff
```
