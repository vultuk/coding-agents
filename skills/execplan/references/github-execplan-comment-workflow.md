# GitHub ExecPlan Comment Workflow

Use this reference when the repository does not provide a stricter local ExecPlan format. It adapts the normal file-backed ExecPlan rules to a GitHub issue comment that is edited in place.

## Claim the Issue First

Before writing the first ExecPlan draft, react to the issue and assign it to the logged-in user.

Resolve the repository slug:

    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

Add the `👀` reaction to the main issue thread:

    gh api "repos/$REPO/issues/$ISSUE/reactions" \
      -X POST \
      -H "Accept: application/vnd.github+json" \
      -f content='eyes' \
      >/dev/null

Assign the issue to the logged-in user:

    gh issue edit "$ISSUE" --add-assignee "@me"

Both commands are safe to re-run. GitHub keeps a single reaction per user/content pair, and `--add-assignee "@me"` is harmless if the user is already assigned.

## Required Comment Shape

The entire managed comment body must be plain Markdown, not a fenced code block:

    <!-- execplan:managed -->
    # <Short, action-oriented description>

    This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

    If the repository contains `.agent/PLANS.md`, name that file here and state that this comment must be maintained in accordance with it.

    ## Purpose / Big Picture

    Explain what a user can do after the change and how to see it working.

    ## Progress

    - [x] (2026-03-12 10:00Z) Example completed step.
    - [ ] Example incomplete step.
    - [ ] Example partially completed step (completed: X; remaining: Y).

    ## Surprises & Discoveries

    - Observation: ...
      Evidence: ...

    ## Decision Log

    - Decision: ...
      Rationale: ...
      Date/Author: ...

    ## Outcomes & Retrospective

    Summarize outcomes, gaps, and lessons learned.

    ## Context and Orientation

    Describe the relevant repository areas as if the reader knows nothing.

    ## Plan of Work

    Describe the sequence of edits in prose.

    ## Concrete Steps

    State the exact commands to run, where to run them, and short expected outputs.

    ## Validation and Acceptance

    Describe how to prove the change works.

    ## Idempotence and Recovery

    Explain how to retry safely and how to roll back risky steps.

    ## Artifacts and Notes

    Include concise transcripts, diffs, or snippets that prove progress.

    ## Interfaces and Dependencies

    Name the modules, services, functions, commands, or APIs that must exist or be used.

    Revision note: 2026-03-12 by Codex. Created the initial issue-backed ExecPlan and chose GitHub comment storage so the issue remains the source of truth.

Keep the plan prose-first. Use checklists only in `Progress`, where they are mandatory.

## Read Issue and Repository Context

Fetch issue metadata first:

    ISSUE=103
    gh issue view "$ISSUE" --json number,title,body,state,url,labels

Then inspect the repository instructions and affected code before drafting the plan.

## Find the Managed Comment

Resolve the repository slug:

    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

Find the newest managed ExecPlan comment on the issue:

    COMMENT_ID=$(gh api "repos/$REPO/issues/$ISSUE/comments" --paginate \
      --jq 'map(select(.body | contains("<!-- execplan:managed -->"))) | sort_by(.updated_at) | last | .id // empty')

If `COMMENT_ID` is empty, no managed ExecPlan comment exists yet.

## Create the Managed Comment

Prepare the comment body in a temporary file. Do not store the plan as a repository file.

    PLAN_FILE=$(mktemp)
    cat > "$PLAN_FILE" <<'EOF'
    <!-- execplan:managed -->
    # Implement issue #103
    ...
    EOF

Create the comment and capture its identifier:

    COMMENT_ID=$(gh api "repos/$REPO/issues/$ISSUE/comments" \
      -F "body=@$PLAN_FILE" \
      --jq '.id')

Delete the temp file after the request succeeds or fails.

