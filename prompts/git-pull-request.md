---
name: git-pull-request
description: From unstaged changes, infer a branch name, produce AI-authored commit/PR messaging, push, and open the PR via gh. Supports both creating new branches from base and continuing work on existing feature branches.
arguments:
  - name: TARGET
    required: false
    description: Base branch to target (defaults to main, override via env TARGET)
  - name: DRAFT
    required: false
    description: Set to "true" to create a draft PR
---

# Git Pull Request

You are a release-minded CLI operator and technical writer. Using standard shell commands and GitHub CLI (`gh`), detect whether we are on the base branch or an existing feature branch. If on base, infer a meaningful branch name from the real changes, create the branch from up-to-date `main`, then continue. If already on a feature branch, reuse it. In all cases: write a highly descriptive AI-generated commit message, PR title, and PR body based on the actual diff, push, and open a PR.

## Constraints and Defaults

- **TARGET (base):** main (override via env TARGET)
- **Language:** UK English, clear prose for engineers and C-level readers
- **Style:** Conventional, but human-first. Avoid ticket codes in titles unless present in diff
- **Idempotent:** If a PR already exists for the branch, print its URL and exit

## Guards

- Ensure `gh auth status` passes and we're inside a git repo
- Ensure `origin` is a GitHub remote
- Abort with a clear message if working tree has conflicts or detached HEAD
- **Never commit files that may contain secrets** (.env, credentials, keys)

## SubAgent Strategy

This workflow benefits from **parallel context gathering** using SubAgents.

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### Phase 1: Parallel Context Collection

Launch these SubAgents **simultaneously** using multiple Task tool calls in a single message:

1. **Bash SubAgent**: Git state and changes
   ```
   Task(subagent_type="Bash", prompt="Run these commands and return results:
   - git rev-parse --abbrev-ref HEAD
   - git status --porcelain
   - git diff --name-only
   - git diff --name-only --cached
   - git rev-list --left-right --count HEAD...@{u} 2>/dev/null || echo 'no upstream'")
   ```

2. **Bash SubAgent**: Diff content
   ```
   Task(subagent_type="Bash", prompt="Run: git diff -U3 (unstaged) and git diff -U3 --cached (staged). Return both.")
   ```

3. **Bash SubAgent**: Auth and remote verification
   ```
   Task(subagent_type="Bash", prompt="Run: gh auth status && git remote get-url origin. Verify we're authenticated and have a GitHub remote.")
   ```

4. **Bash SubAgent**: Recent commit history for style
   ```
   Task(subagent_type="Bash", prompt="Run: git log --oneline -10 to understand commit message conventions in this repo")
   ```

5. **Bash SubAgent**: Check for existing PR
   ```
   Task(subagent_type="Bash", prompt="Run: gh pr list --head $(git rev-parse --abbrev-ref HEAD) --json url,state to check if PR exists")
   ```

### Phase 2: Analysis (After Context Gathered)

Use an **Explore SubAgent** to analyse the changes:
```
Task(subagent_type="Explore", prompt="Analyse these changes to determine:
1. TYPE bucket (fix/feat/perf/refactor/ci/build/docs/chore)
2. SCOPE (dominant path segment or package)
3. DESCRIPTOR (salient tokens from changes)
4. Any ticket patterns (ABC-123)
5. Security concerns (secrets, tokens)
6. Breaking changes
Changes: <DIFF_CONTENT>")
```

### Phase 3: Content Generation

For complex PRs, use a **general-purpose SubAgent** for message generation:
```
Task(subagent_type="general-purpose", prompt="Generate commit message, PR title, and PR body for these changes. Follow Conventional Commit style, UK English. Include: what changed, why, risks, test coverage. Changes: <ANALYSIS_RESULTS>")
```

## Collect Change Context (Unstaged First)

1. Gather files and diffs:
   - `FILES_UNSTAGED="$(git diff --name-only)"`
   - `FILES_STAGED="$(git diff --name-only --cached)"`
   - `DIFF_UNSTAGED="$(git diff -U0)"`
   - If `FILES_UNSTAGED` empty, fall back to staged:
     - `DIFF_STAGED="$(git diff -U0 --cached)"`
   - If both empty and no ahead commits: exit "nothing to commit"
     - Ahead commits check: `git status --porcelain=v2 -b` contains `ahead` or `git rev-list --left-right --count HEAD...@{u}` shows left count > 0

2. Extract signals for summarisation:
   - Added/removed/modified counts per path
   - Language mix by extension
   - Keyword cues from added lines (e.g., "fix", "regression", "refactor", "perf", "docs", "breaking", "deprecate")
   - Linked ticket patterns like `ABC-123` in added lines or file headers
   - Detect tests touched: `**/test/**`, `**/__tests__/**`, `*.test.*`, `*.spec.*`
   - Detect migrations/DB/schema changes and config/CI changes
   - **Detect sensitive tokens; if present, abort with a red-flag message**

## Infer Branch Name from Changes (Only If on Base)

3. **TYPE** bucket (priority order): fix > feat > perf > refactor > ci > build > docs > chore
   - Choose by keywords + file types; mixed changes favour fix/feat over docs/chore

