---
name: pr-feedback-workflow
description: Continuously monitor an open GitHub pull request, process new review feedback and CI failures in a resumable loop, apply fixes or evidence-based replies, create follow-up issues when work is out of scope, resolve review threads, and when explicitly requested merge the clean PR and clean up local worktrees.
---

# PR Feedback Workflow

Use this skill when the user wants an open pull request monitored continuously rather than handled in one pass. The workflow is stateful and resumable: idle polls must not terminate the run, and restarts must continue from the saved state instead of reprocessing the same feedback.

## Inputs

- `PR` optional. Accept a PR number or PR URL. Default: the PR for the current branch.
- `MODE=watch|once` optional. Default: `watch`.
- `POLL_SECONDS` optional. Default: `300`. Minimum: `300`.
- `GOAL_DRIVEN=true|false` optional. Default: `true` when the Codex goal function is available.
- `STATE_FILE` optional. Default: `.codex/pr-feedback-workflow/pr-<number>.json` in the current repository.
  - Use a repo-local path outside `.git/` because git worktrees expose `.git` as a file, which breaks helper state-directory creation.
- `MERGE_AFTER_CLEAN=true|false` optional. Default: `false`; set true only when the user explicitly asks to merge after feedback is clean.
- `CLEANUP_WORKTREE=<path>` optional. Only use when the user explicitly asks to delete the task worktree after merge.

## Codex Goal Contract

When the Codex goal function is available, set a concrete goal before entering the loop. Use `create_goal` in tool surfaces that expose `create_goal`, or the equivalent `set_goal` function in older/newer Codex surfaces.

Goal objective template:

```text
Completely deal with PR <url-or-number>: all actionable review feedback has been fixed, explained, or moved to linked follow-up issues; all review threads that should be resolved are resolved; CI/CD has no failures and no checks still pending or running; the final PR state has been verified directly from GitHub.
```

Do not mark the goal complete until all of these are true on a fresh snapshot:

- helper status is `complete`, or a one-shot helper snapshot plus direct GitHub checks prove the equivalent state
- `new_items`, `updated_items`, `pending_items`, `failed_checks`, `pending_checks`, and `blocked_reasons` are all empty
- `gh pr view <pr> --json statusCheckRollup` shows every current head check is terminal and successful/skipped/neutral
- any actionable review threads have a posted reply or linked follow-up and are resolved when resolution is appropriate
- `git status --short` has no uncommitted intended fix/test changes
- if the user requested merge/cleanup, the PR has been merged, the remote PR branch deletion has been verified, and the requested worktree cleanup has been verified

When those conditions are met, call the Codex goal completion function (`update_goal(status="complete")` where available) and then return the final response. If the PR is merged or closed before the clean state is reached, report that separately instead of marking the goal complete unless the user explicitly defined closure as success.

## Required Helper

