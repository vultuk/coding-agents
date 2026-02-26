---
name: pr-feedback-workflow
description: Continuously monitor an open GitHub pull request, process new review feedback and CI failures in a loop, apply fixes or evidence-based replies, create follow-up issues with generate-issue for out-of-scope requests, resolve review threads, and send a completion notification. Use when asked to address PR feedback continuously, handle review comments end-to-end, auto-fix CI failures, or run a PR feedback loop until stopped.
---

# PR Feedback Workflow

Monitor a pull request in a continuous loop, handle all new feedback and CI failures autonomously, and keep re-checking until stopped.

## Follow Core Behaviour

For each new feedback item, choose exactly one path:

1. Fix it: implement code changes, test, commit, push, reply.
2. No code change needed: reply with evidence-based explanation.
3. Out of scope: create a follow-up issue via `$generate-issue`, then reply with the issue link.

Then continue monitoring for newly arriving feedback and CI updates.

Treat all GitHub reviews equally, including human and bot reviews. For every actionable review item, post an explicit reply and resolve the thread after action is taken.

## Enforce Hard Requirements

1. For every newly submitted review from humans or bots, process all contained actionable items.
2. For every actionable review comment thread, always post a direct reply on that thread.
3. After taking action (fix, explain, or follow-up issue), mark that thread resolved.
4. If a review has a top-level body with requested action, post a PR-level response comment summarising what was done.
5. Do not stop after one pass; continue looped monitoring by default.
6. Use `$generate-issue` for out-of-scope follow-ups.
7. Keep scope to the current PR; do not inspect other issues or PRs unless explicitly requested.

## Run Continuous Loop

Default mode is watch-loop with a minimum polling interval of 300 seconds (5 minutes).
Use a practical range of 300-420 seconds to avoid tight polling patterns.
Do not poll more frequently unless the user explicitly asks for faster checks.

Stop only when:
- user explicitly says stop, or
- PR is merged or closed.

Even when everything is green, keep polling for new feedback.

## Run Workflow

### Phase 1: Identify PR context

Resolve PR number from explicit input or current branch:

```bash
gh pr view --json number,url,title,headRefName,baseRefName,state
```

If PR does not exist, stop and report clearly.

### Phase 2: Poll snapshot (each loop iteration)

Gather in parallel:

```bash
gh pr checks --json name,state,conclusion,link
gh api repos/{owner}/{repo}/pulls/{number}/comments
gh api repos/{owner}/{repo}/pulls/{number}/reviews
gh api repos/{owner}/{repo}/issues/{number}/comments
gh api graphql -f query='query($owner:String!,$repo:String!,$pr:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$pr){reviewThreads(first:100){nodes{id isResolved comments(first:20){nodes{id body author{login} createdAt url}}}}}}}' -f owner="$OWNER" -f repo="$REPO" -F pr=$PR_NUMBER
```

Track processed comment and thread IDs so each item is handled once unless updated.

Also track processed review IDs so newly submitted manual and bot reviews are always acknowledged and handled.

If comments suggest broader follow-up work, keep the PR focused and use `$generate-issue` for out-of-scope tracking.

### Phase 3: Classify each new actionable item

Classification matrix:

| Class | Action |
|------|--------|
| Directly required code change | Implement + test + commit + push + reply |
| Clarification or disagreement | Reply with codebase-backed reasoning |
| Out of scope for this PR | Create follow-up issue via `$generate-issue` + reply |
| CI failure without review comment | Diagnose and auto-fix |

### Phase 3.5: Apply review-by-review response contract

For each new review with actionable feedback:

1. Enumerate all inline review comments and classify each item.
2. Execute one of the three action paths for each item.
3. Reply on each review thread with the action outcome.
4. Resolve that thread immediately after action is completed.
5. If the review includes a top-level summary or request, add one PR-level comment summarising disposition.

Use these primitives:

