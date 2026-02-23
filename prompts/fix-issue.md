---
name: fix-issue
description: Fix a specific GitHub issue using the auto-issue-fixer skill. Implements TDD, creates PR, handles feedback autonomously.
arguments:
  - name: ISSUE_NUMBER
    required: true
    description: The GitHub issue number to fix (e.g., 1198)
  - name: AUTO_MERGE
    required: false
    description: Automatically merge PR when complete (true/false, default false)
  - name: DRY_RUN
    required: false
    description: Analyze and plan without implementing (default false)
  - name: MAX_FEEDBACK_ITERATIONS
    required: false
    description: Maximum rounds of PR feedback to process (default 3)
---

# Fix Issue

Fix a specific GitHub issue using the auto-issue-fixer skill.

## Usage

```bash
# Fix issue #1198
/fix-issue 1198

# Fix issue with auto-merge enabled
/fix-issue 1198 --auto-merge

# Dry run - analyze without implementing
/fix-issue 1198 --dry-run
```

## What This Does

This command invokes the `auto-issue-fixer` skill with the specified issue number, skipping the discovery and prioritization phases:

1. **Loads the specified issue** directly from GitHub
2. **Creates a worktree** for isolated development
3. **Plans and implements** the fix using TDD (Red-Green-Refactor)
4. **Creates a PR** and requests review
5. **Monitors feedback** (CI failures, code reviews, bot reviews)
6. **Addresses all feedback** autonomously
7. **Notifies you** when ready for final review (or auto-merges if enabled)

## Prerequisites

- `gh` CLI authenticated with repo access
- Git repository with GitHub remote
- Issue must exist and be open

## Examples

```bash
# Basic usage - fix issue and leave PR for manual merge
/fix-issue 42

# Fully autonomous - fix and merge when ready
/fix-issue 42 --auto-merge

# Just analyze without making changes
/fix-issue 42 --dry-run

# Allow more feedback iterations before escalating
/fix-issue 42 --max-feedback-iterations 5
```

## Skill Reference

This command is a convenience wrapper for:

```bash
/auto-issue-fixer --issue-number <ISSUE_NUMBER> [options]
```

See the [auto-issue-fixer skill](../skills/auto-issue-fixer/SKILL.md) for full documentation.
