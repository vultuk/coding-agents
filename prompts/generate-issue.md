---
name: generate-issue
description: Create a well-documented GitHub issue from provided details. Formats the issue with clear title, description, reproduction steps, and acceptance criteria.
arguments:
  - name: ISSUE_DETAILS
    required: true
    description: Description of the issue, bug, or feature to create
---

# Generate GitHub Issue

Create a **concise and well-documented GitHub issue** using the `gh issue create` command.

## Input

The `$ISSUE_DETAILS` argument should contain the raw information about the issue. This prompt will structure it properly.

## SubAgent Strategy

This is a **simple single-step workflow** that typically doesn't require SubAgents. However, if you need to gather context before creating the issue:

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### Optional Pre-Issue Research

If `$ISSUE_DETAILS` is vague or requires codebase investigation:

```
# Gather context first (if needed):

Task(subagent_type="Explore", prompt="Investigate the issue described: <ISSUE_DETAILS>
Find: affected files, related code, potential root cause, existing similar issues.
Return: structured findings for issue creation.")
```

For straightforward issues with clear details, proceed directly to issue creation without SubAgents.

## Issue Structure

Include:
- A clear, actionable title
- A detailed description (what, why, how to fix)
- Reproduction steps or affected components if relevant
- Acceptance criteria

## Labels

Assign appropriate **labels/tags** when creating the issues:
- `security` for Security Fixes
- `bug` for Bug Reports
- `code-quality` for Code Quality Fixes
- `enhancement` for System Improvements
- `documentation` for Documentation updates
- `performance` for Performance issues

## Command Format

```bash
gh issue create \
  --title "<ISSUE_TITLE>" \
  --body "<ISSUE_DESCRIPTION>" \
  --label "<label1,label2>"
```

## Issue Body Template

```markdown
## Summary

[1-2 sentence description]

## Details

[Detailed explanation of the issue]

## Reproduction Steps (for bugs)

1. [Step 1]
2. [Step 2]
3. [Expected vs actual result]

## Affected Components

- [Component/file 1]
- [Component/file 2]

## Acceptance Criteria

- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] Tests added/updated

## Additional Context

[Screenshots, logs, related issues]
```

## Output

After creating the issue, report:
- Issue number and URL
- Labels applied
- Assignees (if any)
