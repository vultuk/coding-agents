---
name: code-audit
description: Perform comprehensive code audits on repositories or directories. Use when asked to audit code, review a codebase, analyze code quality, find bugs, check for security issues, review architecture, check SOLID/DRY compliance, or generate a code audit report. Produces well-formatted markdown reports with prioritized recommendations.
triggers:
  - "audit this codebase"
  - "review code quality"
  - "check for security issues"
  - "generate audit report"
  - "find bugs"
  - "check SOLID compliance"
  - "review architecture"
prerequisites:
  - gh (GitHub CLI, authenticated) - for creating issues
  - git - for repository context
arguments:
  - name: SCOPE
    required: false
    description: Path or pattern to audit (defaults to entire repository)
  - name: FOCUS
    required: false
    description: Specific concern to focus on (security, performance, architecture, etc.)
---

# Code Audit

Perform comprehensive code audits and generate structured markdown reports.

**Codex note:** Translate old `Task(...)` references into Codex-native execution: `functions.exec_command` for shell work, `multi_tool_use.parallel` for independent reads, `spawn_agent` for bounded sidecar analysis, and `apply_patch` for manual edits. See [`../../COMPATIBILITY.md`](../../COMPATIBILITY.md).

## Grounding and Side-Effect Rules

- Every finding must be backed by concrete code evidence, not style preference alone.
- If a claim is an inference rather than a directly observed fact, label it as an inference.
- Default to producing the audit report first.
- Create GitHub issues only when the user explicitly asked for issue creation or the surrounding workflow already implies it.
- Before creating issues, deduplicate overlapping findings and verify each issue body still matches the final report wording.

## Workflow

1. **Scope**: Determine target (full repo, specific path, or focused concern)
2. **Discovery**: List and categorise source files
3. **Analysis**: Evaluate each category systematically
4. **Report**: Generate markdown report using template format
5. **GitHub Issues (optional)**: When requested, create issues using `scripts/create_issue.sh`:
   - First: Create individual issues for each actionable recommendation
   - Then: Create the full audit report with subtasks linking to each issue

## Time Estimates

| Scope | Estimated Time |
|-------|---------------|
| Single file | 5-10 minutes |
| Single module/package | 15-30 minutes |
| Small project (<10k LOC) | 30-60 minutes |
| Medium project (10-50k LOC) | 1-2 hours |
| Large project (>50k LOC) | Split into multiple audits |

For large projects, consider:
- Auditing by module/package
- Focusing on specific concerns (security-only, performance-only)
- Auditing recently changed files only

## Analysis Categories

| Category | What to Look For |
|----------|------------------|
| Architecture | Separation of concerns, component structure, dependencies |
| Bugs | Race conditions, null checks, resource leaks, edge cases |
| SOLID Violations | SRP (god classes), OCP, LSP, ISP, DIP issues |
| DRY Violations | Duplicated logic, repeated patterns, copy-paste code |
| Best Practices | Magic numbers, missing docs, broad exceptions |
| Security | Input validation, credential handling, injection risks |
| Performance | O(n) issues, unnecessary copies, inefficient algorithms |
| Good Practices | Highlight what the code does well |

## Severity Levels

| Level | Criteria |
|-------|----------|
| P0/Critical | Race conditions, security vulnerabilities, data loss risks |
| P1/High | Major bugs, architectural issues, memory leaks |
| P2/Medium | Code quality issues, moderate violations |
| P3/Low | Minor improvements, nice-to-have refactors |

## Scoring

Rate each applicable category out of 10:

- Architecture, Thread Safety, Error Handling
- DRY Compliance, SOLID Compliance
- Security, Performance, Testability

Overall score: weighted average (bugs and security weighted higher).

## Security-Focused Audit

When focusing on security, prioritise:

1. **Input Validation**
   - User input sanitisation
   - SQL/NoSQL injection vectors
   - Command injection risks
   - Path traversal vulnerabilities

2. **Authentication & Authorisation**
   - Session management
   - Token handling
   - Permission checks
   - Privilege escalation paths

3. **Data Protection**
   - Credential storage
   - Sensitive data exposure
   - Encryption usage
   - Logging of sensitive data

4. **Dependencies**
   - Known vulnerabilities (CVEs)
   - Outdated packages
   - Typosquatting risks

## Report Format

See [references/report-template.md](references/report-template.md) for the exact output structure.

Key formatting rules:

- Two-column tables for issue metadata (severity, location, impact, recommendation)
- Code blocks with language hints for all code examples
- Horizontal rules between major sections
- ASCII diagrams in code blocks for architecture
- Summary statistics table at the end
- Prioritised recommendations (P0/P1/P2/P3)
- Never use em-dashes

