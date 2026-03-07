---
name: fix-issue
description: Fix GitHub issues with strict TDD and local validation while leaving git/PR operations to the user. Use when asked to implement a specific GitHub issue or run `/fix-issue` without automated branching, committing, or PR creation.
---

# Fix Issue

Implement a single GitHub issue with a strict TDD workflow and leave the issue in a handoff-ready state.

## Require Inputs and Preconditions

- Require `ISSUE_NUMBER`.
- Accept optional flags: `--dry-run`.
- Require authenticated `gh` and a clean, deterministic local git workflow.

## Enforce Hard Constraints

1. Keep execution local to implementation and validation steps.
2. Never commit obvious secrets (`.env`, keys, tokens, credentials).
3. Keep scope limited to the target issue unless the user asks for broader work.
4. Use `rg` instead of `grep` for shell text search and filtering.
5. Stop with a concise explanation if the issue is closed.

## Grounding and Verification Rules

- Base requirements and acceptance criteria on the GitHub issue, nearby code, tests, and repository conventions gathered in this run.
- If an implementation detail is inferred rather than stated explicitly, label it as an assumption in the handoff.
- Treat the task as incomplete until implementation, local validation, and secret scanning have all passed or are explicitly `[blocked]`.
- Before finalizing, verify the reported test/lint/typecheck/build results match the commands that actually ran.

## Deliver Completion State

At successful completion:

- Current checkout context is unchanged (no new worktree, no new branch).
- Code changes are implemented and locally validated.
- Changes are left uncommitted for the user to review.
- Workflow ends with a manual git/PR handoff summary.
- Return a concise handoff summary with suggested next commands.

## Execute Workflow

### Phase 1: Load and Prepare

1. Read issue details:

```bash
gh issue view "$ISSUE_NUMBER" --json number,title,body,state,url,labels
```

2. Apply guard rails:
- Stop if issue is closed.
- Stop if working tree contains unrelated dirty changes; report dirty paths.

3. Capture local git context without changing it:

```bash
git fetch origin
START_BRANCH=$(git branch --show-current)
git status --short
```

### Phase 2: Analyze in Parallel

Run parallel analysis for:

- requirements extraction (acceptance criteria, constraints, edge cases)
- codebase mapping (likely files, tests, configs)
- pattern lookup (existing implementations to mirror)

Synthesize the findings into a concrete RED -> GREEN -> REFACTOR plan.

### Phase 3: Implement with TDD

#### RED

```bash
# Add or adjust tests for expected behaviour
{TEST_COMMAND}
# Expect failing tests
```

#### GREEN

```bash
# Implement minimum code to satisfy tests
{TEST_COMMAND}
# Expect targeted tests passing
```

#### REFACTOR

```bash
{TEST_COMMAND} && {LINT_COMMAND} && {TYPECHECK_COMMAND} && {BUILD_COMMAND}
```

### Phase 4: Validate and Safety-Check

Run full validation and scan working diff for obvious secret patterns:

```bash
{TEST_COMMAND}
{LINT_COMMAND}
{TYPECHECK_COMMAND}
{BUILD_COMMAND}
git diff | rg -e "(AKIA|sk-|ghp_|password\\s*=|secret\\s*=|api[_-]?key\\s*=|token\\s*=)" && exit 1
```

Retry transient failures automatically up to 3 attempts with short backoff.

### Handle Ambiguity Before Asking the User

Before escalation:

1. Re-read issue body and comments.
2. Re-check nearby code and tests for local conventions.
3. Proceed with highest-confidence interpretation.

Ask the user only if material ambiguity remains.

### Phase 5: Prepare Handoff (No Commit/PR Actions)

Summarize outputs for the user:
- files changed
- test/lint/typecheck/build results
- risks or follow-up items

Provide suggested manual next steps, but do not execute them:
- create a branch if the user wants isolated history
- commit with a message referencing `#$ISSUE_NUMBER`
- push and open a PR if the user wants remote review

### Phase 6: Optional Issue Update (Only If User Explicitly Asks)

If explicitly requested, post a status comment describing local completion:

```bash
CURRENT_BRANCH=$(git branch --show-current)
gh issue comment "$ISSUE_NUMBER" -b "Implemented locally and validated.

- Branch: \`$CURRENT_BRANCH\`
- Commit: (not created by this skill)
- PR: (not created by this skill)
- Status: Ready for manual git/PR steps"
```

Do not close the issue in this skill.

### Optional Phase 7: Start PR Feedback Loop

If the user explicitly provides an existing PR and asks for automation, hand off to PR-feedback processing for that PR.

## Apply Escalation Rules

Escalate only after bounded retries:

| Condition | Attempts |
|-----------|----------|
| Tests, lint, typecheck, or build still failing | 3 |
| Material ambiguity after issue and code review | 1 clarification |
| Security-sensitive change required | immediate |

Escalation output:

```markdown
## Escalation Required

Issue: #$ISSUE_NUMBER
Reason: [specific blocker]

What I tried:
1. [attempt]
2. [attempt]
3. [attempt]

Suggested next step:
[actionable recommendation]
```

## Handle Out-of-Scope Discovery

If unrelated issues are found, create follow-up issues instead of broadening the issue implementation:

```bash
gh issue create \
  --title "Follow-up: [title]" \
  --body "Discovered while implementing #$ISSUE_NUMBER.

## Context
[what was found]

## Related
- Parent issue: #$ISSUE_NUMBER" \
  --label "enhancement,discovered"
```

## Use Quick Start Invocations

```bash
# Full issue fix with local-only implementation
/fix-issue 123

# Plan only
/fix-issue 123 --dry-run
```

## Print Final Output Block

```text
ISSUE=#123
CHANGED_FILES=5
TESTS=pass
LINT=pass
TYPECHECK=pass
BUILD=pass
READY_FOR_MANUAL_GIT=true
```

## Final Response Contract

After printing the final output block, end with a concise local handoff summary:

- what changed,
- which validation commands passed,
- any remaining assumptions, risks, or blocked follow-up items.

Send an external notification only if a notification tool is actually configured and the user explicitly asked for it.

## Follow Guidelines

- Keep issue analysis compact; avoid raw JSON dumps in normal flow.
- Keep handoff notes focused on what changed, why, and what remains manual.
- Do not inspect unrelated issues or pull requests unless requested.
