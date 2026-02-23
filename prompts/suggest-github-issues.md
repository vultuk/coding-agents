---
name: suggest-github-issues
description: Analyse the entire codebase and identify security fixes, code quality improvements, and system enhancements. Creates well-documented GitHub issues for each finding.
arguments:
  - name: SCOPE
    required: false
    description: Path or pattern to analyse (defaults to entire repository)
  - name: CATEGORIES
    required: false
    description: Categories to focus on (security, code-quality, enhancement, all)
---

# Suggest GitHub Issues

Analyse the entire codebase in detail and create actionable GitHub issues.

## SubAgent Strategy

This workflow is **highly parallelisable**. Each analysis category can run independently, and issue creation can be batched.

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### Phase 1: Parallel Category Analysis

Launch **all analysis SubAgents simultaneously**:

```
# Launch in a single message with multiple Task calls:

Task(subagent_type="Explore", prompt="SECURITY AUDIT: Analyse the codebase for security vulnerabilities. Look for:
- Input validation gaps
- Authentication/authorisation issues
- Sensitive data exposure
- Dependency vulnerabilities (check package.json, lock files)
- Injection risks (SQL, command, XSS)
- Insecure configurations
Return: List of 3+ findings with file paths, line numbers, severity, and suggested fixes.", model="sonnet")

Task(subagent_type="Explore", prompt="CODE QUALITY AUDIT: Analyse the codebase for code quality issues. Look for:
- Code duplication (DRY violations)
- Complex functions (high cyclomatic complexity)
- Missing error handling
- Inconsistent patterns
- Dead code
- Missing/outdated documentation
Return: List of 3+ findings with file paths, line numbers, and improvement suggestions.", model="sonnet")

Task(subagent_type="Explore", prompt="SYSTEM IMPROVEMENTS AUDIT: Analyse the codebase for enhancement opportunities. Look for:
- Performance optimisations
- Architectural improvements
- Scalability concerns
- Observability gaps (logging, metrics, tracing)
- Developer experience improvements
- Test coverage gaps
Return: List of 3+ findings with affected areas and implementation suggestions.", model="sonnet")
```

### Phase 2: Issue Deduplication

After all SubAgents return, consolidate findings:
- Remove duplicates across categories
- Prioritise by impact (high/medium/low)
- Ensure no overlapping scope between issues

### Phase 3: Parallel Issue Creation

Launch **issue creation SubAgents in parallel** (batch by category):

```
# Create all issues in parallel:

Task(subagent_type="Bash", prompt="Create GitHub issue using gh issue create:
Title: <ISSUE_TITLE>
Labels: security,priority:high
Body: <FORMATTED_ISSUE_BODY>")

Task(subagent_type="Bash", prompt="Create GitHub issue using gh issue create:
Title: <ISSUE_TITLE>
Labels: code-quality,priority:medium
Body: <FORMATTED_ISSUE_BODY>")

# ... repeat for all issues
```

### Alternative: Batch Issue Creation

For efficiency, use a single **Bash SubAgent** to create all issues in sequence:
```
Task(subagent_type="Bash", prompt="Create these GitHub issues in sequence using gh issue create:
1. [Issue 1 details]
2. [Issue 2 details]
...
Return: List of created issue URLs")
```

## Analysis Categories

### 1. Security Fixes (3 minimum)

Look for:
- Input validation vulnerabilities
- Authentication/authorisation gaps
- Sensitive data exposure
- Dependency vulnerabilities
- Injection risks (SQL, command, XSS)
- Insecure configurations

### 2. Code Quality Fixes (3 minimum)

Look for:
- Code duplication (DRY violations)
- Complex functions (high cyclomatic complexity)
- Missing error handling
- Inconsistent patterns
- Dead code
- Missing or outdated documentation

### 3. System Improvements (3 minimum)

Look for:
- Performance optimisations
- Architectural improvements
- Scalability concerns
- Observability gaps (logging, metrics, tracing)
- Developer experience improvements
- Test coverage gaps

## Issue Requirements

For each finding, create a **concise and well-documented GitHub issue** including:

- A clear, actionable title
- A detailed description (what, why, how to fix)
- Reproduction steps or affected components if relevant
- Acceptance criteria
- Estimated effort (small/medium/large)

## Labels

Assign appropriate **labels/tags** when creating the issues:
- `security` for Security Fixes
- `code-quality` for Code Quality Fixes
- `enhancement` for System Improvements
- Priority labels: `priority:high`, `priority:medium`, `priority:low`

## Command Format

```bash
gh issue create \
  --title "<ISSUE_TITLE>" \
  --body "<ISSUE_DESCRIPTION>" \
  --label "<security|code-quality|enhancement>,priority:<level>"
```

## Issue Body Template

```markdown
## Summary

[1-2 sentence description of the issue]

## Details

[Detailed explanation including:]
- What is the current behaviour/state
- Why it's a problem
- Where it occurs (files, line numbers)

## Suggested Fix

[Concrete implementation guidance]

## Acceptance Criteria

- [ ] [Specific criterion]
- [ ] Tests added/updated
- [ ] Documentation updated (if applicable)

## Effort Estimate

[Small (< 1 day) | Medium (1-3 days) | Large (> 3 days)]

## Related Files

- `path/to/file1.ts`
- `path/to/file2.ts`
```

## Output

Ensure all 9+ issues are:
- Distinct (no overlapping scope)
- Relevant to the actual codebase
- Actionable with clear next steps
- Prioritised appropriately

After creating issues, provide a summary table:

| # | Type | Priority | Title | Effort |
|---|------|----------|-------|--------|
| 1 | security | high | [Title] | medium |
| 2 | code-quality | medium | [Title] | small |
| ... | ... | ... | ... | ... |

## Related Skills

For deeper analysis in specific areas, consider:
- [code-audit](../skills/code-audit/SKILL.md): Full audit report with scoring
- [race-condition-audit](../skills/race-condition-audit/SKILL.md): Concurrency-specific issues