## Output

### Step 1: Produce the Audit Report

Always produce the full markdown audit report first using the template in [references/report-template.md](references/report-template.md).

### Step 2: Create Individual Recommendation Issues (only when requested)

For each actionable recommendation, create a separate issue using the format in [references/issue-template.md](references/issue-template.md). Capture the returned issue URL for each.

```bash
bash scripts/create_issue.sh \
  --project "[Project Name]" \
  --title "[Brief issue title]" \
  --label "code-audit,priority:[level],[category]" \
  --body "$ISSUE_BODY"
```

Priority labels:
- P0/Critical: `priority:critical`
- P1/High: `priority:high`
- P2/Medium: `priority:medium`
- P3/Low: `priority:low`

Category labels (use as appropriate):
- `security`, `performance`, `bug`, `technical-debt`
- `architecture`, `observability`, `testing`, `documentation`

### Step 3: Create Full Audit Report with Subtasks (only when requested)

Append a "Related Issues" section to the full report with subtasks linking to each individual issue:

```markdown
## Related Issues

- [ ] #123 - Fix race condition in data index map
- [ ] #124 - Add thread safety to RedisClient
- [ ] #125 - Extract side validation utility
- [ ] #126 - Add metrics and observability
```

Then create the main audit issue:

```bash
bash scripts/create_issue.sh \
  --project "[Project Name]" \
  --title "Code Audit Report - [Project] - [Date]" \
  --label "code-audit" \
  --body "$FULL_REPORT_WITH_SUBTASKS"
```

With a specific repository, add `--repo "owner/repo"`.

### When to Split Audits

Create separate audit reports when:
- Different parts of the codebase have different owners
- Findings span multiple priority levels with different timelines
- The report exceeds ~500 lines (becomes hard to track)

If issues were created, confirm all issue URLs with the user after creation.

## Subagent Usage

Use subagents to parallelize analysis and reduce main context bloat.

### Phase 2: Parallel Analysis

For medium to large codebases, launch up to 4 Explore agents in parallel to analyze different categories simultaneously:

```
Launch parallel Explore agents:

1. Architecture Agent:
   "Analyze the codebase architecture. Look for:
   - Separation of concerns violations
   - Circular dependencies
   - Component structure issues
   - Coupling problems between modules
   Return: List of findings with file:line references and severity"

2. Security Agent:
   "Perform security analysis. Scan for:
   - Input validation gaps (SQL injection, XSS, command injection)
   - Credential handling issues (hardcoded secrets, improper storage)
   - Authentication/authorization flaws
   - OWASP Top 10 vulnerabilities
   Return: List of findings with file:line references and severity"

3. Performance Agent:
   "Analyze performance issues. Find:
   - O(n²) or worse algorithms
   - Unnecessary object copies or allocations
   - N+1 query patterns
   - Missing caching opportunities
   - Inefficient data structures
   Return: List of findings with file:line references and severity"

4. Code Quality Agent:
   "Check code quality and best practices. Look for:
   - SOLID principle violations (god classes, tight coupling)
   - DRY violations (duplicated logic, copy-paste code)
   - Magic numbers and missing documentation
   - Broad exception handling
   - Resource leaks
   Return: List of findings with file:line references and severity"
```

Each agent returns structured findings. Main context synthesizes into final report.

**Benefits:**
- 4x faster analysis on large codebases
- Exploration output stays in subagent context (reduces token usage)
- Main context receives only synthesized findings

### Phase 5: Background Issue Creation (optional)

After generating the report, create GitHub issues in background:

```
Launch background agent:
"Create GitHub issues for each audit finding using scripts/create_issue.sh.
Findings to create:
[List of findings with titles, labels, and bodies]

For each finding:
1. Create issue with appropriate labels (priority:X, category)
2. Capture the issue URL
3. Return all created issue URLs when complete"
```

Main context can continue summarizing results while issues are created.

**When to use subagents:**
- Codebase > 5,000 LOC: Use parallel analysis agents
- More than 5 issues to create: Use background issue creation
- Time-sensitive audit: Always use parallel agents

**When to skip subagents:**
- Single file audit
- Focused audit on specific concern (one category only)
- Small codebase < 1,000 LOC

## Related Skills

- [race-condition-audit](../race-condition-audit/SKILL.md): Deep-dive on concurrency issues
- [fix-issue](../fix-issue/SKILL.md): Implement fixes from audit recommendations
