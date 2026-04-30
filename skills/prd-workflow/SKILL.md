---
name: prd-workflow
description: Turn project ideas into comprehensive PRDs via structured questioning, then post as GitHub issues. Ensures consistent PRD format every time.
triggers:
  - user says "create a prd" or "new prd" or "I have an idea"
  - user describes a feature, bug, enhancement, or fix they want documented
  - user asks to write up a project requirement
---

# PRD Workflow

## Phase 1: Intake
1. User provides initial idea/description
2. Identify which repo this targets (ask if unclear):
   - afx Markets: nummus-software/afx-markets (local: /home/ec2-user/Development/Work/afx-markets)
   - afx Hedge Fund: nummus-software/afx-hedge-fund (local: /home/ec2-user/Development/Work/afx-hedge-fund)
   - igi-fund-managers: nummus-software/igi-fund-managers (local: /home/ec2-user/Development/Work/igi-fund-managers)
3. Classify type: Feature / Enhancement / Bug Fix / Refactor / Infrastructure

## Phase 2: Grilling Questions
IMPORTANT: Start by confirming WHERE in the system this feature lives before exploring code. Ask the user which part of the codebase / which existing system this relates to. Do NOT assume based on keywords — e.g. "MT5 accounts" doesn't mean it's in the mt5-proxy; it could be in the bridge/MAM system. Wrong assumptions waste time and annoy the user.

Ask targeted questions across these areas (not all at once — batch 3-5 at a time based on relevance):

**Problem & Context**
- What problem does this solve? Who is affected?
- What happens today without this? What's the impact?

**Scope & Requirements**
- What exactly should this do? Walk me through the ideal user flow
- What are the inputs and outputs?
- Are there specific business rules or logic?
- What data is involved? Any new models/fields/APIs?

**Edge Cases & Constraints**
- What should NOT be in scope?
- Known edge cases or error scenarios?
- Performance requirements or constraints?
- Security or permissions considerations?

**Dependencies & Integration**
- Does this depend on other work or systems?
- Does anything else depend on this?
- Third-party services or APIs involved?

**Acceptance Criteria**
- How do we know this is done?
- What should QA specifically test?

**Priority & Timeline**
- Priority level (Critical / High / Medium / Low)?
- Any deadline or sprint target?

Ask priority early in the grilling (second or third batch), not at the very end — it shapes the depth of detail needed.

When useful, check the local codebase to understand current implementation and ask smarter questions.
If `read_file` unexpectedly returns empty output for a known-existing file, or `search_files` is unavailable because `rg`/`find` is missing, fall back to `execute_code` with Python `Path.read_text().splitlines()` to inspect exact line ranges directly from the local repo. This is a reliable fallback for PRD work when filesystem helper tools are degraded.

## Phase 3: PRD Generation
Once all questions are answered, generate the PRD using the EXACT template below.

## Phase 4: Review & Post
1. Present the full PRD to the user for review
2. Ask for any changes
3. Once approved, post as a GitHub issue:
   - Repo: as identified in Phase 1
   - Title: "PRD: <descriptive title>"
   - Body: the full PRD markdown
   - Labels: add relevant labels if available (enhancement, bug, etc.)

---

## PRD Template

```markdown
# PRD: [Title]

**Type:** [Feature / Enhancement / Bug Fix / Refactor / Infrastructure]
**Priority:** [Critical / High / Medium / Low]
**Target Repo:** [repo name]
**Date:** [YYYY-MM-DD]
**Author:** Simon Skinner

---

## 1. Overview
[2-3 sentence summary of what this is and why it matters]

## 2. Problem Statement
[What problem exists today? Who is affected and how?]

## 3. Goals & Objectives
- [Goal 1]
- [Goal 2]
- [Goal 3]

## 4. Non-Goals (Out of Scope)
- [What this does NOT cover]

## 5. Detailed Requirements

### 5.1 Functional Requirements
| ID | Requirement | Details |
|----|-------------|---------|
| FR-01 | [Requirement] | [Details] |
| FR-02 | [Requirement] | [Details] |

### 5.2 Non-Functional Requirements
| ID | Requirement | Details |
|----|-------------|---------|
| NFR-01 | [Requirement] | [Details] |

## 6. User Flow / Technical Flow
[Step-by-step walkthrough of how this works from the user or system perspective]

1. [Step 1]
2. [Step 2]
3. [Step 3]

## 7. Data & API Changes
[New models, fields, endpoints, or data flow changes. "None" if not applicable]

## 8. Dependencies
[External services, other PRDs, or prerequisites. "None" if not applicable]

## 9. Edge Cases & Error Handling
| Scenario | Expected Behavior |
|----------|-------------------|
| [Edge case 1] | [What should happen] |
| [Edge case 2] | [What should happen] |

## 10. Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## 11. QA / Testing Notes
[Specific things QA should verify, test scenarios, devices/browsers if relevant]

## 12. Timeline & Milestones
[Any deadlines, sprint targets, or phasing information]

## 13. Open Questions
[Anything still unresolved that needs further discussion]
```

