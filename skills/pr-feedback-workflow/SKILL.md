---
name: pr-feedback-workflow
description: Process all PR feedback in one pass. Fetches review comments and CI failures together, creates a unified action plan, applies fixes, replies to reviewers, resolves threads, and posts a summary. Use when asked to address PR feedback, fix review comments, handle CI failures, or process PR reviews. Works on the current branch's open PR.
triggers:
  - "address PR feedback"
  - "fix review comments"
  - "handle CI failures"
  - "process PR reviews"
  - "respond to reviewers"
prerequisites:
  - gh (GitHub CLI, authenticated)
  - git
  - jq (for JSON parsing in scripts)
arguments:
  - name: PR_NUMBER
    required: false
    description: The PR number (auto-detected from current branch if not provided)
---

# PR Feedback Workflow

Gather all PR feedback (review comments + CI failures), plan holistically, then execute.

**Codex note:** This skill references Claude Code subagents (`Task(...)`). In Codex, run the equivalent steps with tool calls (for example `functions.shell_command` and `multi_tool_use.parallel`) or run them sequentially. See [`../../COMPATIBILITY.md`](../../COMPATIBILITY.md).

## Phase 1: Gather Context

Run the script to collect all feedback:

```bash
scripts/load-pr-feedback.sh
```

This fetches:
- PR number, title, and current branch
- All conversation comments (general PR discussion)
- All review comments with thread IDs (code-specific feedback)
- All review threads (resolved and unresolved)
- Latest CI/CD run status and failure logs (if any)
- Summary statistics

The script handles:
- Rate limit checking before proceeding
- Pagination for large PRs (>100 threads)
- Graceful error handling for missing permissions

## Phase 2: Analyse

For each piece of feedback, categorise:

| Category | Action |
|----------|--------|
| **Code fix required** | Note the file, change needed, and which comments/CI failures it addresses |
| **No change needed** | Prepare explanation for reviewer |
| **Out of scope** | Prepare to create a new issue and link it |
| **CI-only failure** | Note the fix needed (may overlap with review comments) |
| **General question/discussion** | Prepare appropriate response |

Look for overlaps where one fix addresses multiple items.

Note the comment type (conversation vs review) as they use different reply mechanisms.

### Prioritising Feedback

Handle feedback in this order:
1. **Blocking issues**: Security concerns, correctness bugs, breaking changes
2. **Required changes**: Explicitly requested by reviewers with "Request changes"
3. **CI failures**: Tests, linting, type checking
4. **Suggestions**: Nice-to-haves, style preferences
5. **Questions**: Clarifications that don't block merge

### Handling Conflicting Opinions

When reviewers disagree:
1. Identify the core technical concern from each reviewer
2. If both are valid, choose the approach that:
   - Best fits existing codebase patterns
   - Is more maintainable long-term
   - Has better performance characteristics
3. Reply explaining your reasoning and invite further discussion
4. Tag both reviewers in your response

## Phase 3: Create Unified Plan

Before making changes, output a plan:

1. Code changes to make (grouped by file)
2. Which review comments each change addresses
3. Which CI failures each change fixes
4. Comments that need explanation-only replies
5. Out-of-scope items to convert to issues

Ask: "Ready to execute this plan?"

Wait for confirmation.

## Phase 4: Execute

### 1. Apply code fixes

Make all code changes, then commit:

```bash
git add -A
git commit -m "Address PR feedback

- [summary of changes]
- Fixes review comments from @reviewer
- Resolves CI failure in [workflow]"
git push
```

### 2. Reply to comments

**For code review comments** (attached to specific lines):

```bash
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/replies \
  -f body="Fixed: [description of change]"
```

**For PR conversation comments** (general discussion):

```bash
gh pr comment {PR_NUMBER} -b "Replying to @{author}: [response]"
```

Reply templates:
- Fix applied: `Fixed: [what was changed]`
- No change needed: `No change required: [explanation]`
- Out of scope: `Good suggestion, tracked as #[issue_number]`
- Acknowledgement: `Thanks for the feedback, [response]`

### Declining suggestions diplomatically

When you disagree with a suggestion:

```
Thanks for the suggestion. I considered this approach but chose [current approach] because:

1. [Technical reason]
2. [Practical reason]

Happy to discuss further if you see issues with this reasoning.
```

### 3. Create issues for out-of-scope items

```bash
gh issue create \
  -t "Enhancement: [title]" \
  -b "Suggested during PR review of #[PR_NUMBER].

## Context
[Original comment]

## Suggested approach
[Implementation ideas]"
```

### 4. Resolve review threads

