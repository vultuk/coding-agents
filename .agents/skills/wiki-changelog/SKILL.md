---
name: wiki-changelog
description: Generate human-readable daily changelog summaries from merged GitHub pull requests and update a repository wiki `Changelog.md` safely and idempotently. Use when asked to update a repo wiki changelog, backfill daily changelog entries from merged PR history, refresh GitHub wiki release notes, or maintain a wiki `Changelog.md` for a repository with wiki pages enabled.
---

# Wiki Changelog

Update a repository wiki changelog by grouping merged pull requests by day and writing one short, plain-English summary paragraph per date.

## Require Inputs And Defaults

- Require a target repository in `OWNER/REPO` form. If the user does not provide it, infer it from the current git remote and confirm only if inference is ambiguous.
- Accept an optional timezone. Default to `UTC`.
- Use a temporary working directory for wiki cloning and cleanup.
- Write for non-technical readers: one short paragraph per date, no PR numbers, no exhaustive change lists, and prefer user-visible impact over implementation minutiae.
- Treat the task as incomplete until every merged PR after the cutoff has been assigned to a date section or explicitly marked blocked.

## Use The Right Execution Pattern

- Use shell tools for `gh`, `git`, and filesystem operations.
- Parallelize only independent setup work such as authentication checks, wiki clone setup, and merged PR retrieval.
- Keep the final wiki edit, commit, and push sequence strictly serial to avoid conflicts and duplicate sections.
- Prefer direct execution over planning prose. This skill is operational, not advisory.

## Validate Preconditions

1. Run `gh auth status` and fail fast with a clear message if GitHub CLI authentication or repo access is missing.
2. In unattended or profile-isolated environments, set `GH_CONFIG_DIR` if GitHub auth lives outside the active `HOME`, then run `gh auth setup-git` so wiki clone/pull/push uses the GitHub CLI credential helper reliably.
3. Set explicit commit identity before writing the wiki so commits do not fall back to generic machine defaults. Prefer exported environment variables for cron-safe runs, for example `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL`.
4. Confirm the repository wiki is accessible before doing substantive work. Prefer `gh repo clone OWNER/REPO.wiki "${WORKDIR}/wiki"` or `git ls-remote https://github.com/OWNER/REPO.wiki.git`; do **not** rely on `gh repo view OWNER/REPO.wiki`, which can fail with a GraphQL repository-resolution error even when the wiki clone is accessible.
5. Clone the wiki into a temporary directory:

```bash
gh repo clone OWNER/REPO.wiki "${WORKDIR}/wiki"
```

6. Ensure `Changelog.md` exists inside the wiki clone. If absent, create it with:

```markdown
# Changelog
```

## Determine The Cutoff

- Parse the most recent date header matching `^##\s+(\d{4}-\d{2}-\d{2})$`.
- If a date exists, set the cutoff to that date at `23:59:59` in the requested timezone.
- If no date exists, use `1970-01-01T00:00:00` in the requested timezone.
- Never create a duplicate `## YYYY-MM-DD` section.
- If the existing section for a date is present but clearly low-quality, generic, or repetitive, treat the task as a rewrite of that existing section instead of skipping it. In that case, regenerate the paragraph for the existing date from the merged PRs for that date and replace the old text in place.

## Fetch Merged Pull Requests

Fetch merged PRs strictly after the cutoff from the main repository, not the wiki clone.

- Prefer `gh` commands or `gh api` queries that expose `mergedAt`, `title`, `body`, `author`, and labels.
- Paginate until exhausted. Do not stop at the first page if more results may exist.
- Use simple retry with backoff (`2s`, `4s`, `8s`) for transient API or rate-limit failures.
- Group PRs by the calendar date of `mergedAt` in the requested timezone, not by creation date.
- Optionally detect linked issues from PR bodies using close/fix/resolve keywords. This is best-effort only and must not block completion.

## Summarize By Date

For each date with at least one merged PR:

- Write one paragraph of `1-3` sentences.
- Cluster related work into themes such as features, fixes, infrastructure, docs, or reliability.
- Prefer plain language and user-facing outcomes.
- Name the actual product areas, workflows, or systems touched whenever the PR data supports it: for example coverage reporting, LP exposure, copy trading, MT5 equity, settlement flows, onboarding, notifications, admin tooling, or specific services.
- Use concrete nouns and verbs taken from PR titles and bodies; do **not** flatten a day into vague buckets when more specific phrasing is available.
- Avoid PR numbers, branch names, commit hashes, and low-level implementation jargon.
- Skip dates that already exist in `Changelog.md`.

### Anti-Slop Rules

Do **not** use repetitive filler or App-Store-style boilerplate such as:
- "focused on ..."
- "behind-the-scenes deployment and infrastructure work"
- "clearer documentation and guidance"
- "new capabilities"
- "bug fixes and smoother day-to-day behavior"
- "combining several small changes"
- "more polished and dependable experience"

Instead, summarize what actually changed and why it matters. A reader should be able to tell one date apart from another.

Prefer this shape:
- sentence 1: the most important concrete product or operational changes
- sentence 2: secondary improvements or reliability work, also named specifically
- optional sentence 3: only if needed for another clearly distinct theme

If a date has many unrelated PRs, mention the top `2-4` concrete themes rather than collapsing everything into generic categories.

Example tone:

> Coverage and exposure reporting became more consistent, with adjustments treated as active hedges, LP exposure shown in lots, and position pricing corrected for more accurate P/L. Copy-trading composition now aligns better with MAM details, and operators can control LP aggregation separately for bid and ask sides. Under the hood, Rust services and CI workflows were hardened for faster, more reliable delivery.

## Update The Wiki

Insert new sections at the top of `Changelog.md`, newest first, using:

```markdown
## YYYY-MM-DD
<summary paragraph>
```

Before committing, verify:

- Date grouping used the requested timezone consistently.
- Each new date appears exactly once.
- Sections were inserted newest-first.
- `Changelog.md` remains valid markdown and only intended sections changed.

If there are no merged PRs after the cutoff, exit cleanly without editing, committing, or pushing.

## Commit And Push

Commit only the changelog update:

```bash
git add Changelog.md
git commit -m "chore(changelog): update for YYYY-MM-DD"
git push
```

- If multiple dates were added, use a single commit message that reflects the covered range.
- If the push is rejected because the wiki changed remotely, pull with rebase once, resolve the changelog file carefully, and retry the push.
- Never delete or modify files outside the temporary working directory and the intended wiki file.

## Output Contract

Return a concise execution summary that includes:

- Dates added, newest first
- PR count summarized for each added date
- Any explicitly blocked date or PR grouping
- Or a clear statement that no changes were needed

## Finish Cleanly

- Remove the cloned wiki directory from the temporary working directory when done.
- Report a concise result including dates added and PR counts per date, or state that no changes were needed.