---

## Pitfalls
- Don't dump all questions at once — batch them 3-5 at a time, contextually
- Always check the local codebase when the idea touches existing functionality
- Never skip the review step before posting to GitHub
- Keep the grilling conversational, not robotic — adapt questions to the specific idea
- If the user says "that's it" or "nothing else", wrap up — don't over-question
- Read the user's initial description carefully — they often mention key concepts (e.g. FIFO, scaling, tracking). Build on these specifics in your questions rather than asking them to re-explain what they already said
- Ask priority and timeline in the second or third round of questions, not as the final question before writing — it informs how detailed the PRD needs to be
- DO NOT assume which system/service a feature belongs to based on domain keywords. Always ask the user first before exploring code. e.g. "MT5 accounts" could mean the bridge/MAM system, not the mt5-proxy app.
- When exploring existing code, ask the user to confirm the relevant directory/module BEFORE diving in — saves time and avoids going down wrong paths
- If the user explicitly says they do not care which module owns the change yet (e.g. "leave that to the developer, just write a PRD"), do not keep blocking on module confirmation. Instead, inspect the most likely repo areas yourself to ground the PRD in current patterns, then clearly frame the exact implementation location as a developer decision in the PRD.
- Local repos may not always be cloned/available on the current machine — don't let failed code exploration block the conversation. When the local filesystem is unavailable, use `execute_code` with `subprocess.run()` to browse the repo via GitHub API:
  ```python
  import subprocess, os, yaml, base64
  # Read token from gh CLI config
  with open(os.path.expanduser("~/.config/gh/hosts.yml")) as f:
      hosts = yaml.safe_load(f)
  os.environ['GITHUB_TOKEN'] = hosts['github.com']['oauth_token']
  # Browse repo tree recursively
  r = subprocess.run(["gh", "api", "repos/OWNER/REPO/git/trees/main?recursive=1",
       "--jq", '.tree[] | select(.path | test("some/pattern")) | .path'],
      capture_output=True, text=True, env=os.environ)
  # Fetch file contents
  r = subprocess.run(["gh", "api", f"repos/OWNER/REPO/contents/{filepath}", "--jq", ".content"],
      capture_output=True, text=True, env=os.environ)
  content = base64.b64decode(r.stdout.strip()).decode('utf-8')
  ```
  This lets you explore project structure, read route files, understand patterns, and write informed PRDs even without local access.
