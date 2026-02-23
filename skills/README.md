# Codex + Claude Code Skills

A collection of custom skills that automate common development workflows in both Codex CLI and Claude Code.
See [`../COMPATIBILITY.md`](../COMPATIBILITY.md) for dual-mode notes.

## Skills

### fix-github-issue

Load a GitHub issue, create an isolated worktree, plan the implementation, and submit a PR.

**Triggers:**
- "Fix issue #123"
- "Implement GitHub issue 456"
- "Work on issue #78"

**Workflow:**
1. Creates isolated git worktree for the issue (or direct branch with `--no-worktree`)
2. Fetches issue context (description, comments, labels)
3. Explores codebase and creates implementation plan
4. Implements changes after confirmation
5. Commits and opens PR with proper issue linking

**Features:**
- Validates prerequisites (gh auth, git repo, origin remote)
- Handles uncommitted changes gracefully
- Supports both worktree and direct branch workflows
- Auto-detects default branch (main/master)

### pr-feedback-workflow

Process all PR feedback in one pass - review comments and CI failures together.

**Triggers:**
- "Address the PR feedback"
- "Fix the review comments"
- "Handle the CI failures on this PR"
- "Process the PR reviews"

**Workflow:**
1. Gathers all review comments and CI failure logs
2. Categorises feedback (code fix, explanation needed, out of scope)
3. Creates unified action plan
4. Applies fixes, replies to reviewers, resolves threads
5. Posts summary comment

**Features:**
- Handles pagination for large PRs (>100 threads)
- Rate limit checking before API calls
- Guidance for handling conflicting reviewer opinions
- Templates for diplomatic responses

### cleanup-issue

Clean up after an issue PR is merged.

**Triggers:**
- "Clean up issue #123"
- "Finish up the issue"
- "The PR was approved, clean up"

**Workflow:**
1. Merges PR if approved but not yet merged (with confirmation)
2. Removes the worktree
3. Deletes the local branch
4. Updates main branch
5. Starts fresh session

**Features:**
- Confirmation prompts before destructive actions
- `--force` flag for automation
- Helpful diagnostics when PR can't be merged

### code-audit

Perform comprehensive code audits and generate structured reports.

**Triggers:**
- "Audit this codebase"
- "Review the code quality"
- "Check for security issues"
- "Generate a code audit report"

**Analysis categories:**
- Architecture and component structure
- Bugs and race conditions
- SOLID/DRY violations
- Security vulnerabilities
- Performance issues

**Features:**
- Time estimates by project size
- Security-focused audit mode
- Severity scoring (P0-P3)
- Automatic GitHub issue creation

**Output:** Markdown report with severity-prioritised recommendations and optional GitHub issue creation.

### auto-issue-fixer

Automate the complete GitHub issue lifecycle with TDD and draft PR workflow.

**Triggers:**
- "Auto fix issues"
- "Process GitHub issues"
- "Fix next issue"

**Workflow:**
1. Fetches and prioritizes all open issues by importance and speed
2. Selects highest-priority issue automatically
3. Implements fix using TDD (Red-Green-Refactor)
4. Creates draft PR with comprehensive description
5. Monitors CI and addresses failures automatically
6. Handles review feedback autonomously
7. Marks PR ready when all checks pass

**Features:**
- Fully autonomous operation (no confirmation prompts)
- Draft PR workflow - only marked ready when complete
- Extensive subagent usage for context efficiency
- Configurable feedback iteration limits
- Automatic escalation on defined failure conditions
- Comprehensive prioritization algorithm

### race-condition-audit

Systematic identification of race conditions and concurrency bugs.

**Triggers:**
- "Find race conditions in this code"
- "Audit the concurrent code"
- "Check for thread safety issues"
- "Look for data races"

**Supports:** TypeScript, JavaScript, Python, Go, Rust, C++, Java, Kotlin

**Detects:**
- Check-then-act races
- Read-modify-write without atomics
- Lazy initialisation races
- Deadlocks and lock ordering issues
- Collection mutation during iteration
- Async/await races

**Features:**
- Language-specific reference guides
- Severity and risk scoring
- Testing recommendations (TSan, go race, etc.)

## Requirements

- Codex CLI or Claude Code
- GitHub CLI (`gh`) authenticated for GitHub-related skills
- Git
- jq (for JSON parsing in scripts)

## Installation

- Claude Code: `~/.claude/skills/`
- Codex CLI: `$CODEX_HOME/skills` (often `~/.codex/skills`)

## Skill Format

All skills use YAML frontmatter for metadata:

```yaml
---
name: skill-name
description: What the skill does
triggers:
  - "trigger phrase 1"
  - "trigger phrase 2"
prerequisites:
  - required tool 1
  - required tool 2
arguments:
  - name: ARG_NAME
    required: true/false
    description: What the argument is for
---
```
