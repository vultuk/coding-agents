---
name: pr-feedback-workflow
description: Continuously monitor an open GitHub pull request, process new review feedback and CI failures in a resumable loop, apply fixes or evidence-based replies, create follow-up issues when work is out of scope, resolve review threads, and keep re-entering watch mode until stopped.
---

# PR Feedback Workflow

Use this skill when the user wants an open pull request monitored continuously rather than handled in one pass. The workflow is stateful and resumable: idle polls must not terminate the run, and restarts must continue from the saved state instead of reprocessing the same feedback.

## Inputs

- `PR` optional. Accept a PR number or PR URL. Default: the PR for the current branch.
- `MODE=watch|once` optional. Default: `watch`.
- `POLL_SECONDS` optional. Default: `300`. Minimum: `300`.
- `STATE_FILE` optional. Default: `.git/codex/pr-feedback-workflow/pr-<number>.json` in the current repository.

## Required Helper

Use the helper as the canonical snapshot and state engine:

```bash
python3 skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode <watch|once> --poll-seconds 300 --state-file <path> [--pr <number|url>]
```

In `watch` mode the helper must keep polling while the PR is idle and return only when one of these happens:

- new or updated actionable work is present
- a blocker is present
- the PR is merged or closed

In `once` mode the helper returns one snapshot immediately.

The helper emits JSON with:

- `pr`
- `iteration`
- `status` as `actionable|idle|blocked|closed`
- `new_items`
- `updated_items`
- `failed_checks`
- `blocked_reasons`
- `state_file`

The helper also supports state updates before the next snapshot:

```bash
python3 skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file <path> \
  --mark-handled <item-key> \
  --set-last-action "<summary>"
```

Optional update flags:

- `--mark-handled <item-key>` repeatable
- `--record-blocked <item-key>=<reason>` repeatable
- `--increment-retry <item-key>` repeatable
- `--clear-retry <item-key>` repeatable
- `--set-last-action "<summary>"`

## State Contract

Persist workflow state atomically after each helper invocation. The state file is the source of truth for dedupe, resume, and retry tracking.

Stable state fields:

- `repo`
- `pr_number`
- `pr_state`
- `loop_iteration`
- `last_poll_at`
- `handled_review_ids`
- `handled_comment_ids`
- `handled_thread_ids`
- `handled_body_hashes`
- `handled_ci_failures`
- `pending_items`
- `blocked_items`
- `retry_counters`
- `last_action_summary`

Operational rules:

- `handled_body_hashes` is keyed by item key and stores the last handled body hash. If the same item key appears again with a different body hash, treat it as updated work.
- `handled_ci_failures` is keyed by `failure-class + head SHA`. The same CI failure on the same SHA is deduped after handling; the same failure on a new SHA is new work.
- `retry_counters` must survive restarts so transient retry budgets do not reset.
- `blocked_items` are resumable blockers, not terminal loss of state.

## Workflow

### 1. Resolve PR Context

Use the helper or `gh pr view` to resolve the PR. If no PR exists for the current branch and none was provided explicitly, stop and report that clearly.

### 2. Enter Watch Mode

Default to:

```bash
python3 skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode watch --poll-seconds 300 --state-file "$STATE_FILE" [--pr "$PR"]
```

Do not implement your own sleep loop in the agent. Let the helper absorb idle polls and return only when work, a blocker, or closure exists.

### 3. Process Every Surfaced Item

For each item in `new_items` and `updated_items`, choose exactly one path:

1. Fix it: implement code changes, test, commit, push, reply.
2. No code change needed: reply with evidence-based explanation.
3. Out of scope: draft a follow-up with `$issue-writer`, create it with `gh issue create`, then reply with the issue link.

Treat human and bot reviews equally. For every actionable thread, always post a direct thread reply.

### 4. Persist Action Outcomes Immediately

After each reply, fix, thread resolution, blocker, or retry update, write it back to the state file before re-entering watch mode.

Examples:

```bash
python3 skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --mark-handled "thread:123" \
  --set-last-action "Replied on thread:123 and resolved it"
```

```bash
python3 skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --record-blocked "issue-comment:456=gh issue create failed after retry budget"
```

```bash
python3 skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --increment-retry "ci:test-suite:<head-sha>" \
  --set-last-action "Retrying flaky test-suite job after timeout"
```

### 5. Resume Watch Mode

After the current surfaced work is handled or recorded as blocked, go back to watch mode using the same state file. Do not stop just because one pass is green.

### 6. Exit Conditions

Stop only when:

- the user explicitly says stop
- the PR is merged
- the PR is closed
- an unrecoverable blocker is recorded and surfaced as `status=blocked`

Even in a blocked state, leave the saved state file intact so the run can resume later.

## Review and Reply Rules

- Reply on every actionable review thread.
- If a review has a meaningful top-level body, add one PR-level comment summarising what changed.
- Use concise, evidence-based replies with concrete file paths or codebase references.
- Use UK spelling in user-facing text.

Never resolve a thread until:

1. the reply mutation succeeded, and
2. the next helper snapshot or direct GitHub check confirms the action is reflected

If confirmation fails, do not mark the item handled yet.

## CI Self-Healing

If a surfaced item is a CI failure:

1. Inspect the failing logs.
2. Classify transient vs persistent.
3. For transient failures, retry with backoff and update `retry_counters`.
4. For persistent failures, implement the fix, validate, commit, push, and reply if needed.
5. Clear retry state when the failure class is resolved for the current SHA.

Retry budget:

- transient retries: up to `5`
- persistent fix cycles: up to `3` per distinct failure class and head SHA

## Out-of-Scope Follow-Ups

This skill no longer depends on `generate-issue`.

When feedback is valid but out of scope:

1. Use `$issue-writer` to draft a short implementation issue body.
2. Create the issue with `gh issue create`.
3. Reply on the PR thread with the issue link.
4. Mark the surfaced item handled only after the reply is posted successfully.

If issue creation fails after retries, record a blocker with `--record-blocked` and leave the thread unresolved.

## Status Cadence

While the workflow is active, post concise status updates in this format:

```text
PR=<url>
LOOP_ITERATION=<n>
NEW_ITEMS=<count>
ACTION_TAKEN=fix|explain|follow-up-issue|retry|blocked|none
CI=pass|fail|pending
STATE_FILE=<path>
```

## Validation

Before trusting the helper behaviour, use:

```bash
python3 -m unittest discover -s skills/pr-feedback-workflow/tests -v
```

Live manual validation on a disposable PR should confirm:

- idle watch mode keeps polling instead of exiting
- a new review appears on the next surfaced snapshot
- a failing check is deduped per failure class and head SHA
- blocked issue creation leaves a resumable blocker instead of silently giving up

## Final Response Contract

When monitoring ends, return a concise summary covering:

- why monitoring ended
- fixes applied
- explanations posted
- follow-up issues created
- final CI state
- unresolved-thread state
- path to the saved state file

## Related Skills

- [issue-writer](../issue-writer/SKILL.md)
