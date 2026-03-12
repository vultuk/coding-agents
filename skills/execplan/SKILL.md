---
name: execplan
description: Create and execute living ExecPlans stored in GitHub issue comments instead of local markdown files. Use when Codex needs to turn a GitHub issue into a self-contained implementation plan, keep that plan updated while work progresses, or continue work from an existing issue-backed plan. Typical triggers include `Implement #123 using $execplan`, `Create an ExecPlan for issue #123`, `continue #123`, or any request to keep the issue comment as the source of truth.
---

# ExecPlan

Use this skill to manage a living ExecPlan inside one machine-managed GitHub issue comment. An ExecPlan is an executable specification: it explains why the work matters, what files and commands are involved, how progress is tracked, and how to prove the result works. This skill replaces the normal local `.md` ExecPlan file with a single authoritative issue comment that is edited in place as the work evolves.

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

## Load the Right Context

1. Read the target issue title, body, labels, state, and existing comments.
2. Read repository-specific instructions that govern planning or implementation if they exist. Prioritize files such as `AGENTS.md`, `.agent/PLANS.md`, or equivalent local planning guidance.
3. Read the relevant code, tests, and configuration before writing the plan. The plan must be grounded in the actual repository, not in the issue text alone.
4. If the repository does not contain its own ExecPlan spec, follow [`references/github-execplan-comment-workflow.md`](references/github-execplan-comment-workflow.md) as the contract.

## Choose the Operating Mode

Use planning mode when the user asks to create, draft, refresh, or revise the ExecPlan. In this mode, create or update the managed issue comment but do not implement the code unless the user also asks for execution.

Use execution mode when the user asks to implement, continue, or execute the issue. In this mode, first refresh the managed issue comment so it reflects the current understanding, then perform the implementation, and edit that same comment after every single `Progress` item is completed so observers can see the work advancing in near real time.

## Maintain One Canonical Comment

Follow the exact REST workflow in [`references/github-execplan-comment-workflow.md`](references/github-execplan-comment-workflow.md).

The required storage model is strict:

- Keep exactly one machine-managed ExecPlan comment per issue.
- Identify the comment by the marker `<!-- execplan:managed -->` at the top of the Markdown comment body.
- If no managed comment exists, create one.
- If one exists, edit it in place.
- If multiple managed comments exist, keep the newest one, update it, and record the cleanup decision in the plan's `Decision Log`.
- Do not post routine status as new comments. Routine progress belongs inside the managed ExecPlan comment.
- Once the managed comment exists, remove the initial `👀` reaction and ensure the issue has the label `in progress`.

## Write the ExecPlan

The managed comment body must be plain Markdown so GitHub renders the headings, lists, and links normally. Do not wrap the plan in fenced code blocks. Write a fully self-contained ExecPlan that a stateless agent or novice human can follow without prior context.

The plan must:

- Explain the user-visible outcome first.
- Define every non-obvious term in plain language.
- Name repository paths precisely.
- Include the exact commands to run and what success looks like.
- Stay up to date as the work changes.

The plan must always include these sections and keep them current:

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

Use timestamps in `Progress`. At the bottom of the plan, add a short revision note describing what changed and why.

Keep `Progress` granular enough that each checkbox represents one observable unit of work. Do not batch several completed items and update them later; mark each one complete and push the updated comment before moving on.

## Execute From the Comment

When executing the plan:

1. Re-read the latest managed comment before changing code so you do not overwrite newer plan edits.
2. Break the work into small `Progress` items that can be completed and reported independently.
3. Implement the next smallest verifiable slice.
4. Run validation that proves the slice works.
5. As soon as that `Progress` item is done, immediately edit the same GitHub comment to mark it complete and refresh any affected sections such as `Concrete Steps`, `Artifacts and Notes`, `Surprises & Discoveries`, `Decision Log`, or `Outcomes & Retrospective`.
6. Only then start the next `Progress` item.

If work is interrupted, leave the comment in a resumable state. The next agent should be able to continue from the issue comment alone.

## Finalize With Git and Pull Request

Once all planned work and validation are complete, finish the delivery instead of stopping at local changes:

1. Review the managed comment one last time and ensure every completed `Progress` item, validation result, discovery, and outcome is reflected.
2. Create or switch to a branch that uses the repository convention `fix/<issue-number>-<short-slug>` unless a suitable branch already exists.
3. Commit the completed work with a concise imperative subject and a short body that explains what changed and why.
4. Push the branch to `origin`.
5. Create a pull request with a structured, reviewer-friendly description.

The pull request must be explicitly linked to the issue so the relationship is traceable in GitHub. Use a closing keyword in the PR body such as `Closes #123` when the PR should close the issue on merge. If automatic closure would be wrong for the repository workflow, use a non-closing link such as `Refs #123`, but still include the issue number in the PR body.

The pull request description must be well written and implementation-aware. Use these sections unless the repository has a stricter local template:

- `## Why`
- `## What changed`
- `## Impact`
- `## Testing`
- `## Out of scope / follow-ups`

After the PR is created, update the managed issue comment so it includes the branch name, commit hash, PR number or URL, and final validation evidence.

## Grounding and Safety Rules

- Base the plan and implementation on evidence from the issue, repository, and executed commands in the current run.
- Mark assumptions explicitly when issue requirements are incomplete.
- Do not claim tests, builds, or manual checks passed unless they actually ran.
- Prefer additive, reversible steps. If a step is risky, document the rollback or retry path in `Idempotence and Recovery`.
- Do not merge a PR or delete branches unless the user explicitly asks. Creating the branch, commit, push, and linked PR is part of the normal completion flow for this skill.

## Expected User Requests

- `Create an ExecPlan for #103 using $execplan`
- `Implement #103 using $execplan`
- `Continue issue #103 with $execplan`
- `Refresh the ExecPlan comment for #103`

## Final Response Contract

At the end of a planning-only run, report that the ExecPlan comment was created or updated and summarize the main milestones captured in it.

At the end of an execution run, report what changed in code, which validations ran, the branch name, commit hash, PR URL, and confirm that the managed issue comment was updated to match the current state.
