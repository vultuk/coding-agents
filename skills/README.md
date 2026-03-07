# Codex + Claude Code Skills

This repository contains reusable skills for Codex and Claude Code workflows. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md) for dual-mode tool mapping and execution notes.

## Current Skill Catalogue

| Skill | Purpose |
|-------|---------|
| `auto-issue-fixer` | End-to-end GitHub issue automation with prioritisation, TDD, PR creation, and feedback handling |
| `cleanup-issue` | Merge-ready issue cleanup, worktree removal, branch cleanup, and repo reset to a safe state |
| `code-audit` | Broad code audits with prioritised findings and optional issue creation |
| `create-retrospective` | Evidence-backed incident retrospectives with optional GitHub Discussions publishing |
| `dashboard-designer` | Dashboard UX review and implementation using embedded playbooks |
| `design-principles-enforcer` | Pass/fail design-principles audits with remediation plans |
| `fix-issue` | Single-issue implementation with strict local TDD and manual git/PR handoff |
| `generate-issue` | Draft or create repository-aware implementation issues |
| `pr-feedback-workflow` | Continuous PR feedback and CI handling loop |
| `prompt-optimizer` | Rewrite rough prompts into stronger GPT-5.4-style prompt contracts |
| `race-condition-audit` | Concurrency and race-condition analysis across supported languages |
| `review-changes` | One high-signal consolidated review for diffs, commits, or PRs |
| `rust-best-practices-enforcer` | Rust handbook enforcement with automated checker integration |

## Repo Expectations

- Skills should define clear inputs, execution boundaries, and completion criteria.
- Prefer evidence-backed findings over generic advice.
- Gate remote side effects such as issue creation, publishing, or comments behind explicit user intent or workflow context.
- Keep SKILL bodies concise and push detailed references into `references/` when possible.

## Requirements

- Codex CLI or Claude Code
- Git
- GitHub CLI (`gh`) authenticated for GitHub-related skills
- Any tool-specific prerequisites declared in each `SKILL.md`

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