Use the helper as the canonical snapshot and state engine:

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode <watch|once> --poll-seconds 300 --state-file <path> [--complete-when-clean] [--pr <number|url>]
```

In `watch` mode the helper must keep polling while the PR is idle and return only when one of these happens:

- new or updated actionable work is present
- a blocker is present
- `--complete-when-clean` is set and the PR has no actionable work, no blockers, no failed checks, and no pending/running checks
- the PR is merged or closed

In `once` mode the helper returns one snapshot immediately.

The helper emits JSON with:

- `pr`
- `iteration`
- `status` as `actionable|idle|blocked|closed`
- `new_items`
- `updated_items`
- `failed_checks`
- `pending_checks`
- `blocked_reasons`
- `state_file`

When `--complete-when-clean` is used, `status` may also be `complete`.

The helper also supports state updates before the next snapshot:

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
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

### Worktree path caveat

In git worktrees, `.git` is often a file that points at the shared git dir, not a directory. That means the documented default path `.git/codex/pr-feedback-workflow/pr-<number>.json` can fail with `NotADirectoryError` when used literally from a worktree checkout.

When running this workflow inside a worktree, choose an explicit writable state-file path outside `.git/...`, for example:

- `/tmp/pr-<number>-feedback-state.json` for short-lived runs
- another repo-adjacent writable path that is not nested under the `.git` file

Before starting the helper, verify the chosen parent path is a real directory.

### Repo-local `.codex/` caveat

Some repos already track files under `.codex/` (for example checked-in environment config). In those repos, using a repo-local state path like `.codex/pr-feedback-workflow/...` can create noisy untracked files and make cleanup risky because removing the directory may also touch tracked `.codex` contents.

If `git status --short .codex` shows tracked or modified files, prefer a non-repo state path such as:

- `/tmp/pr-feedback-workflow/pr-<number>.json`
- another user-writable temp/cache directory outside the checkout

Treat the state file as workflow metadata, not product code: do not commit it.

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

### GitHub auth environment note

The helper shells out to `gh`, so it inherits whatever auth environment the current shell has.
In work-dev, `gh` auth commonly lives outside the profile-isolated `HOME`, so export:

```bash
export GH_CONFIG_DIR=/home/ec2-user/.config/gh
```

before running the helper or any `gh pr` / `gh api` commands. Otherwise the helper can report a blocked "please run gh auth login" state even when GitHub CLI auth already exists.

### 1. Resolve PR Context

Use the helper or `gh pr view` to resolve the PR. If no PR exists for the current branch and none was provided explicitly, stop and report that clearly.

### 2. Enter Goal-Driven Watch Mode

When goal-driven mode is active, default to:

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode watch --poll-seconds 300 --state-file "$STATE_FILE" --complete-when-clean [--pr "$PR"]
```

Do not implement your own sleep loop in the agent. Let the helper absorb idle polls and return only when work, completion, a blocker, or closure exists.

If the helper returns `status=complete`, perform the final direct GitHub verification listed in the Codex Goal Contract, then complete the Codex goal and stop. If the verification finds pending/running checks or unresolved actionable feedback, re-enter watch mode with the same state file.

If the Codex goal function is unavailable and the user explicitly wants ongoing monitoring, use normal watch mode without `--complete-when-clean` and keep the older open-ended behaviour.

### 3. Process Every Surfaced Item

For each item in `new_items` and `updated_items`, choose exactly one path:

1. Fix it: implement code changes, test, commit, push, reply.
2. No code change needed: reply with evidence-based explanation.
3. Out of scope: draft a follow-up with `$issue-writer`, create it with `gh issue create`, then reply with the issue link.

Before changing code, verify whether the newly surfaced feedback is already satisfied on the current PR head.
Sometimes review bots comment on an older head SHA or the user re-runs this workflow after the fix has already been pushed.
In that case:

- inspect the current branch / HEAD commit and relevant files/tests first
- if the work is already present, do **not** manufacture a no-op follow-up commit
- reply on the thread with concrete evidence from the current head, including commit hash, file paths, and validation commands where relevant
- resolve the thread and update workflow state normally

Treat this as the preferred path whenever the codebase already matches the requested change.

Treat human and bot reviews equally. For every actionable thread, always post a direct thread reply.

If the helper surfaces PR-level bot review summaries or other informational review items that do not require a reply, explicitly mark them handled after confirming all actionable child threads are resolved. Otherwise the workflow can remain artificially `actionable` with only summary reviews left in `pending_items`.

Use the item key exactly as surfaced by the helper, which is often a `review:<id>` key for these summaries, for example:

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --mark-handled "review:4133890831" \
  --set-last-action "Marked informational bot review summary as handled after resolving its child threads"
```

### 4. Persist Action Outcomes Immediately

After each reply, fix, thread resolution, blocker, or retry update, write it back to the state file before re-entering watch mode.

### 4.5. Verify Working Tree Cleanliness Before Pushing

After implementing a feedback round, but before posting final PR replies, run `git status --short` and make sure every intended code, test, and migration change is either committed or intentionally excluded.

This matters because PR-feedback loops often touch supporting files outside the primary implementation path, for example:

- route/unit/e2e mocks that must be updated after service/repository changes
- generated DB migrations and snapshot metadata
- test fixtures added during regression coverage work

Do not assume the files you staged for the main fix are the only ones that changed. If `git status --short` still shows relevant modified files after a commit, commit and push them before replying that the feedback is addressed.

Examples:

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --mark-handled "thread:123" \
  --set-last-action "Replied on thread:123 and resolved it"
```

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --record-blocked "issue-comment:456=gh issue create failed after retry budget"
```

```bash
python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py \
  --mode once \
  --state-file "$STATE_FILE" \
  --increment-retry "ci:test-suite:<head-sha>" \
  --set-last-action "Retrying flaky test-suite job after timeout"
