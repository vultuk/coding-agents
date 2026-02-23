---
name: wiki-changelog
description: Generate human-readable daily changelog summaries from merged PRs and update the repository's Wiki Changelog.md, safely and idempotently.
arguments:
  - name: REPO
    required: true
    description: Repository in OWNER/REPO format
  - name: TZ
    required: false
    description: Timezone for date calculations (defaults to UTC)
---

# Wiki Changelog

You are an expert project manager with 25 years of experience translating between software engineers and non-technical stakeholders.

**Goal:** Generate human-readable daily changelog summaries from merged PRs and update the repo's Wiki (Changelog.md), safely and idempotently.

## Constraints and Defaults

- **TIMEZONE:** UTC (override via TZ argument). DATE_FMT: YYYY-MM-DD
- **REPO:** $REPO (OWNER/REPO format)
- **WORKDIR:** a temporary folder
- **Style:** 1 short paragraph per date, plain English for non-technical readers; no PR numbers; themes > minutiae; mention user-visible impacts when possible

## SubAgent Strategy

This workflow benefits from parallel operations in the setup and summarisation phases.

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### Phase 1: Parallel Setup

Launch these SubAgents **simultaneously**:

```
# Launch in a single message with multiple Task calls:

Task(subagent_type="Bash", prompt="Verify gh auth status has repo scope. Return auth status and any errors.")

Task(subagent_type="Bash", prompt="Clone the wiki repository:
gh repo clone $REPO.wiki /tmp/wiki-changelog-workdir/wiki
Return: success/failure and path to cloned wiki")

Task(subagent_type="Bash", prompt="Fetch merged PRs from $REPO:
gh pr list --repo $REPO --state merged --limit 200 --json number,title,body,mergedAt,author,labels
Return: JSON array of merged PRs")
```

### Phase 2: Parallel Date Summarisation

When multiple dates have PRs to summarise, launch **parallel summarisation SubAgents**:

```
# For each date with merged PRs, launch in parallel:

Task(subagent_type="general-purpose", prompt="Summarise these PRs merged on 2024-01-15 into a single paragraph for non-technical readers:
PRs: <LIST_OF_PR_TITLES_AND_BODIES>
Style: Plain English, focus on user-visible impacts, no PR numbers, themes over details.
Example: 'Polished onboarding with clearer error handling, trimmed API latency on order flow.'", model="haiku")

Task(subagent_type="general-purpose", prompt="Summarise these PRs merged on 2024-01-14 into a single paragraph for non-technical readers:
PRs: <LIST_OF_PR_TITLES_AND_BODIES>
Style: Plain English, focus on user-visible impacts, no PR numbers, themes over details.", model="haiku")

# ... repeat for each date
```

### Phase 3: Sequential Commit

The final commit and push must be sequential to avoid conflicts:
```
Task(subagent_type="Bash", prompt="In /tmp/wiki-changelog-workdir/wiki:
1. Update Changelog.md with new date sections (newest first)
2. git add Changelog.md
3. git commit -m 'chore(changelog): update for YYYY-MM-DD to YYYY-MM-DD'
4. git push (retry once with pull --rebase if rejected)")
```

## Setup

1. Ensure `gh auth status` is OK (repo scope). Fail fast with a clear error if not.

2. Create WORKDIR and clone wiki:
   ```bash
   gh repo clone $REPO.wiki "${WORKDIR}/wiki"
   ```
   Or `gh repo clone $REPO.wiki` if WORKDIR not set.

3. In `${WORKDIR}/wiki`, ensure `Changelog.md` exists; if not, create an empty file with a top-level title.

## Determine "Since" Cutoff

4. Parse the most recent date header in `Changelog.md` matching `^##\s+(\d{4}-\d{2}-\d{2})$`.
   - If found, set CUTOFF = that date's 23:59:59 in TZ
   - If none, set CUTOFF = 1970-01-01T00:00:00 in TZ

## Fetch Merged PRs

5. From the main repo (not the wiki clone), fetch merged PRs strictly after CUTOFF:
   ```bash
   gh pr list --state merged --limit 200 --search "merged:>YYYY-MM-DD" \
     --json number,title,body,mergedAt,author,labels
   ```
   - If >200 possible, page until exhausted
   - Treat `mergedAt` in TZ; group by calendar DATE_FMT of `mergedAt` (not createdAt)

## Linked Issues (Best-Effort)

6. For each PR, detect linked issues via common close keywords in the body (`close(s) #\d+`, `fix(es) #\d+`, `resolve(s) #\d+`). Optional: enrich via `gh api` timeline if available. Do not block on this.

## Summarisation

7. For each date with >=1 merged PR:
   - Write one paragraph (1-3 sentences) summarising the day's work in natural prose:
     - Cluster by theme (features, fixes, infra, docs)
     - Avoid jargon; surface user impact where relevant
     - Example tone: "Polished onboarding with clearer error handling, trimmed API latency on order flow, and fixed edge-case crashes in the exporter."
   - Do NOT list PRs or numbers. Do NOT duplicate an existing date section.

## Insert and Commit

8. In `Changelog.md`, if a section `## DATE` already exists, skip that date (idempotent).

9. Otherwise, insert each new date section at the top (newest first):
   ```markdown
   ## YYYY-MM-DD
   <paragraph>
   ```

10. Commit and push the wiki:
    ```bash
    git add Changelog.md
    git commit -m "chore(changelog): update for YYYY-MM-DD"
    git push
    ```
    For multiple dates, batch into a single commit with range in message.

## Cleanup

11. Remove the cloned wiki directory from WORKDIR when done.

## Guards and Edge Cases

- If no merged PRs after CUTOFF, do nothing and exit cleanly
- Use UTC consistently unless TZ provided; date grouping must be stable
- Handle rate limits with a simple retry (up to 3 attempts, backoff 2s/4s/8s)
- Never delete outside WORKDIR; refuse if path sanity checks fail
- If the wiki push is rejected due to remote updates, pull/rebase once and retry push

## Output

Print a concise summary:
- Dates added (if any)
- Number of PRs summarised per date
- Or confirmation that no changes were needed
