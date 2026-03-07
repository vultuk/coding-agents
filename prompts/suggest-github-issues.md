---
name: suggest-github-issues
description: Analyse the codebase for security fixes, code quality improvements, and system enhancements. Drafts evidence-backed GitHub issues and creates them when requested.
arguments:
  - name: SCOPE
    required: false
    description: Path or pattern to analyse (defaults to entire repository)
  - name: CATEGORIES
    required: false
    description: Categories to focus on (security, code-quality, enhancement, all)
---

# Suggest GitHub Issues

Analyse the entire codebase in detail and produce actionable, evidence-backed GitHub issue proposals.

## Codex Execution Strategy

This workflow is highly parallelisable, but only the evidence gathering should be parallel by default.

- Use `multi_tool_use.parallel` for independent category scans and repository reads.
- Use `spawn_agent` only for bounded sidecar audits when the category is large enough to justify delegation.
- Keep deduplication, prioritisation, and issue drafting in the main run so the final issue list stays consistent.
- Use `functions.exec_command` for `gh issue create` only after the evidence set and dedupe pass are complete.

## Grounding and Creation Rules

- Every proposed issue must cite concrete repository evidence such as `file:line`, failing command output, or a clearly named affected component.
- If a finding is plausible but not yet well supported, keep it in the report as `[needs-validation]` instead of creating an issue.
- If the user asked only for suggestions, stop at the preview/report stage.
- Create GitHub issues only when the user explicitly asked for creation or the workflow is running in an automation context that already implies creation.

## Completion Contract

- Treat the task as incomplete until each requested category has been analysed, deduplicated, and either drafted or explicitly marked `[blocked]`.
- Do not create overlapping issues for the same root problem.
- Before creating anything remotely, re-check that the final title/body/labels still match the deduplicated finding set.

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

For each finding, prepare a **concise and well-documented GitHub issue** including:

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

Ensure all proposed issues are:
- Distinct (no overlapping scope)
- Relevant to the actual codebase
- Actionable with clear next steps
- Prioritised appropriately

Provide a summary table:

| # | Type | Priority | Title | Effort |
|---|------|----------|-------|--------|
| 1 | security | high | [Title] | medium |
| 2 | code-quality | medium | [Title] | small |
| ... | ... | ... | ... | ... |

If issues were created, append the created issue numbers/URLs.
If issues were only drafted, mark each row as `draft`.

## Related Skills

For deeper analysis in specific areas, consider:
- [code-audit](../skills/code-audit/SKILL.md): Full audit report with scoring
- [race-condition-audit](../skills/race-condition-audit/SKILL.md): Concurrency-specific issues