- If local files do exist but `read_file` returns empty content or `search_files` is unavailable/broken, fall back to `execute_code` and inspect files directly with Python (`Path.read_text().splitlines()`) so you can still quote exact line ranges from the local repo. This is especially useful for large TypeScript/Rust files where file tools intermittently fail despite the files being present.
- `search_files` file globs may not behave like shell brace expansion (for example `*.{ts,tsx,js,jsx}` can miss expected files). For PRD codebase exploration, prefer separate searches per extension, broad file discovery first, or `execute_code` keyword scans when results look suspiciously empty.
- When posting the GitHub issue, write the PRD body to a temp file and use `gh issue create --body-file /tmp/prd_body.md` — avoids shell escaping issues with complex markdown containing tables, pipes, backticks, etc.
- Prefer writing the temp PRD body file via `execute_code` + Python (`Path(...).write_text(...)`) rather than `write_file` when the markdown contains formatting like `**bold**`, tables, or other special characters. In some environments, `write_file` can fail while interpreting markdown-heavy content, whereas Python file writes are reliable.
- If the `terminal()` tool returns empty output, fall back to `execute_code` with `subprocess.run()` for GitHub CLI operations
- When the PRD has open questions directed at specific people, use @mentions in the Open Questions section AND add them as assignees with `--assignee username` when creating the issue so they get GitHub notifications
- When checking the codebase for existing endpoints/APIs, verify what's already available before writing the PRD — this ensures the Data & API Changes section accurately reflects what's new vs existing. Use the route files and existing patterns to inform the PRD's technical detail
- Before creating a new PRD issue, search existing GitHub issues (open and recently closed) for the same area/keywords so you can avoid duplicating active work, reference related parent/child issues, and pitch the new PRD at the correct layer of scope. This is especially important when the repo already has recent PRDs or implementation issues in the same feature area.
- If the user refers to "this workaround", "that issue", or another recently discussed change without restating the details, use `session_search` first to recover the missing context before asking them to repeat themselves. When the recovered context is strong enough, draft the PRD from that evidence and label any assumptions explicitly.
- If the user explicitly asks you to "write up a GitHub issue" for a clearly scoped workaround/fix and the needed context can be recovered from session history, existing issues, and code inspection, do not block on a separate review round. Draft the PRD, post the issue directly, and make the assumptions/remaining open questions explicit in the issue body.
- If you find an existing issue that already matches the requested feature closely, do not blindly create a duplicate PRD. Present the user with options such as: (1) upgrade the existing issue into the full PRD template, (2) create a separate PRD because the scope is materially different, or (3) review/summarize the existing issue first. In afx-markets this is especially useful because implementation-scoping issues may already exist before the user asks for a formal PRD.
- If the feature needs to trigger an existing downstream workflow (for example publishing an order into an existing execution path), inspect adjacent modules that already do something similar even if they are slightly out of scope for the final PRD. This helps you reference the real integration pattern without over-scoping the change. Example: for a reports UI/backend action that should send a trade into the existing execution pipeline, inspect any current manual-trade or adjustment flows to understand validation, confirmation UX, payload shape, and publish mechanism before drafting the PRD.
- For MCP-server PRDs in afx-markets, inspect both `libs/mcp-server/core/src/lib/server/mcp-capability-catalog.ts` and `apps/reports-api/src/routes/chat-mcp-tools.ts`, not just the individual tool files. The active capability catalog and chat namespace allow-lists determine what users can actually call, and they may still advertise legacy/mock/simple tools even when richer backend routes already exist.
- For portal/UI PRDs, check existing component patterns (modal styles, data fetching with TanStack Query, Storybook requirements) so the PRD references the correct conventions and the developer knows exactly which patterns to follow
- For afx-markets portal reporting PRDs specifically, inspect `apps/portal/src/components/navigation.tsx` for current Reporting-menu grouping conventions, inspect existing report pages/components under `apps/portal/src/app/reports/` and `apps/portal/src/components/`, and look for reusable account-investigation flows such as `Mt5AccountLink` / `Mt5AccountModal` before describing new UX. Also inspect adjacent reports-api routes (for example existing MAM reconciliation or drift-correction endpoints) so the PRD explicitly reuses current backend actions instead of inventing parallel flows.
- When searching for existing GitHub issues before writing a PRD, do not rely on a single broad `gh issue list --search` query. In afx-markets, broader searches can return empty output even when adjacent work exists. Run several narrow queries around the core nouns/actions (for example feature area, domain object, underlying operation, and existing UI affordance), then open the most relevant closed/open issues to avoid duplicating nearby work and to reference the current implementation lineage in the PRD.
- When assigning issues, use `--assignee <username>` on `gh issue create`. Simon's GitHub username is "vultuk"
- When user says "assign to vultuk" they mean assign to themselves (Simon Skinner)
- Always ask about priority BEFORE writing the PRD — don't make it the last question

## Phase 5: Ongoing Monitoring (Optional)
If the user requests it, set up a cron job to monitor PRD issues for new questions:
- Check all three repos for open issues with "PRD:" in the title
- Only check issues created by "vultuk" or "vultuk-bot"
- Look for unanswered comments (last comment is from someone other than vultuk/vultuk-bot)
- Report questions to the user for confirmation before replying
- Reply with [SILENT] if no new questions
- When the user confirms an answer, use `gh issue comment` to reply on their behalf
- Typical schedule: every 15 minutes
