---
name: fix-github-actions
description: Identify and fix failing GitHub Actions workflows for the current repository. Analyses failure logs, diagnoses issues, applies fixes, and verifies the workflow passes.
arguments:
  - name: RUN_ID
    required: false
    description: Specific workflow run ID to fix (auto-detects latest failure if not provided)
  - name: WORKFLOW_NAME
    required: false
    description: Specific workflow name to focus on
---

# Fix GitHub Actions

Using the gh command, identify and fix any failing GitHub Actions workflows for the current repository.

## Prerequisites

- `gh` CLI authenticated with repo access
- Git repository with GitHub remote
- Write access to push fixes

## Codex Execution Strategy

Translate the old subagent plan into Codex-native phases:

- Use `multi_tool_use.parallel` for independent discovery:
  - latest failing run lookup
  - current git state
  - workflow-file inventory under `.github/workflows/`
- Once `RUN_ID` is known, use `multi_tool_use.parallel` again for:
  - full log retrieval
  - targeted codebase searches for affected files/config
  - any bounded sidecar analysis that classifies the failure type and root cause
- Use `functions.update_plan` for a short fix plan when the failure spans multiple files or systems.
- Use `functions.exec_command` for all `gh`, git, test, and build commands, and `apply_patch` for manual edits.

## Completion Contract

- Treat the task as incomplete until the failing workflow is either passing, re-run and still failing with a documented blocker, or explicitly `[blocked]`.
- Do not stop after diagnosing the first symptom if the root cause has not been verified locally.
- Keep a retry checklist per failure class so repeated failures are tracked rather than rediscovered.

## Verification Loop

Before finalizing:
- verify the fix addresses the failure class seen in the retrieved logs,
- run the narrowest meaningful local validation before pushing,
- confirm the re-run workflow result or the exact blocked state,
- include any remaining gaps if local and remote validation differ.

## Workflow

### 1. Detect the latest failing run

Use `gh run list --limit 10 --json databaseId,name,conclusion,headSha,headBranch` to find the most recent run with `"conclusion": "failure"`.

Store its ID as `<RUN_ID>`.

If no failures found, report success and exit.

### 2. Pull the failing logs

Retrieve the logs for that run using:
```bash
gh run view <RUN_ID> --log > action_failure.log
```

Analyse the log output to determine the cause of failure:
- Build errors (compilation, bundling)
- Lint issues (ESLint, Prettier, etc.)
- Type errors (TypeScript, Flow)
- Test failures (unit, integration, e2e)
- Missing dependencies
- Environment/configuration issues
- Timeout or resource limits

### 3. Diagnose and repair

Based on the log details, inspect relevant files and code paths.

Apply necessary fixes to resolve the failure. Examples include:
- Updating syntax or import paths
- Adjusting configuration or environment variables
- Fixing tests or build commands
- Adding missing dependencies
- Updating lockfiles
- Fixing type errors

**Important:** Understand the failure context fully before changing code. Only make meaningful fixes, not superficial edits.

### 4. Verify the fix

Commit and push your changes:
```bash
git add -A
git commit -m "fix(ci): <summary of fix>

- <detailed explanation>
- Resolves workflow failure in <workflow_name>"
git push
```

Monitor the re-triggered workflow:
```bash
gh run watch
```

If the workflow is not automatically triggered, manually trigger it:
```bash
gh workflow run <WORKFLOW_NAME> --ref <BRANCH_NAME>
```

### 5. Report progress

If the user explicitly asked for a PR update, post a summary comment on the relevant PR:
```bash
gh pr comment <PR_NUMBER> -b "<summary_of_fix>"
```

Otherwise, include the same summary in the final response only:
- The error identified
- The exact change implemented
- Confirmation that the workflow re-run has passed (or next steps if still failing)

## Common Failure Patterns

| Pattern | Likely Cause | Fix |
|---------|--------------|-----|
| `ENOENT: no such file` | Missing file or wrong path | Check paths, add missing files |
| `Cannot find module` | Missing dependency | Run `npm install` or add to package.json |
| `Type error` | TypeScript issue | Fix type annotations |
| `Test failed` | Code/test mismatch | Fix code or update test expectations |
| `ENOMEM` | Out of memory | Increase memory limit or optimise |
| `rate limit` | GitHub API limits | Add retry logic or reduce API calls |
| `Permission denied` | Token/permission issue | Check workflow permissions |

## Iterative Fixing

If the first fix doesn't resolve the issue:
1. Re-fetch logs from the new run
2. Identify if it's a new failure or the same issue
3. Apply additional fixes
4. Repeat until passing or escalate to user

Limit to 3 automatic fix attempts before asking for human intervention.

## Output

Report final status:
- `WORKFLOW=<name>`
- `RUN_ID=<id>`
- `STATUS=fixed|partial|needs-attention`
- `COMMITS=<list of fix commits>`
- `PR_COMMENT=<url if posted>`