```

### 5. Resume Watch Mode

After the current surfaced work is handled or recorded as blocked, go back to watch mode using the same state file. Do not stop just because one pass is green unless the helper returns `status=complete` and the direct GitHub final verification also passes.

### 6. Merge and Cleanup When Explicitly Requested

Only merge when the user explicitly asked for it, or when the user explicitly confirms a merge after the workflow reports clean state.

Before merging, all of these must be true on fresh direct checks:

- the helper returned `status=complete`, with empty `new_items`, `updated_items`, `pending_items`, `failed_checks`, `pending_checks`, and `blocked_reasons`
- `gh pr view <pr> --json statusCheckRollup,mergeStateStatus,headRefOid,state` shows the current PR head, all checks terminal success/skipped/neutral, and `mergeStateStatus` is mergeable such as `CLEAN`
- a direct review-thread query shows no unresolved review threads
- every actioned review thread has a direct reply that names what changed or why no code change was needed
- actioned review threads are resolved, including outdated threads, after the reply has posted successfully
- `git status --short` is clean in the task checkout

Use this unresolved-thread check before merge:

```bash
gh api graphql \
  -f query='query($owner:String!, $repo:String!, $number:Int!) { repository(owner:$owner, name:$repo) { pullRequest(number:$number) { reviewThreads(first:100) { nodes { id isResolved } } } } }' \
  -F owner="$OWNER" -F repo="$REPO" -F number="$PR_NUMBER" \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

Resolve actioned threads explicitly with GraphQL after replying:

```bash
gh api graphql \
  -f query='mutation($threadId:ID!) { resolveReviewThread(input:{threadId:$threadId}) { thread { id isResolved } } }' \
  -F threadId="$THREAD_ID"
```

Do not treat `reviewDecision=REVIEW_REQUIRED` by itself as an actionable item when direct thread checks show no unresolved review threads and `mergeStateStatus` is mergeable. Some repos still report review-required after bot comment reviews or member replies; rely on branch protection/mergeability plus unresolved-thread checks.

Merge method:

- use the method the user requested if specified
- otherwise inspect recent main history with `git log --oneline --first-parent origin/main -8`
- if recent history is squash-style PR commits, prefer `gh pr merge <pr> --squash --delete-branch`
- if repository policy is unclear or branch protection blocks merge, stop and report the exact blocker instead of forcing a merge

After merge, verify:

```bash
gh pr view "$PR" --json state,mergedAt,mergeCommit,headRefName,url
git ls-remote --heads origin "$HEAD_BRANCH"
```

If the user asked to delete the task worktree after merge:

1. confirm the task worktree is clean with `git status --short`
2. remove it from the canonical source repo, not from inside the removed directory:

   ```bash
   git -C "$SOURCE_REPO" worktree remove "$WORKTREE_PATH"
   git -C "$SOURCE_REPO" worktree prune
   ```

3. verify `test ! -d "$WORKTREE_PATH"`, `git -C "$SOURCE_REPO" worktree list`, and `git ls-remote --heads origin "$HEAD_BRANCH"` is empty
4. never remove unrelated worktrees or the canonical source repo

### 7. Exit Conditions

Stop only when:

- the user explicitly says stop
- the Codex goal is complete: no actionable review feedback remains, no blockers remain, and CI/CD is fully terminal green or neutral with nothing pending/running
- the PR is merged
- the PR is closed
- an unrecoverable blocker is recorded and surfaced as `status=blocked`

Even in a blocked state, leave the saved state file intact so the run can resume later.

## Review and Reply Rules

- Reply on every actionable review thread.
- If a review has a meaningful top-level body, add one PR-level comment summarising what changed.
- Use concise, evidence-based replies with concrete file paths or codebase references.
- Use UK spelling in user-facing text.