4. **SCOPE:** dominant first path segment or package name (monorepo aware via nearest `package.json` `"name"`); fallback to repo name. Kebab-case, <=20 chars

5. **DESCRIPTOR:** top 2-3 salient tokens from the diff (added lines and filenames), kebab-case, <=24 chars; fallback "update"

6. Optional ticket prefix if `ABC-123` found

7. Compose BRANCH: `${TICKET+-${TICKET}-}${TYPE}/${SCOPE}-${DESCRIPTOR}-$(date -u +%Y%m%d-%H%M)`; normalise dashes; <=60 chars

## Branch Mode Selection

8. Determine current branch:
   - `CURRENT="$(git rev-parse --abbrev-ref HEAD)"`
   - `BASE="${TARGET:-main}"`
   - If `CURRENT = "${BASE}"`: **BASE MODE**
     a. `git fetch origin && git checkout "${BASE}" && git pull --rebase origin "${BASE}"`
     b. Infer `${BRANCH}` as above
     c. `git checkout -b "${BRANCH}"` (or `git checkout "${BRANCH}"` if exists)
   - Else: **FEATURE MODE**
     a. `BRANCH="${CURRENT}"`
     b. Confirm it is not the base: if it is, fall back to BASE MODE flow
     c. Ensure branch is clean enough to rebase if requested:
        - If `REBASE_ON_BASE=true` env set: `git fetch origin && git rebase "origin/${BASE}"` (abort with clear message on conflicts)
        - Otherwise, continue without rebase

## AI-Generate Commit Message, PR Title, PR Body (from Diff)

9. Provide the AI with:
   - `FILES_UNSTAGED`, `FILES_STAGED`
   - Use `DIFF_UNSTAGED` if present, else `DIFF_STAGED`
   - Detected signals: type, scope, descriptors, tickets, tests touched, potential breaking changes, perf notes, security-sensitive areas, migrations

10. Instruct the AI to produce:

    **A) Commit message** (Conventional Commit style, present-tense imperative):
    - Subject <= 72 chars: `<type>(<scope>): <concise action>`
    - Body wrapped ~72 cols:
      - What changed (grouped by theme)
      - Why (intent/rationale)
      - Risk/impact (perf, security, UX)
      - Breaking changes (explicit "BREAKING CHANGE:" with migration steps)
      - Tests: what's covered/added/updated
      - Links: referenced tickets/issues if found
    - Footers: `Co-authored-by` lines if authors detected from `git shortlog -sne HEAD~10..` touching changed files

    **B) PR title:**
    - <= 72 chars, human-readable, mirrors commit subject but without scope if noisy
    - Example: "Resolve order submission retries and tighten idempotency in API"

    **C) PR body** (sections, markdown):
    - Summary: 2-4 sentences in plain language for non-technical readers
    - Technical details: bullets grouped by feature/fix/refactor/perf
    - Risks & mitigations: clear, honest assessment
    - Breaking changes / Migration: explicit steps if any
    - Test coverage: what scenarios are covered; note any gaps
    - Rollback plan: how to safely revert if needed
    - Checklist: [ ] docs updated, [ ] dashboards/alerts adjusted, [ ] migrations applied

11. Validate outputs are non-empty and coherent; if the AI returns nothing, fail fast rather than committing junk

## Stage, Commit, Push

12. `git add -A`

13. Determine if there's anything to commit:
    - If diff exists: write AI commit message to a temp file and run `git commit -F <file>`
      - Capture commit SHA with `git rev-parse --short HEAD`
    - Else if there are ahead commits but no new changes: set `COMMIT=none` and continue

14. Ensure upstream:
    - If no upstream: `git push -u origin "${BRANCH}"`
    - Else: `git push` (on reject: `git pull --rebase` once, then retry)

## Create or View PR

15. If a PR already exists for `--head "${BRANCH}"`, print its URL and exit:
    - `gh pr view --head "${BRANCH}" --json url -q .url`

16. Else create it with AI-generated title/body:
    - `gh pr create --base "${BASE}" --head "${BRANCH}" --title "<AI TITLE>" --body "<AI BODY>"`
    - Add `--draft` flag if DRAFT argument is "true"

## When PR Description Needs Human Input

If the changes are ambiguous or the AI cannot determine intent:
1. Generate a placeholder PR body with `[TODO: describe why]` markers
2. Open the PR as a draft
3. Prompt the user: "I've created a draft PR but need your input on [specific sections]. Please review and update."

## Edge Cases and Quality Bars

- If only whitespace changes, set type `chore` and state that explicitly
- If both docs and code changed, prefer type `fix` or `feat`
- If schema or public API changes, require a "BREAKING CHANGE:" footer
- If secrets or keys appear in the diff, abort with a red-flag message (never commit secrets)
- Respect `TARGET` override; support repos using `master`
- Use UK spelling in prose ("optimise", "initialise", "licence", etc.)

## Final Output to Stdout

Print a concise report:
- `MODE=base|feature`
- `BRANCH=<name>`
- `COMMIT=<sha or none>`
- `PR=<url or existing url>`
- `TYPE=<type> SCOPE=<scope>`
- `DRAFT=true|false`
