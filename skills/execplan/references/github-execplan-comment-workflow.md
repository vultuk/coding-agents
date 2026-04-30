# GitHub ExecPlan Comment Workflow

Use this reference when the repository does not provide a stricter local ExecPlan format. It adapts the official Codex Exec Plans guidance from [developers.openai.com/cookbook/articles/codex_exec_plans](https://developers.openai.com/cookbook/articles/codex_exec_plans) to a GitHub issue comment that is edited in place and treated as the audit log.

The helper script for deterministic comment maintenance lives at [`../scripts/manage_execplan_comment.py`](../scripts/manage_execplan_comment.py).

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

The entire managed comment body must be plain Markdown, not a fenced code block. Keep the existing managed marker exactly as:

    <!-- execplan:managed -->

Add a hidden metadata block near the top of the comment. Keep the metadata inside a single HTML comment, but base64-encode the JSON payload first so GitHub never sees raw `-->` terminators from user-controlled strings:

    <!-- execplan:meta
    eyJicmFuY2giOiBudWxsLCAiY29tbWVudElkIjogOTg3NjU0MzIxLCAiY29tbWl0IjogbnVsbCwgImhhbmRvZmYiOiB7ImNvbW1lbnRJZCI6IG51bGwsICJzdGF0dXMiOiAicGVuZGluZyJ9LCAiaXNzdWUiOiAxMDMsICJpc3N1ZUF1dGhvciI6ICJvY3RvY2F0IiwgImxhc3RTeW5jZWRBdCI6ICIyMDI2LTAzLTI2VDE0OjA1OjAwWiIsICJtb2RlIjogInBsYW5uaW5nIiwgInBsYW5SZXZpc2lvbiI6IDEsICJwciI6IHsibnVtYmVyIjogbnVsbCwgInVybCI6IG51bGx9LCAicmVwbyI6ICJvd25lci9yZXBvIiwgInJldmlld0dhdGUiOiB7ImJsb2NrZXJzIjogW10sICJmaXhlc0FwcGxpZWQiOiBmYWxzZSwgInJldmlld2VkQXQiOiBudWxsLCAic3RhdHVzIjogInBlbmRpbmciLCAic3VtbWFyeSI6IG51bGx9LCAic3RhdHVzIjogImluX3Byb2dyZXNzIiwgInZhbGlkYXRpb24iOiB7ImNvbW1hbmRzIjogW10sICJzdGF0dXMiOiAicGVuZGluZyIsICJzdW1tYXJ5IjogbnVsbH19
    -->

The helper script handles encoding and decoding automatically; humans should treat the payload as opaque.

The managed comment must always contain these sections:

- `Progress`
- `Surprises & Discoveries`
- `Decision Log`
- `Outcomes & Retrospective`
- `Context and Orientation`
- `Plan of Work`
- `Concrete Steps`
- `Validation and Acceptance`
- `Idempotence and Recovery`
- `Artifacts and Notes`
- `Interfaces and Dependencies`
- `Audit Evidence`
- `Delivery Metadata`

Unlike the file-backed guide, the GitHub version stays plain Markdown so the managed marker, hidden metadata block, and required sections remain machine-editable. The visible prose should still follow the guide's quality bar:

- Start with the outcome and relevant repository context, not generic template narration.
- Prefer short paragraphs over bullet spam outside `Progress` and `Delivery Metadata`.
- Keep the initial plan to a small set of independently verifiable slices.
- Use repository-relative paths in visible prose and `<repo-root>` when a working directory matters.
- Never include local worktree paths such as `/Users/...` or `~/.codex/worktrees/...` in the GitHub comment body.
- Do not repeat the same information across `Context and Orientation`, `Plan of Work`, and `Concrete Steps`.

`Progress` is the authoritative completion log. Every item needs a stable slice ID:

    - [ ] EP-001 Implement config parser
    - [x] EP-001 (2026-03-26T14:05:00Z) Implement config parser

`Audit Evidence` must contain one matching entry for every completed slice:

    - slice: EP-001
      time: 2026-03-26T14:05:00Z
      kind: validation
      action: pytest tests/test_execplan.py -q
      cwd: <repo-root>
      result: Passed
      proof: 7 tests passed in 0.41s

Use UTC ISO 8601 timestamps everywhere in the audit trail.

## Read Issue and Repository Context

Fetch issue metadata first:

    ISSUE=103
    gh issue view "$ISSUE" --json number,title,body,state,url,labels,author
    ISSUE_AUTHOR=$(gh issue view "$ISSUE" --json author --jq '.author.login // empty')

Then inspect the repository instructions and affected code before drafting the plan.

## Find the Managed Comment

Resolve the repository slug:

    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

Find the newest managed ExecPlan comment on the issue:

    COMMENT_ID=$(gh api "repos/$REPO/issues/$ISSUE/comments" --paginate \
      --jq 'map(select(.body | contains("<!-- execplan:managed -->"))) | sort_by(.updated_at) | last | .id // empty')

If `COMMENT_ID` is empty, no managed ExecPlan comment exists yet.

## Create or Enrich the Managed Comment

Prepare metadata in a temporary file:

    META_FILE=$(mktemp)
    cat > "$META_FILE" <<EOF
    {
      "issue": $ISSUE,
      "repo": "$REPO",
      "mode": "planning",
      "status": "in_progress",
      "issueAuthor": "${ISSUE_AUTHOR:-}",
      "commentId": null,
      "planRevision": 1,
      "lastSyncedAt": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
      "branch": null,
      "commit": null,
      "pr": {
        "number": null,
        "url": null
      },
      "reviewGate": {
        "status": "pending",
        "reviewedAt": null,
        "summary": null,
        "fixesApplied": false,
        "blockers": []
      },
      "validation": {
        "status": "pending",
        "summary": null,
        "commands": []
      },
      "handoff": {
        "commentId": null,
        "status": "pending"
      }
    }
    EOF

Create a new local plan skeleton or enrich an existing one in place:

    PLAN_FILE=$(mktemp)
    if [ -n "$COMMENT_ID" ]; then
      gh api "repos/$REPO/issues/comments/$COMMENT_ID" --jq '.body' > "$PLAN_FILE"
    else
      printf '%s\n' '<!-- execplan:managed -->' '# Implement issue #103' > "$PLAN_FILE"
    fi

    python3 skills/execplan/scripts/manage_execplan_comment.py normalize \
      --input "$PLAN_FILE" \
      --output "$PLAN_FILE" \
      --title "Implement issue #$ISSUE" \
      --meta-file "$META_FILE"

If the comment already existed without a metadata block, `normalize` enriches it in place. It preserves prior prose and appends any missing required sections without rewriting the full history.

Before posting a new or refreshed plan body, lint the visible content:

    python3 skills/execplan/scripts/manage_execplan_comment.py lint \
      --input "$PLAN_FILE"

Create the comment and capture its identifier when needed:

    if [ -z "$COMMENT_ID" ]; then
      COMMENT_ID=$(gh api "repos/$REPO/issues/$ISSUE/comments" \
        -F "body=@$PLAN_FILE" \
        --jq '.id')
    fi

Patch the metadata block with the resolved `commentId` after creation:

    python3 skills/execplan/scripts/manage_execplan_comment.py normalize \
      --input "$PLAN_FILE" \
      --output "$PLAN_FILE" \
      --title "Implement issue #$ISSUE" \
      --meta-json "{\"commentId\": $COMMENT_ID, \"lastSyncedAt\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"

After the managed comment exists, remove the temporary `👀` reaction and add the `in progress` label:

    OWNER=$(echo "$REPO" | cut -d/ -f1)
    REPO_NAME=$(echo "$REPO" | cut -d/ -f2)
    ISSUE_NODE_ID=$(gh api graphql \
      -f query='query($owner:String!,$repo:String!,$number:Int!){repository(owner:$owner,name:$repo){issue(number:$number){id}}}' \
      -f owner="$OWNER" \
      -f repo="$REPO_NAME" \
      -F number="$ISSUE" \
      --jq '.data.repository.issue.id')

    # Prefer GraphQL removeReaction here. The REST delete-by-reaction-id path can 404 unexpectedly
    # even when the eyes reaction is visible, while GraphQL removal by issue node ID is idempotent.
    gh api graphql \
      -f query='mutation($subjectId:ID!){removeReaction(input:{subjectId:$subjectId,content:EYES}){subject{id}}}' \
      -f subjectId="$ISSUE_NODE_ID" \
      >/dev/null || true

    LABEL_EXISTS=$(gh api "repos/$REPO/labels/in%20progress" --silent >/dev/null 2>&1; echo $?)
    if [ "$LABEL_EXISTS" -ne 0 ]; then
      gh label create "in progress" --color "0E8A16" --description "Work has started" >/dev/null
    fi
    gh issue edit "$ISSUE" --add-label "in progress"

## Conflict-Safe Comment Updates

No long-lived local copy of the plan is authoritative. Before every edit:

1. Fetch the latest remote body and `updated_at`.
2. Rebuild the local temp file from that body.
3. Apply deterministic updates locally with the helper script.
4. Re-check `updated_at` before patching.
5. If it changed, rebuild against the fresh remote body and retry once.
6. If it changes again, stop and record a blocker rather than risking an overwrite.

Example conflict-safe patch flow:

    fetch_plan() {
      gh api "repos/$REPO/issues/comments/$COMMENT_ID" --jq '.body' > "$PLAN_FILE"
      gh api "repos/$REPO/issues/comments/$COMMENT_ID" --jq '.updated_at'
    }

    FIRST_UPDATED_AT=$(fetch_plan)

    python3 skills/execplan/scripts/manage_execplan_comment.py normalize \
      --input "$PLAN_FILE" \
      --output "$PLAN_FILE" \
      --title "Implement issue #$ISSUE" \
      --meta-json "{\"planRevision\": 2, \"lastSyncedAt\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"

    CURRENT_UPDATED_AT=$(gh api "repos/$REPO/issues/comments/$COMMENT_ID" --jq '.updated_at')
    if [ "$CURRENT_UPDATED_AT" != "$FIRST_UPDATED_AT" ]; then
      SECOND_UPDATED_AT=$(fetch_plan)
      python3 skills/execplan/scripts/manage_execplan_comment.py normalize \
        --input "$PLAN_FILE" \
        --output "$PLAN_FILE" \
        --title "Implement issue #$ISSUE" \
        --meta-json "{\"planRevision\": 2, \"lastSyncedAt\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
      CURRENT_UPDATED_AT=$(gh api "repos/$REPO/issues/comments/$COMMENT_ID" --jq '.updated_at')
      if [ "$CURRENT_UPDATED_AT" != "$SECOND_UPDATED_AT" ]; then
        echo "Remote managed comment changed twice. Stop and record a blocker instead of patching." >&2
        exit 1
      fi
    fi

    gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
      -X PATCH \
      -F "body=@$PLAN_FILE" \
      >/dev/null

After each execution-time patch, re-fetch the comment and confirm the intended `Progress` checkbox and matching `Audit Evidence` entry are visible remotely before continuing work.

## Record Progress and Evidence Deterministically

During execution, split the work into granular `Progress` items before code changes begin for a slice. Do not batch several completed items and update them later. A good slice captures one outcome that another agent could verify without interpreting several unrelated changes at once.

Add the next unchecked slice before implementation starts:

    python3 skills/execplan/scripts/manage_execplan_comment.py record-slice \
      --input "$PLAN_FILE" \
      --output "$PLAN_FILE" \
      --title "Implement issue #$ISSUE" \
      --slice-id EP-002 \
      --summary "Run focused validation for the parser changes" \
      --state pending

Update the local plan file for one completed slice:

    python3 skills/execplan/scripts/manage_execplan_comment.py record-slice \
      --input "$PLAN_FILE" \
      --output "$PLAN_FILE" \
      --title "Implement issue #$ISSUE" \
      --meta-json "{\"mode\": \"execution\", \"status\": \"in_progress\", \"lastSyncedAt\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}" \
      --slice-id EP-002 \
      --summary "Run focused validation for the parser changes" \
      --state done \
      --time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
      --kind validation \
      --action "pytest tests/test_parser.py -q" \
      --cwd "$PWD" \
      --result "Passed" \
      --proof "7 tests passed in 0.41s"

This updates the exact `Progress` line keyed by `EP-002` and creates or replaces the matching `Audit Evidence` entry for that slice.

## Review Gate

Before the first commit is created, run the `review-changes` skill against the current local diff as a required pre-flight review. Treat the adjudicated output as binding for delivery and loop until the latest adjudicated result is `LGTM`:

1. Fix every `Must fix (blocking)`, `Should fix (important)`, and in-scope `Nice to have / Nits` item that is safe to resolve.
2. Re-run the relevant validation commands.
3. Re-run `review-changes` against the updated local diff.
4. Repeat the fix -> validation -> review loop until the adjudicated review returns `LGTM`.
5. If `LGTM` cannot be reached safely, record the blocker, why it cannot be resolved now, and what follow-up is required; then stop before commit, push, and PR creation.
6. Do not commit, push, or open a PR unless the latest adjudicated review is `LGTM`.

Capture the review gate in both metadata and prose. At minimum, update:

- `reviewGate.status`
- `reviewGate.reviewedAt`
- `reviewGate.summary`
- `reviewGate.fixesApplied`
- `reviewGate.blockers`
- `reviewGate.lgtm`

## Finalize the Delivery

When all unchecked `Progress` items are complete and validation passes, do not stop at a local diff. Finish the GitHub delivery loop.

Create a branch using the repository naming convention:

    ISSUE_SLUG=implement-issue-103
    BRANCH="fix/$ISSUE-$ISSUE_SLUG"
    git checkout -b "$BRANCH"

Only after the review gate has returned `LGTM`, commit the work with an issue-linked message:

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

Request review from the original issue author when possible:

    VIEWER=$(gh api graphql -f query='query { viewer { login } }' --jq '.data.viewer.login')
    REVIEWER_REQUEST_STATUS="Issue author reviewer request not attempted yet."
    if [ -n "$ISSUE_AUTHOR" ] && [ "$ISSUE_AUTHOR" != "$VIEWER" ]; then
      if REVIEWER_OUTPUT=$(gh pr edit "$PR_URL" --add-reviewer "$ISSUE_AUTHOR" 2>&1); then
        REVIEWER_REQUEST_STATUS="Requested review from @$ISSUE_AUTHOR."
      else
        REVIEWER_REQUEST_STATUS="Could not request review from @$ISSUE_AUTHOR: $REVIEWER_OUTPUT"
      fi
    else
      REVIEWER_REQUEST_STATUS="Skipped reviewer request because the issue author matches the current user or could not be resolved."
    fi

## Render and Upsert the Final Handoff Comment

Render a stable handoff body with the fixed marker `<!-- execplan:handoff -->`:

    COMMIT_SHA=$(git rev-parse HEAD)
    VALIDATION_STATUS=${VALIDATION_STATUS:-}
    if [ -z "$VALIDATION_STATUS" ]; then
      echo "VALIDATION_STATUS must describe the validation that passed before posting the handoff comment." >&2
      exit 1
    fi

    HANDOFF_BODY=$(mktemp)
    python3 skills/execplan/scripts/manage_execplan_comment.py render-handoff \
      --issue "$ISSUE" \
      --issue-author "${ISSUE_AUTHOR:-}" \
      --viewer "$VIEWER" \
      --pr "$PR_URL" \
      --branch "$BRANCH" \
      --commit "$COMMIT_SHA" \
      --validation "$VALIDATION_STATUS" \
      --output "$HANDOFF_BODY"

Upsert that comment in place on retries:

    HANDOFF_MARKER="<!-- execplan:handoff -->"
    HANDOFF_COMMENT_ID=$(gh api "repos/$REPO/issues/$ISSUE/comments" \
      --paginate \
      --jq '.[] | select(.user.login == env.VIEWER and (.body | contains(env.HANDOFF_MARKER))) | .id' \
      | tail -n 1)
    if [ -n "$HANDOFF_COMMENT_ID" ]; then
      gh api "repos/$REPO/issues/comments/$HANDOFF_COMMENT_ID" \
        -X PATCH \
        -F "body=@$HANDOFF_BODY" \
        >/dev/null
      OWNER_NOTIFICATION_STATUS="Updated existing handoff comment."
    else
      gh issue comment "$ISSUE" --body-file "$HANDOFF_BODY" >/dev/null
      HANDOFF_COMMENT_ID=$(gh api "repos/$REPO/issues/$ISSUE/comments" \
        --paginate \
        --jq '.[] | select(.user.login == env.VIEWER and (.body | contains(env.HANDOFF_MARKER))) | .id' \
        | tail -n 1)
      OWNER_NOTIFICATION_STATUS="Created new handoff comment."
    fi

## Update Delivery Metadata

After PR creation, update the managed issue comment again so the issue records the final traceability details:

    python3 skills/execplan/scripts/manage_execplan_comment.py set-delivery \
      --input "$PLAN_FILE" \
      --output "$PLAN_FILE" \
      --title "Implement issue #$ISSUE" \
      --meta-json "{\"branch\": \"$BRANCH\", \"commit\": \"$COMMIT_SHA\", \"pr\": {\"url\": \"$PR_URL\"}, \"lastSyncedAt\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\", \"handoff\": {\"commentId\": ${HANDOFF_COMMENT_ID:-null}, \"status\": \"complete\"}, \"validation\": {\"status\": \"passed\", \"summary\": \"$VALIDATION_STATUS\"}}" \
      --branch "$BRANCH" \
      --commit "$COMMIT_SHA" \
      --pr "$PR_URL" \
      --reviewer-status "$REVIEWER_REQUEST_STATUS" \
      --handoff-status "$OWNER_NOTIFICATION_STATUS" \
      --validation-summary "$VALIDATION_STATUS"

Patch the managed comment with the refreshed body:

    gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
      -X PATCH \
      -F "body=@$PLAN_FILE" \
      >/dev/null

When updating the managed comment after delivery, include the final validation evidence plus the `review-changes` outcome that gated the commit, including any review-driven fixes or explicit blockers.

Delete temporary files after the push, PR creation, and handoff comment steps succeed or fail.

If the repository uses a non-`main` default branch or already has a stricter PR template, adapt the command and body to match local conventions while preserving explicit issue linkage.

## Failure and Recovery

If GitHub API writes fail:

1. Keep the current plan text in a temporary file.
2. Retry the `gh api` request after re-fetching `COMMENT_ID`, `updated_at`, and issue state.
3. If the remote comment changed unexpectedly, rebuild the edit against the latest body before retrying.
4. If retries keep failing, tell the user the issue comment could not be updated and include the exact failure point.
5. Do not silently fall back to a local permanent plan file unless the user explicitly approves that change in storage model.
