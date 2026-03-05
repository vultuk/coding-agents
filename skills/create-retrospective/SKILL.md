---
name: create-retrospective
description: Create polished incident retrospectives and publish them to GitHub Discussions in the Retrospectives category. Use after a major bug fix, outage remediation, or production incident when Codex should reconstruct what happened from session actions, logs, issue/PR history, and code changes, then post the retrospective automatically.
---

# Create Retrospective

Generate a factual retrospective post from concrete evidence and publish it in the `Retrospectives` discussion category.

## Workflow

### 1. Establish scope

- Identify the incident target from user input first.
- Resolve linked artifacts:
  - GitHub issue number
  - PR number
  - Main fix commits
- If multiple incidents are possible, choose the one most directly tied to the merged fix and state the assumption.

### 2. Gather evidence

Collect enough detail to explain the full path from symptom to prevention:

- Session actions:
  - Commands executed
  - Logs queried
  - Diagnostics performed
  - Hypotheses tested and rejected
- Git evidence:
  - `git log --oneline --decorate -n 30`
  - `git show --stat <commit>`
- GitHub evidence:
  - `gh issue view <issue> --comments`
  - `gh pr view <pr> --comments --json number,title,body,author,state,mergeCommit,commits,files,reviews`
  - CI/check results relevant to the fix
- Operational evidence:
  - Include key log events or metrics used during debugging when available.

Do not invent actions or timestamps. Mark uncertain details explicitly as unknown.

### 3. Draft the retrospective

- Load `references/retrospective-template.md`.
- Fill each section with concrete evidence.
- Prefer direct causal sequencing:
  - Detection -> investigation -> root cause -> fix -> validation -> prevention.
- Keep tone professional and concise.
- Redact secrets, credentials, and sensitive identifiers.

### 4. Publish automatically

- Save the final markdown body to a temporary file.
- Post a new discussion using:

```bash
python3 skills/create-retrospective/scripts/post_retrospective_discussion.py \
  --title "[Retrospective] <incident title> (<YYYY-MM-DD>)" \
  --body-file /tmp/retrospective.md
```

- Default category is `Retrospectives`.
- Override repository or category when needed:

```bash
python3 skills/create-retrospective/scripts/post_retrospective_discussion.py \
  --repo owner/repo \
  --category "Retrospectives" \
  --title "<title>" \
  --body-file /tmp/retrospective.md
```

### 5. Return completion details

- Return the posted discussion URL.
- Summarize:
  - Incident title
  - Root cause
  - Fix summary
  - Follow-up actions

If posting fails, provide the exact error and rerun once with `--dry-run` to preserve the generated draft.
