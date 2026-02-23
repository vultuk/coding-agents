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

## SubAgent Strategy

This workflow benefits from parallel SubAgent execution. Use the Task tool with these patterns:

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### Parallel Initial Analysis (Phase 1)

Launch these SubAgents **in parallel** at the start:

1. **Bash SubAgent**: Fetch failing run details
   ```
   Task(subagent_type="Bash", prompt="Run: gh run list --limit 10 --json databaseId,name,conclusion,headSha,headBranch and identify the most recent failure")
   ```

2. **Bash SubAgent**: Check current git status
   ```
   Task(subagent_type="Bash", prompt="Run git status and git branch to understand current state")
   ```

3. **Explore SubAgent**: Survey workflow files
   ```
   Task(subagent_type="Explore", prompt="Find all GitHub Actions workflow files in .github/workflows/ and summarise their purposes")
   ```

### Parallel Diagnosis (Phase 2)

Once you have the failing run ID, launch **in parallel**:

1. **Bash SubAgent**: Fetch full logs
   ```
   Task(subagent_type="Bash", prompt="Run: gh run view <RUN_ID> --log and save to action_failure.log")
   ```

2. **Explore SubAgent**: Analyse error patterns
   ```
   Task(subagent_type="Explore", prompt="Read action_failure.log and identify: 1) Error type (build/lint/type/test), 2) Affected files, 3) Root cause")
   ```

3. **Explore SubAgent**: Search codebase for related issues
   ```
   Task(subagent_type="Explore", prompt="Based on the error in <ERROR_SUMMARY>, search the codebase for related files and potential fixes")
   ```

### Fix Implementation (Phase 3)

For complex fixes, use a **Plan SubAgent** first:
```
Task(subagent_type="Plan", prompt="Plan the fix for CI failure: <ERROR_DETAILS>. Consider: affected files, test implications, minimal change approach")
```

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

Post a summary comment on the relevant PR (if applicable):
```bash
gh pr comment <PR_NUMBER> -b "<summary_of_fix>"
```

Include:
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