After the managed comment exists, remove the temporary `👀` reaction and add the `in progress` label:

    VIEWER=$(gh api graphql -f query='query { viewer { login } }' --jq '.data.viewer.login')
    EYES_REACTION_ID=$(gh api "repos/$REPO/issues/$ISSUE/reactions" \
      -H "Accept: application/vnd.github+json" \
      --jq "map(select(.content == \"eyes\" and .user.login == \"$VIEWER\")) | first | .id // empty")

    if [ -n "$EYES_REACTION_ID" ]; then
      gh api "repos/$REPO/issues/reactions/$EYES_REACTION_ID" \
        -X DELETE \
        -H "Accept: application/vnd.github+json" \
        >/dev/null
    fi

    LABEL_EXISTS=$(gh api "repos/$REPO/labels/in%20progress" --silent >/dev/null 2>&1; echo $?)
    if [ "$LABEL_EXISTS" -ne 0 ]; then
      gh label create "in progress" --color "0E8A16" --description "Work has started" >/dev/null
    fi
    gh issue edit "$ISSUE" --add-label "in progress"

## Edit the Managed Comment

Before editing, fetch the current remote copy again if any time has passed or code work has completed. This avoids clobbering newer edits.

Update the temporary file with the latest complete plan body, then patch the comment:

    gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
      -X PATCH \
      -F "body=@$PLAN_FILE" \
      >/dev/null

If this is the first successful creation of the managed comment and the `👀` reaction is still present, run the cleanup-and-label step above after the patch succeeds.

## Execution Rules

During implementation, the GitHub comment replaces the local `.md` plan file. Keep it updated with the same discipline as a file-backed ExecPlan:

- Split work into granular `Progress` items before implementation starts.
- Update the GitHub comment immediately after each individual `Progress` item is completed.
- Do not wait until the end of a milestone or the end of the task to publish accumulated progress.
- Record unexpected findings in `Surprises & Discoveries`.
- Record design changes in `Decision Log`.
- Record milestone outcomes in `Outcomes & Retrospective`.
- Add a new revision note at the bottom every time the plan materially changes.

Do not create extra comments for routine progress. The managed comment is the authoritative log.

Use this execution loop:

1. Read the latest managed comment.
2. Pick one unchecked `Progress` item.
3. Complete only that unit of work.
4. Run the validation that proves that unit is complete.
5. Patch the managed comment immediately to mark that checkbox complete and update any related sections.
6. Repeat with the next unchecked item.

## Finalize the Delivery

When all unchecked `Progress` items are complete and validation passes, do not stop at a local diff. Finish the GitHub delivery loop.

Create a branch using the repository naming convention:

    ISSUE_SLUG=implement-issue-103
    BRANCH="fix/$ISSUE-$ISSUE_SLUG"
    git checkout -b "$BRANCH"

Commit the work with an issue-linked message:

    git status --short
    git add <changed-files>
    git commit -m "Implement issue #103 workflow" -m "Complete the planned changes and validation for #103."

Push the branch:

    git push -u origin "$BRANCH"

Prepare a pull request body in a temporary file. Link the issue explicitly in the body:

    PR_BODY=$(mktemp)
    cat > "$PR_BODY" <<'EOF'
    Closes #103

    ## Why

    Explain the original problem or request that led to this work.

    ## What changed

    Describe the implementation in concrete terms.

    ## Impact

    Explain user-facing, developer-facing, or operational impact.

    ## Testing

    List the commands that ran and what passed.

    ## Out of scope / follow-ups

    Note intentionally excluded work, limitations, or next steps.
    EOF

Create the PR:

    PR_URL=$(gh pr create \
      --base main \
      --head "$BRANCH" \
      --title "Implement #103: concise outcome-focused title" \
      --body-file "$PR_BODY")

Update the managed issue comment again after PR creation so the issue itself records the final traceability details:

    COMMIT_SHA=$(git rev-parse HEAD)
    # Refresh PLAN_FILE with the latest Markdown plan content, including:
    # - completed Progress entries
    # - validation results
    # - branch name
    # - commit hash
    # - PR URL
    gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
      -X PATCH \
      -F "body=@$PLAN_FILE" \
      >/dev/null

Delete temporary files after the push and PR creation succeed or fail.

If the repository uses a non-`main` default branch or already has a stricter PR template, adapt the command and body to match local conventions while preserving explicit issue linkage.

## Failure and Recovery

If GitHub API writes fail:

1. Keep the current plan text in a temporary file.
2. Retry the `gh api` request after re-fetching `COMMENT_ID` and issue state.
3. If retries keep failing, tell the user the issue comment could not be updated and include the exact failure point.
4. Do not silently fall back to a local permanent plan file unless the user explicitly approves that change in storage model.