```bash
# Reply to a review comment
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/replies -f body="<response>"

# Resolve review thread
gh api graphql -f query='mutation($threadId:ID!){resolveReviewThread(input:{threadId:$threadId}){thread{id isResolved}}}' -f threadId="$THREAD_ID"
```

### Phase 4: Execute actions

#### A) Fix path

1. Apply minimal code change.
2. Run relevant tests, lint, typecheck, and build.
3. Commit and push.
4. Reply to comment with what changed (include file paths).
5. Resolve the thread once fix is in place and reply is posted.

#### B) No-change path

Reply with concise technical justification and references:
- cite existing pattern files
- explain why requested change is not needed now
- keep tone collaborative

Resolve thread only if reply fully addresses concern.

In this workflow, once explanation is posted as the chosen action and no further change is pending, resolve the thread.

#### C) Out-of-scope path (must use `$generate-issue`)

Before creating a follow-up issue, keep momentum and focus on the actionable request.

Invoke `$generate-issue` with full context:

```text
Prompt payload:
- Source PR: #<number> <url>
- Reviewer comment URL and text
- Why this is out of scope for current PR
- Suggested follow-up direction
Expected output: created issue URL and number
```

Then reply on the PR comment:

```text
Great suggestion. This is out of scope for this PR, so I opened <issue-url> to track it and keep this PR focused.
```

Resolve the thread after posting the follow-up issue link.

### Phase 5: CI self-healing

If any check fails:

1. Fetch failed logs.
2. Classify transient vs persistent.
3. For transient errors (timeout, 429, network): retry with backoff.
4. For persistent errors: implement fix, commit, push.
5. Re-check CI and continue loop.

Retry budget:
- transient: up to 5 retries
- persistent fix cycles: up to 3 per distinct failure class

### Phase 6: Loop decision

After processing current items:

1. Sleep for at least 300 seconds before the next poll (recommended 300-420 seconds with jitter).
2. Poll a fresh snapshot.
3. If new actionable items exist, process them and continue the loop.
4. If no actionable items exist (including when CI is still pending), keep looping and sleep for the next interval.

Do not exit just because all checks are green once.

## Follow Reply Quality Rules

- Be specific and evidence-based.
- Mention concrete files and functions when claiming precedent.
- Keep explanations short, direct, and respectful.
- Use UK spelling in user-facing text.
- Use `rg` instead of `grep` for shell-based text search and filtering.

## Escalate Only as Last Resort

Escalate only if all retries are exhausted:

| Condition | Escalate After |
|-----------|----------------|
| Same CI class keeps failing | 3 fix attempts |
| Reviewer conflict with no codebase precedent | present both options once |
| Security-sensitive disagreement | immediate human review |

Escalation message format:

```markdown
## Escalation Required

PR: #$PR_NUMBER
Reason: [blocker]

Attempts made:
1. ...
2. ...
3. ...

Recommended decision:
[specific choice]
```

## Maintain Output Cadence

Post concise periodic status updates while looping:

```text
PR=<url>
LOOP_ITERATION=<n>
NEW_ITEMS=<count>
ACTION_TAKEN=fix|explain|follow-up-issue|none
CI=pass|fail|pending
```

When the user stops monitoring, provide a final summary of:
- fixes applied
- explanations posted
- follow-up issues created
- current CI and unresolved-thread state

## Send Completion Notification as Final Step

When monitoring ends (user stops, or PR is merged or closed), after posting the final summary the very last action must be a Telegram notification.

Use `parse_mode: "Markdown"` and include:
- completion status and reason monitoring ended
- PR number and URL
- counts of fixes, explanations, and follow-up issues
- final CI and unresolved-thread status

Template:

```text
[PR Feedback Loop Complete]

*PR:* #$PR_NUMBER
*URL:* $PR_URL
*Ended because:* <user stopped|merged|closed>

*What was done:*
- Fixes applied: <count>
- Explanations posted: <count>
- Follow-up issues created: <count>
- Final CI: <pass|fail|pending>
- Unresolved threads: <count>
```

## Related Skills

- [generate-issue](../generate-issue/SKILL.md)
