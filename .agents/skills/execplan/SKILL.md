---
name: execplan
description: Create and execute living ExecPlans stored in GitHub issue comments instead of local markdown files. Use when Codex needs to turn a GitHub issue into a self-contained implementation plan, keep that plan updated while work progresses, or continue work from an existing issue-backed plan with a strict GitHub audit trail. Typical triggers include `Implement #123 using $execplan`, `Create an ExecPlan for issue #123`, `continue #123`, or any request to keep the issue comment as the source of truth.
---

# ExecPlan

Use this skill to manage a living ExecPlan inside one machine-managed GitHub issue comment. The GitHub thread is the audit log, not a secondary summary. The managed comment must stay current enough that another stateless agent or reviewer can reconstruct what happened from GitHub alone.

This skill should follow the spirit of the official Codex Exec Plans guide at [developers.openai.com/cookbook/articles/codex_exec_plans](https://developers.openai.com/cookbook/articles/codex_exec_plans), while adapting the storage model to a managed GitHub issue comment instead of a local `PLANS.md` file.

## Require Inputs and Preconditions

- Require a GitHub issue number.
- Require `gh` authentication that can read issues and edit comments in the target repository.
- Treat the GitHub issue comment as the source of truth. Do not create a persistent local ExecPlan file unless the user explicitly asks for an export.
- Use temporary files only as short-lived scratch space when preparing a comment body for `gh api`.
- Stop if the issue is closed unless the user explicitly asked for retrospective analysis or a closed-issue update.

## Claim the Issue Before Planning

Before drafting or refreshing the ExecPlan, visibly claim the issue in GitHub:

1. React to the issue itself with `👀`.
2. Assign the issue to the currently logged-in GitHub user.

Perform this claim step before generating the first ExecPlan draft so other humans and agents can see the issue is actively being worked. Make the step idempotent: re-running it must be safe if the reaction or assignee already exists.

After the managed ExecPlan comment has been created successfully, clear the temporary claim signal by removing the `👀` reaction from the issue and add the label `in progress`. Keep this step idempotent as well: removing a missing reaction or re-adding an existing label must not break the workflow.

Practical GitHub API note: deleting issue reactions via REST can return `404 Not Found` even when the reaction is visible. Prefer the GraphQL `removeReaction` mutation keyed by the issue node ID when clearing your own `EYES` reaction, and treat a missing reaction as a no-op.

## Load the Right Context

1. Read the target issue title, original author, body, labels, state, and existing comments.
2. Read repository-specific instructions that govern planning or implementation if they exist. Prioritize files such as `AGENTS.md`, `.agent/PLANS.md`, or equivalent local planning guidance.
3. Read the relevant code, tests, and configuration before writing the plan. The plan must be grounded in the actual repository, not in the issue text alone.
4. If the repository does not contain its own ExecPlan spec, follow [`references/github-execplan-comment-workflow.md`](references/github-execplan-comment-workflow.md) as the contract.

## Maintain One Canonical Comment

Follow the exact workflow in [`references/github-execplan-comment-workflow.md`](references/github-execplan-comment-workflow.md).

The storage model is strict:

- Keep exactly one machine-managed ExecPlan comment per issue.
- Identify the comment by the marker `<!-- execplan:managed -->` at the top of the Markdown comment body.
- If no managed comment exists, create one.
- If one exists, edit it in place.
- If multiple managed comments exist, keep the newest one, update it, and record the cleanup decision in the plan's `Decision Log`.
- Do not post routine status as new comments. Routine progress belongs inside the managed ExecPlan comment.
- The only allowed extra issue comment is a single final completion handoff comment with the marker `<!-- execplan:handoff -->`; update it in place on retries instead of posting duplicates.
- Once the managed comment exists, remove the initial `👀` reaction and ensure the issue has the label `in progress`.

## Managed Comment Contract

The managed comment body must be plain Markdown so GitHub renders headings, lists, and links normally. Do not wrap the plan in fenced code blocks. Write a self-contained ExecPlan that a stateless agent or novice human can follow without prior context.

The comment must always contain:

- The managed marker `<!-- execplan:managed -->`.
- A visible H1 title.
- A hidden metadata block near the top of the comment:
  `<!-- execplan:meta`
  JSON
  `-->`
- These sections, kept current at all times:
  `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`, `Context and Orientation`, `Plan of Work`, `Concrete Steps`, `Validation and Acceptance`, `Idempotence and Recovery`, `Artifacts and Notes`, `Interfaces and Dependencies`, `Audit Evidence`, `Delivery Metadata`.

The metadata block must include these top-level fields:

- `issue`
- `repo`
- `mode`
- `status`
- `issueAuthor`
- `commentId`
- `planRevision`
- `lastSyncedAt`
- `branch`
- `commit`
- `pr`
- `reviewGate`
- `validation`
- `handoff`

Use the helper at [`scripts/manage_execplan_comment.py`](scripts/manage_execplan_comment.py) to create or enrich this structure deterministically instead of hand-editing the hidden block.

Existing managed comments remain valid. On the next update, enrich them in place by adding the metadata block, `Audit Evidence`, `Delivery Metadata`, and slice IDs for new progress items. Preserve prior history rather than rewriting it.

## Plan Quality Bar

The visible comment should read like a good ExecPlan from the official guide, not like a template dump.

- Lead with the problem, the intended outcome, and the repository context before listing steps.
- Prefer short prose paragraphs for `Context and Orientation` and `Plan of Work`. Use bullets only where they materially improve scanability.
- Keep the initial plan lean. A healthy starting point is usually 2 to 5 independently verifiable slices, not a checklist for every clerical workflow step.
- Do not bundle review, commit, push, PR creation, and handoff into one giant progress slice. Track delivery in metadata unless it is a real remaining milestone.
- Avoid filler such as `None yet`, `Pending`, or speculative retrospective text unless there is genuinely nothing to say; when needed, keep it to one short line.
- Do not duplicate the same information across `Context and Orientation`, `Plan of Work`, and `Concrete Steps`.
- Use repository-relative paths in visible prose. Never paste machine-local absolute paths, Codex worktree paths, or user-home paths into the GitHub comment.
- When a working directory is needed in visible content or audit evidence, prefer `<repo-root>` or a repository-relative subdirectory.
- Name concrete files, modules, types, commands, and validation checks precisely enough that another agent can continue without re-discovery.

## Progress and Audit Evidence Rules

The `Progress` section is the only authoritative completion log.

- Every progress item must use a stable slice ID such as `EP-001`.
- Incomplete format:
  `- [ ] EP-001 Implement config parser`
- Complete format:
  `- [x] EP-001 (2026-03-26T14:05:00Z) Implement config parser`
- Use UTC ISO 8601 timestamps everywhere in the audit trail.
- The slice ID is the authoritative key. Wording can evolve, but the slice ID must stay stable.
- The only valid way to record completion is to flip the matching checkbox line in `## Progress`. Notes in other sections do not count unless the checkbox state also changes.

Every completed slice must add one matching entry in `## Audit Evidence` with these fields:

- `slice`
- `time`
- `kind`
- `action`
- `cwd`
- `result`
- `proof`

Allowed `kind` values are `context`, `implementation`, `validation`, `review`, `blocker`, and `delivery`.

Use the helper script to update progress and evidence together so the audit trail stays synchronized.

Each slice should be independently verifiable. Prefer slices such as `Add regression coverage for disabled-provider summaries` or `Update summary aggregation to exclude manual-off providers`, not broad bundles such as `Run review gate, resolve findings, and deliver`.

## Choose the Operating Mode

Use planning mode when the user asks to create, draft, refresh, or revise the ExecPlan. In this mode, create or update the managed issue comment but do not implement the code unless the user also asks for execution.

Use execution mode when the user asks to implement, continue, or execute the issue. In this mode, first refresh the managed issue comment so it reflects the current understanding, then perform the implementation. After every single completed unit of work, update the matching `Progress` item, append its audit evidence entry, patch that same GitHub comment, and re-read the remote comment to verify the intended change is visible before starting the next slice.

Execution mode is not complete when code and tests are done locally. It remains in progress until the local diff has been reviewed with the `review-changes` skill, every finding has been resolved or turned into an explicit blocker, the adjudicated review returns `LGTM`, and only then the branch is committed, pushed, turned into a pull request, and handed back to the original issue author.

## Concurrency and Idempotence Rules

- No long-lived local copy of the plan is authoritative.
- Before every comment edit, fetch the latest remote body and `updated_at`.
- If the remote comment changed since the last read, rebuild the edit against the fresh remote body and retry once.
- If a second conflict occurs, stop and record an explicit blocker in the managed comment rather than risking an overwrite.
- Before each progress update, refresh the temporary file from the managed comment so the next patch starts from the latest remote state.
- Treat a work slice as unfinished until the remote comment shows the checked checkbox and matching evidence entry.
- If work is interrupted, leave the comment in a resumable state. The next agent should be able to continue from the issue comment alone.

## Review, Delivery, and Handoff Rules

Before any commit is created in execution mode, run the `review-changes` skill against the local diff. Treat its adjudicated output as the required pre-flight review and loop until it returns `LGTM`.

- Fix every `Must fix (blocking)`, `Should fix (important)`, and in-scope `Nice to have / Nits` item that can be resolved safely.
- Re-run validation after review-driven fixes, then re-run `review-changes` against the updated diff.
- Continue the fix -> validation -> `review-changes` loop until the adjudicated review returns `LGTM`.
- If a finding cannot be fixed safely in scope, stop the delivery flow and record an explicit blocker with rationale and follow-up; do not commit, push, or open a PR.
- Do not create the commit, push, or PR unless the latest adjudicated `review-changes` result is `LGTM`.

The metadata block and prose sections must capture the review gate state:

- review timestamp
- findings summary
- whether fixes were applied
- whether blockers remain
- latest LGTM status

When all planned work and validation are complete, finish the delivery instead of stopping at local changes:

1. Review the managed comment one last time and ensure every completed `Progress` item, validation result, discovery, and outcome is reflected.
2. Run the `review-changes` skill against the current local diff before any commit is created.
3. Fix every adjudicated finding that is safe and in scope.
4. Re-run validation, then re-run `review-changes`; repeat until the latest adjudicated review returns `LGTM`.
5. If `LGTM` cannot be reached safely, record the blocker in the managed issue comment and stop before commit, push, and PR creation.
6. Create or switch to a branch that uses the repository convention `fix/<issue-number>-<short-slug>` unless a suitable branch already exists.
7. Commit the completed work with a concise imperative subject and a short body that explains what changed and why.
8. Push the branch to `origin`.
9. Create a pull request with explicit issue linkage and a reviewer-friendly description.
10. Request review from the GitHub user who originally opened the issue when GitHub allows it.
11. Create or update one final issue comment marked with `<!-- execplan:handoff -->`.
12. Update the managed issue comment so it includes final delivery metadata.

The `Delivery Metadata` section must record:

- branch
- commit
- PR number or URL
- reviewer-request result
- handoff-comment status
- final validation summary

The final handoff issue comment must mention `@<issue-author>` when the original issue author is known and is not the current logged-in user. Include the PR URL, branch name, commit hash, and concrete validation status in that comment so the owner can act from the issue thread alone. If the issue author cannot be resolved or is the current user, still create or update the completion comment, record why the direct mention was not used, and include the same delivery metadata.

## Helper Script

Use [`scripts/manage_execplan_comment.py`](scripts/manage_execplan_comment.py) to reduce brittle manual edits:

- `normalize`
  Ensures the managed marker, metadata block, and required sections exist.
- `record-slice`
  Upserts one `Progress` item and one matching `Audit Evidence` entry.
- `set-delivery`
  Renders the `Delivery Metadata` section deterministically.
- `render-handoff`
  Generates the stable final issue comment body with `<!-- execplan:handoff -->`.

Prefer the helper for structure updates and repeated audit operations. It does not replace the need to re-fetch the remote GitHub comment before patching.

Before posting or patching the managed comment, run `python3 .agents/skills/execplan/scripts/manage_execplan_comment.py lint --input "$PLAN_FILE"` to catch obvious visible-content mistakes such as machine-local absolute paths.

## Grounding and Safety Rules

- Base the plan and implementation on evidence from the issue, repository, and executed commands in the current run.
- Mark assumptions explicitly when issue requirements are incomplete.
- Do not claim tests, builds, or manual checks passed unless they actually ran.
- Do not self-waive pre-commit review. Run the `review-changes` skill, use its adjudicated output as the gate, and keep fixing, validating, and re-running review until the latest adjudicated result is `LGTM`. If `LGTM` cannot be reached safely, document the blocker and stop before commit, push, and PR creation.
- Prefer additive, reversible steps. If a step is risky, document the rollback or retry path in `Idempotence and Recovery`.
- Do not merge a PR or delete branches unless the user explicitly asks. Creating the branch, commit, push, linked PR, reviewer request, and final owner-notification comment is part of the normal completion flow for this skill, but only after the `review-changes` gate has returned `LGTM`.

## Expected User Requests

- `Create an ExecPlan for #103 using $execplan`
- `Implement #103 using $execplan`
- `Continue issue #103 with $execplan`
- `Refresh the ExecPlan comment for #103`

## Final Response Contract

At the end of a planning-only run, report that the ExecPlan comment was created or updated and summarize the main milestones captured in it.

At the end of an execution run, report what changed in code, which validations ran, that `review-changes` was run until `LGTM`, what review-driven fixes were applied, whether any findings remain as explicit blockers, the branch name, commit hash, PR URL, whether the original issue author was requested as a reviewer, whether the final issue handoff comment tagged that author, and confirm that the managed issue comment was updated to match the current state.
