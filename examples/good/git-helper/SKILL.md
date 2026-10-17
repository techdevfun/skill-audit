---
name: git-helper
description: Help with git branches, rebasing, stashing and resolving merge conflicts safely. Use when the user is stuck on a git workflow.
version: "1.0.0"
---

# Git Helper

1. Ask which branch and what state the working tree is in before suggesting commands.
2. Prefer non-destructive commands first (`git status`, `git log`, `git diff`).
3. Never run `git reset --hard` or `git push --force` without explicit confirmation.
