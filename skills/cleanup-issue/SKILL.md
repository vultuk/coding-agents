---
name: cleanup-issue
description: Clean up after an issue PR is merged. Merges the PR if needed, removes the worktree, deletes the branch, updates main, and starts a fresh session. Use when asked to clean up an issue, finish an issue, or after a PR is approved.
triggers:
  - "clean up issue"
  - "finish issue"
  - "PR was approved"
  - "PR was merged"
  - "done with issue"
prerequisites:
  - gh (GitHub CLI, authenticated)
  - git
arguments:
  - name: ISSUE_NUMBER
    required: true
    description: The GitHub issue number to clean up
---

# Cleanup Issue

Finalise and clean up after an issue is complete.

## Workflow

### 1. Merge PR (if not already merged)

Check PR status and merge if approved:

```bash
scripts/cleanup-issue.sh $ISSUE_NUMBER
```

This will:
- Find the PR for the issue branch
- Check if it's already merged
- If approved but not merged, prompt for confirmation then merge it
- Remove the worktree
- Delete the local branch
- Update main
- Prune stale worktree references

**Options:**
- `--force` or `-f`: Skip confirmation prompts (useful for automation)

The script provides helpful information when the PR cannot be merged:
- **BLOCKED**: Required reviews or status checks not met
- **BEHIND**: Branch needs to be updated from base
- **DIRTY**: Merge conflicts exist

### 2. Start fresh session

After cleanup completes successfully:

- **Claude Code:** output `/new` to start a fresh session.
- **Codex:** say "Ready for next task."

## Manual Steps

If the script fails or you need manual control:

```bash
# Check PR status
gh pr view issue-$ISSUE_NUMBER --json state,mergeStateStatus

# Merge if ready
gh pr merge issue-$ISSUE_NUMBER --merge --delete-branch

# Remove worktree
git worktree remove .worktrees/issue-$ISSUE_NUMBER

# Delete local branch (if not auto-deleted)
git branch -d issue-$ISSUE_NUMBER

# Update main
git checkout main
git pull --ff-only origin main

# Prune worktree references
git worktree prune
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/cleanup-issue.sh` | Full cleanup: merge, remove worktree, update main |

## Related Skills

- [fix-github-issue](../fix-github-issue/SKILL.md): The workflow that creates the issue branch and PR
- [pr-feedback-workflow](../pr-feedback-workflow/SKILL.md): Address review comments before cleanup