### Requirement-source arbitration

Do not assume every automated review suggestion should be implemented verbatim.
Before changing code for a review comment, check the governing requirement source when one exists, for example:

- the linked issue or PRD
- the PR description
- acceptance criteria or QA notes already attached to the work

If a review suggestion conflicts with the explicit product requirement, do **not** blindly implement it just to silence the bot. Instead:

1. confirm the requirement text with citations
2. keep or restore the implementation that matches the requirement
3. reply on the thread with an evidence-based explanation that cites the requirement source and relevant file paths/tests
4. add or update regression coverage so the intended behaviour is explicit

If a reviewer claims a bug, race, or semantic mismatch and investigation shows the current implementation is already correct, prefer a **regression-only** response over speculative production edits:

1. write a focused test that exercises the claimed scenario as directly as possible
2. run it to determine whether the current code actually fails or already behaves correctly
3. if the code is already correct, keep production code unchanged, commit the regression test, and reply with evidence from that test
4. if the test proves the reviewer is right, then implement the minimal fix and keep the new regression coverage

This is especially important for concurrency ordering, async lifecycle concerns, threshold/tolerance debates, signed-vs-absolute values, and other cases where a reviewer may be optimising for implementation intuition rather than the stated product contract.

TanStack Query refresh nuance for Portal/UI fixes:

- In React Query / TanStack Query, `query.refetch()` does not necessarily throw when the refresh fails; it commonly resolves with a result object where `isError` is true.
- If a success banner, resolved state, or button re-enable depends on a successful refresh, do not treat `await query.refetch()` alone as proof of success.
- Prefer one of these patterns:
  - inspect the returned result and gate success on `!result.isError`, or
  - use `throwOnError` explicitly if that is the chosen convention in the codebase.
- Add regression coverage for both cases when relevant:
  - refresh returns an error result without throwing
  - refresh throws/rejects outright

Practical GitHub API note for review-comment replies:

- For pull-request review comments surfaced as thread comment IDs, `gh api repos/<owner>/<repo>/pulls/comments/<comment_id>/replies` can 404 unexpectedly.
- Prefer the PR-scoped route: `gh api repos/<owner>/<repo>/pulls/<pr_number>/comments/<comment_id>/replies -X POST -f body='...'`.
- GraphQL `addPullRequestReviewThreadReply` can also work when you already have the thread node ID, but the PR-scoped REST path is the simplest reliable default.

Practical state-handling note for resolved threads:

- Once a review thread is resolved, the helper may stop surfacing that `thread:<id>` item on the next snapshot.
- That means a later `--mark-handled thread:<id>` can fail with `Cannot mark unknown item as handled` even though the thread was successfully replied to and resolved.
- Preferred sequence: reply, confirm the reply succeeded, resolve the thread, then use the next helper snapshot to verify the thread is gone. Only call `--mark-handled` for items that still exist in the helper state; for resolved threads that disappeared, rely on resolution plus the fresh snapshot and update `--set-last-action` instead.
- Informational PR-level review summaries (`review:<id>`) often remain after child threads are resolved, so continue marking those explicitly when they no longer require action.

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
GOAL=active|complete|blocked
STATE_FILE=<path>
```

## Validation

Before trusting the helper behaviour, use:

```bash
python3 -m unittest discover -s .agents/skills/pr-feedback-workflow/tests -v
```

Live manual validation on a disposable PR should confirm:

- idle watch mode keeps polling instead of exiting
- goal-driven watch mode returns `status=complete` only when no actionable feedback and no pending/running CI remain
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
- merge state and merge commit, if merged
- remote branch deletion and worktree cleanup state, if requested
- path to the saved state file

Before reporting the final CI state after a push, verify the live check rollup directly, for example with `gh pr view <pr> --json statusCheckRollup`. The helper surfaces failed checks, but a fresh head SHA can still have validation in progress even when the workflow snapshot is otherwise idle. Report `pending` when checks are still running rather than claiming `pass` just because no failures have surfaced yet.

## Related Skills

- [issue-writer](../issue-writer/SKILL.md)
