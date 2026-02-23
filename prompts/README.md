# Prompt Operations Library

## Overview

This repository contains a set of operational playbooks and prompts for running coding agent workflows. Each Markdown file captures the objective, guardrails, and expected outputs for a specific task you may encounter while assisting engineers, release managers, or product stakeholders.

## Prompt Catalogue

| File | Focus | Key Responsibilities |
|------|-------|---------------------|
| `git-pull-request.md` | Automated PR creation | From unstaged changes, infer a branch name, produce AI-authored commit/PR messaging, push, and open the PR via `gh`. Supports draft PRs. |
| `push-publish.md` | Release and publish workflow | Decide the next semantic version, update changelog and version metadata, tag and push, create a release, merge the PR, and publish if required. Includes rollback procedures. |
| `run-prompt.md` | Prompt execution logging | Log prompts to `.prompts/log.md` with metadata before running user instructions. |
| `wiki-changelog.md` | Wiki changelog automation | Summarise merged PRs per day in plain English, update `Changelog.md` in the GitHub Wiki, and push the changes idempotently. |
| `fix-github-actions.md` | CI failure resolution | Identify failing workflows, diagnose issues, apply fixes, and verify success. Includes common failure patterns. |
| `generate-issue.md` | Issue creation | Create well-documented GitHub issues from provided details with proper labels and acceptance criteria. |
| `setup-project.md` | Project scaffolding | Set up a production-ready monorepo with Nx, Expo, Next.js, Hono, and supporting infrastructure. |
| `suggest-github-issues.md` | Codebase analysis | Analyse codebase and create issues for security fixes, code quality improvements, and system enhancements. |

## Prompt Format

All prompts use YAML frontmatter for metadata:

```yaml
---
name: prompt-name
description: What the prompt does
arguments:
  - name: ARG_NAME
    required: true/false
    description: What the argument is for
---
```

Arguments marked as `required: true` must always be provided when using the prompt.

## Working With These Prompts

- Treat each file as an authoritative SOP: follow the sequence, guardrails, and reporting expectations it outlines.
- Many prompts assume access to standard tooling such as Git, the GitHub CLI (`gh`), and project-specific scripts; ensure you meet the prerequisites before execution.
- Maintain professionalism and accuracy - most instructions target high-scrutiny workflows like release management or executive reporting.
- For Codex CLI vs Claude Code differences (subagents, headless execution), see [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

## Related Skills

For more complex, multi-phase workflows, see the [skills repository](../skills/README.md):

- `fix-github-issue`: Full issue-to-PR workflow with worktrees
- `pr-feedback-workflow`: Process PR review comments and CI failures
- `cleanup-issue`: Post-merge cleanup
- `code-audit`: Comprehensive code auditing with reports
- `race-condition-audit`: Concurrency bug detection

## Extending The Library

When adding new prompts:

1. Use YAML frontmatter with name, description, and arguments
2. Keep instructions concise, specific, and actionable
3. Note any tooling assumptions, environment variables, or safety checks
4. Describe the expected deliverables so operators can validate their work quickly
5. Include error handling and edge cases
6. Add cross-references to related prompts or skills

By following these guidelines, contributors can continue to grow a reliable reference set for complex operational tasks.