Use the helper script:

```bash
scripts/resolve-thread.sh <THREAD_ID>
```

Or manually via GraphQL:

```bash
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {threadId: "<THREAD_ID>"}) {
      thread { id isResolved }
    }
  }'
```

**Note:** Only resolve threads where the feedback has been addressed. Leave threads open if discussion is ongoing.

### 5. Verify CI passes

Wait for CI to complete after pushing:

```bash
gh run watch
```

If still failing, repeat analysis on new logs.

### 6. Request re-review (if needed)

If reviewers requested changes:

```bash
gh pr edit $PR_NUMBER --add-reviewer @reviewer1,@reviewer2
```

## Phase 5: Summarise

Post a summary comment using [templates/summary.md](templates/summary.md):

```bash
gh pr comment -b "## PR Feedback Summary

### Review Comments
- X comments addressed with code changes
- Y comments resolved with explanations  
- Z suggestions tracked as new issues

### CI/CD
- [Status of workflow runs]

### Changes Made
- [List of commits/changes]

All feedback has been addressed."
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/load-pr-feedback.sh` | Fetches PR comments, threads, and CI status |
| `scripts/resolve-thread.sh` | Resolves a review thread by ID |

## Subagent Usage

Use subagents to parallelize data gathering and offload reply posting.

### Phase 1: Parallel Data Gathering

For PRs with significant feedback, launch 3 agents in parallel to gather all data sources simultaneously:

```
Launch parallel agents:

1. Review Comments Agent (general-purpose):
   "Fetch all code review comments for PR #{number} in {owner}/{repo}.
   Use GraphQL to get review threads with pagination.
   For each comment, capture:
   - Thread ID (for resolution)
   - Comment ID (for replies)
   - File path and line number
   - Author
   - Body text
   - Resolution status
   Return: Structured list of all review threads and comments"

2. CI Failures Agent (general-purpose):
   "Fetch CI/CD status for PR #{number} in {owner}/{repo}.
   Steps:
   1. Run: gh pr checks {number}
   2. For failed checks, get run IDs: gh run list --branch {branch}
   3. For each failed run, get logs: gh run view {run_id} --log-failed
   4. Extract error messages and affected files
   Return: List of failures with error messages, affected files, and suggested fixes"

3. Conversation Agent (general-purpose):
   "Fetch PR conversation comments for PR #{number} in {owner}/{repo}.
   Use: gh api repos/{owner}/{repo}/issues/{number}/comments
   Handle pagination for large discussions.
   For each comment, capture:
   - Comment ID
   - Author
   - Body text
   - Created date
   Return: Chronological list of conversation comments"
```

**Benefits:**
- Data gathering 3x faster (concurrent API calls)
- API rate limits spread across parallel requests
- Main context receives only structured summaries

### Phase 4: Background Reply Posting

After applying code fixes, offload reply posting to background:

```
Launch background agent:
"Post replies to PR #{number} review comments.
Replies to post:
[List of {comment_id, reply_text, comment_type}]

For each reply:
1. If code review comment:
   gh api repos/{owner}/{repo}/pulls/comments/{id}/replies -f body='...'
2. If conversation comment:
   gh pr comment {number} -b '...'
3. Log success/failure for each

Return: Summary of posted replies with any failures"
```

```
Launch background agent:
"Resolve addressed review threads for PR #{number}.
Threads to resolve:
[List of thread IDs]

For each thread:
1. Run scripts/resolve-thread.sh {thread_id}
2. Log success/failure

Return: Summary of resolved threads"
```

Main context can continue working (e.g., creating follow-up issues) while replies post.

**When to use subagents:**
- PR has > 10 review comments: Use parallel data gathering
- > 5 replies to post: Use background reply agent
- CI has multiple failed workflows: Use dedicated CI agent

**When to skip subagents:**
- Small PR with < 5 comments total
- Single CI failure to address
- Quick turnaround needed (subagent overhead not worth it)

### Handling Agent Results

After parallel agents complete, synthesize in main context:

```markdown
## Feedback Summary

### From Review Comments Agent:
- X unresolved threads across Y files
- Key themes: [categorize by type]

### From CI Agent:
- Z failed workflows
- Common failures: [test name, lint errors, etc.]

### From Conversation Agent:
- N general comments
- Unanswered questions: [list]

### Overlaps
- Comment about X and CI failure Y both fixed by: [change]
```

## Related Skills

- [fix-github-issue](../fix-github-issue/SKILL.md): The workflow that creates the PR
- [cleanup-issue](../cleanup-issue/SKILL.md): Clean up after PR is merged
