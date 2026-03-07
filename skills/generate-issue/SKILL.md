---
name: generate-issue
description: Draft and create GitHub issues from user requests using repository-aware analysis, affected-component inference, effort estimation, and canonical issue formatting. Use when asked to create, draft, or refine an issue for bugs, enhancements, performance work, security work, documentation, or code-quality tasks.
---

# Generate Issue

Draft or create a clear, implementation-ready GitHub issue with high automation and minimal back-and-forth.

## Follow Core Principles

1. Execute directly for the current request.
2. Infer impacted components from repository evidence.
3. Estimate effort from concrete codebase scope.
4. Ask for confirmation only when ambiguity or risk is high.
5. Keep execution least-invasive and prefer read-only analysis unless local changes are needed to improve issue quality.

## Grounding and Creation Rules

- Base issue scope, acceptance criteria, and impacted components on repository evidence gathered in this run.
- Attach concrete evidence such as `file:line`, command output, or named modules/components whenever possible.
- If a requirement is inferred rather than directly supported, label it as an inference.
- If the user asked to draft or refine only, stop before `gh issue create`.
- Only create the GitHub issue when the user explicitly asked for creation or the surrounding workflow already implies creation.

## Use Required Output Contracts

When invoked by another agent with pre-filled context, return exactly:

```text
ISSUE CREATED
Number: #<number>
URL: <issue-url>
Title: <title>
Labels: <labels>
```

After standard creation, print:

```text
ISSUE CREATED
Number: #789
URL: https://github.com/owner/repo/issues/789
Title: fix: resolve authentication timeout
Type: bug
Labels: bug, security
Complexity: Medium (estimated 4-8 hours)
Components: src/auth/*, src/api/middleware.ts
```

## Run Workflow

### Phase 1: Build repository awareness in parallel

Collect:
- Top-level structure and key entry points
- Test layout
- Conventions from README, CONTRIBUTING, and architecture docs
- Issue and PR links explicitly supplied by the user

### Phase 2: Take direct issue path

Skip duplicate screening across open and closed issues or PRs unless the user explicitly asks for deduplication analysis.

### Phase 3: Analyse request

Infer:
- Issue type: `bug`, `enhancement`, `documentation`, `performance`, `security`, `code-quality`
- Severity: `critical`, `high`, `medium`, `low`
- Candidate acceptance criteria from expected behaviour in the request
- Likely components from paths, modules, and feature keywords

Use detection heuristics:
- `crash`, `error`, `broken`, `regression` -> `bug`
- `add`, `support`, `feature`, `new` -> `enhancement`
- `slow`, `optimise`, `memory`, `CPU` -> `performance`
- `vulnerability`, `CVE`, `injection`, `auth bypass` -> `security`
- `typo`, `README`, `docs`, `clarify` -> `documentation`

### Phase 4: Infer affected components in parallel

Search codebase to identify:
1. Likely files
2. Involved modules or packages
3. Related tests
4. Relevant configs

Use `rg` for code search and provide concise evidence with `file:line`.

### Phase 5: Estimate effort

Map scope to complexity:
- `Trivial`: single file, under 20 lines, no test work, under 1 hour
- `Small`: 1-3 files, under 100 lines, minor test updates, 1-4 hours
- `Medium`: 3-7 files, 100-500 lines, new tests needed, 4-16 hours
- `Large`: 7+ files, 500+ lines, architectural impact, 2-5 days
- `Epic`: cross-cutting work, migrations, or breaking contracts, 1+ weeks

### Phase 6: Draft issue body with canonical structure

Include every section below in this order:
- `## Summary`
- `## Context / Current Behaviour (confirmed)`
- `## Problem Statement`
- `## Goals`
- `## Non-Goals`
- `## Definitions (the contract we will implement)`
- `## Proposed Changes`
- `## Acceptance Criteria`
- `## Test Plan`
- `## Rollout Plan`
- `## Notes / Open Questions (answer in implementation)`
- `## Deliverables`
- `## Definition of Done`

Use this body template:

```markdown
## Summary

[1-2 sentence description]

## Context / Current Behaviour (confirmed)

## Problem Statement

## Goals

## Non-Goals

## Definitions (the contract we will implement)

### 1)

- Definition:
- Evidence:

### 2)

- Definition:
- Evidence:

### 3)

- Definition:
- Evidence:

## Proposed Changes

### A)

1. ...

### B)

1. ...

### C) (if required)

1. ...

## Acceptance Criteria

- [ ] ...
- [ ] ...
- [ ] Tests added or updated
- [ ] Documentation updated (if public API)

## Test Plan

### Unit Tests

- [ ] ...

### Integration Tests

- [ ] ...

### Load/Soak (optional but recommended)

- [ ] ...

## Rollout Plan

1. ...

## Notes / Open Questions (answer in implementation)

- [ ] ...

## Deliverables

- [ ] Code changes in affected components
- [ ] Schema or contract changes (if required)
- [ ] Updated payloads or contracts (if required)
- [ ] Unit and integration tests
- [ ] Release notes and config documentation (if required)

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests green in CI
- [ ] Metrics or observability verified where applicable
- [ ] No behavioural regressions under default config

## References (optional)

- User-provided issue and PR links only
```

### Phase 7: Select labels

Auto-apply based on request:
- `security`
- `bug`
- `code-quality`
- `enhancement`
- `documentation`
- `performance`

Apply additional labels by complexity:
- `good-first-issue` for trivial isolated work
- `help-wanted` for medium or larger work with clear scope

### Phase 8: Confirm only when needed

Skip confirmation when requirements are clear and low risk.

Request confirmation when:
- Multiple interpretations exist
- Complexity is `Large` or `Epic`
- Security implications need explicit verification

Use this preview format:

```text
## Issue Preview

**Title**: [title]
**Type**: [bug|enhancement|...]
**Labels**: [label1, label2]
**Complexity**: [estimate]

**Summary**:
[first paragraph of body]

**Components**:
- path/to/file.ts
- path/to/other.ts

Create this issue? (yes/edit/cancel)
```

### Phase 9: Create issue

Create the issue using GitHub CLI with a concise prefixed title and the prepared body file:

```bash
gh issue create \
  --title "[type]: [concise title]" \
  --body-file /tmp/issue-body.md \
  --label "$LABELS"
```

Capture and report the new issue URL and number after creation.

## Apply Automatic Enhancements

- Assign active milestone when appropriate.
- Suggest assignee from CODEOWNERS or ownership signals for impacted paths.

## Verification Loop

Before finalizing:
- verify the title, labels, complexity, and component list still match the drafted body,
- verify every acceptance criterion is supported by the summary/problem/proposed-change sections,
- if an issue was created, verify the returned issue number and URL from `gh issue create`.

## Final Response Contract

End with either:
- the exact created-issue output block, or
- this exact draft block when no issue was created:

```text
ISSUE DRAFT
Title: <title>
Labels: <labels>
Complexity: <complexity>
Components: <components>
```

Send an external notification only if a notification tool is configured and the user explicitly asked for it.

## Follow Quality Rules

- Provide evidence-based suggestions with `file:line`.
- Prefer compact summaries over raw `gh` JSON output.
- Use UK spelling in issue content.
- Keep confirmation minimal for clear requests.
- Include effort estimates to aid prioritisation.
- Include only issue and PR links explicitly supplied by the user.
- Use `rg` instead of `grep` for shell search and filtering.
