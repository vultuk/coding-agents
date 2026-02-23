# Issue Prioritization Criteria

This document details the scoring algorithm used to prioritize GitHub issues for automated fixing.

## Combined Priority Score

**Formula**: `Combined = (Importance × 0.6) + (Speed × 0.4)`

This weights importance higher while still favoring quick wins. An issue that is both important AND fast to fix will score highest.

---

## Importance Score (0-100)

Measures how critical the issue is to address.

### Label Score (30% weight)

Based on issue labels. Takes the highest matching score:

| Label Pattern | Score | Rationale |
|--------------|-------|-----------|
| `security`, `vulnerability` | 95 | Security issues are critical |
| `priority-critical`, `P0`, `critical` | 90 | Explicitly marked critical |
| `priority-high`, `P1`, `high-priority` | 80 | High priority |
| `bug`, `defect` | 70 | Bugs affect users |
| `priority-medium`, `P2` | 60 | Medium priority |
| `enhancement`, `feature` | 40 | Nice to have |
| `priority-low`, `P3`, `low-priority` | 30 | Low priority |
| `documentation`, `docs` | 20 | Documentation only |
| No labels | 50 | Default middle score |

### Age Score (20% weight)

Older issues get higher priority:

| Age | Score | Rationale |
|-----|-------|-----------|
| > 90 days | 90 | Very stale, needs attention |
| > 30 days | 80 | Getting old |
| > 14 days | 60 | Moderate age |
| > 7 days | 40 | Recent but not new |
| < 7 days | 20 | Very recent |

### Author Score (15% weight)

Based on author's relationship to the project:

| Author Type | Score | Detection |
|-------------|-------|-----------|
| Maintainer | 80 | Has WRITE access or more |
| Contributor | 60 | Has merged PRs |
| External | 40 | First-time or occasional |

**Note**: If author detection fails, defaults to 50.

### Assignee Score (10% weight)

Unassigned issues score higher (they need help):

| Assignee Status | Score | Rationale |
|-----------------|-------|-----------|
| Assigned to bot | 80 | Bot may need help |
| Unassigned | 70 | No one working on it |
| Assigned to human | 20 | Someone is handling it |

### Comment Activity Score (15% weight)

More comments indicate community interest:

| Comments | Score | Rationale |
|----------|-------|-----------|
| > 10 | 80 | High engagement |
| 5-10 | 70 | Good discussion |
| 3-5 | 50 | Some interest |
| 1-2 | 30 | Minimal discussion |
| 0 | 20 | No engagement |

### Milestone Score (10% weight)

Issues in active milestones get priority:

| Milestone | Score | Rationale |
|-----------|-------|-----------|
| Current/active milestone | 90 | Release pressure |
| Next milestone | 60 | Coming up |
| Future milestone | 40 | Planned |
| No milestone | 30 | Unscheduled |

---

## Speed Score (0-100)

Estimates how quickly the issue can be resolved.

### Description Length Score (20% weight)

Shorter descriptions often indicate simpler issues:

| Character Count | Score | Rationale |
|-----------------|-------|-----------|
| < 200 | 80 | Simple, clear issue |
| 200-500 | 60 | Moderate detail |
| 500-1000 | 40 | Complex description |
| > 1000 | 20 | Very detailed/complex |

### Files Affected Score (30% weight)

Estimated from codebase search (via subagent):

| Files | Score | Rationale |
|-------|-------|-----------|
| 1 file | 90 | Minimal scope |
| 2-3 files | 70 | Small scope |
| 4-5 files | 40 | Medium scope |
| > 5 files | 20 | Large scope |

**Detection**: Subagent searches codebase for keywords from issue title/body.

### Complexity Keywords Score (25% weight)

Keywords in title/body indicate complexity:

| Keywords | Score | Examples |
|----------|-------|----------|
| Simple fixes | 80 | "typo", "spelling", "rename", "update version" |
| Small changes | 70 | "fix", "patch", "correct", "adjust" |
| Additions | 60 | "add", "include", "support", "enable" |
| Changes | 50 | "change", "modify", "improve" |
| Refactoring | 30 | "refactor", "restructure", "reorganize" |
| Major work | 10 | "rewrite", "redesign", "architecture", "migrate" |

### Reproduction Steps Score (15% weight)

Clear reproduction steps make bugs easier to fix:

| Has Reproduction | Score | Detection |
|------------------|-------|-----------|
| Yes - clear steps | 80 | Contains numbered steps or "Steps to reproduce" |
| Partial | 50 | Some context but incomplete |
| No | 30 | No reproduction info |

**Detection patterns**:
- "steps to reproduce"
- "how to reproduce"
- "reproduction steps"
- Numbered list (1. 2. 3.)
- "Expected:" and "Actual:" sections

### Suggested Fix Score (10% weight)

If the issue includes a solution hint:

| Has Suggested Fix | Score | Detection |
|-------------------|-------|-----------|
| Yes - code snippet | 90 | Contains code blocks with fix |
| Yes - description | 70 | "Solution:", "Fix:", "Could be fixed by" |
| Partial hint | 50 | References specific file/function |
| No | 40 | No solution suggested |

---

## Score Calculation Example

**Issue #123**: "Fix null pointer in user service"
- Labels: `bug`, `priority-high`
- Age: 15 days
- Author: Contributor
- Assignees: None
- Comments: 4
- Milestone: v2.1 (current)
- Description: 350 characters
- Keywords: "fix", "null"
- Has repro: Yes
- Has fix hint: Mentions specific file

### Importance Calculation

| Factor | Raw Score | Weight | Weighted |
|--------|-----------|--------|----------|
| Labels (priority-high) | 80 | 0.30 | 24.0 |
| Age (15 days) | 60 | 0.20 | 12.0 |
| Author (contributor) | 60 | 0.15 | 9.0 |
| Assignees (none) | 70 | 0.10 | 7.0 |
| Comments (4) | 50 | 0.15 | 7.5 |
| Milestone (current) | 90 | 0.10 | 9.0 |
| **Total** | | | **68.5** |

### Speed Calculation

| Factor | Raw Score | Weight | Weighted |
|--------|-----------|--------|----------|
| Description (350 chars) | 60 | 0.20 | 12.0 |
| Files (~2) | 70 | 0.30 | 21.0 |
| Keywords ("fix") | 70 | 0.25 | 17.5 |
| Repro (yes) | 80 | 0.15 | 12.0 |
| Fix hint (partial) | 50 | 0.10 | 5.0 |
| **Total** | | | **67.5** |

### Combined Score

```
Combined = (68.5 × 0.6) + (67.5 × 0.4)
         = 41.1 + 27.0
         = 68.1
```

**Result**: Issue #123 scores **68.1/100**

---

## Automatic Exclusions

Issues are excluded from consideration if:

| Condition | Reason | Detection Method |
|-----------|--------|------------------|
| **Has open linked PR** | Already being worked on | GitHub Timeline API (`CROSS_REFERENCED_EVENT`, `CONNECTED_EVENT`) |
| Assigned to human | Someone is handling it | `assignees` field |
| Label: `auto-fixing` | Currently being processed by skill | Label check |
| Label: `auto-fixed` | Already completed by skill | Label check |
| Label: `wontfix` | Intentionally not fixing | Label check |
| Label: `duplicate` | Duplicate of another issue | Label check |
| Label: `invalid` | Not a valid issue | Label check |
| Label: `blocked` | Blocked by dependency | Label check |
| Label: `on-hold` | Intentionally paused | Label check |

### Linked PR Detection

The script uses GitHub's GraphQL Timeline API to reliably detect linked PRs:

```graphql
timelineItems(itemTypes: [CROSS_REFERENCED_EVENT, CONNECTED_EVENT]) {
  nodes {
    ... on CrossReferencedEvent {
      source { ... on PullRequest { number, state } }
    }
    ... on ConnectedEvent {
      subject { ... on PullRequest { number, state } }
    }
  }
}
```

- **CROSS_REFERENCED_EVENT**: PR body contains "Closes #N", "Fixes #N", etc.
- **CONNECTED_EVENT**: PR explicitly linked via GitHub UI
- Only **OPEN** PRs block the issue (merged/closed PRs don't count)

This prevents the skill from creating duplicate PRs for issues already being worked on.

---

## Customization

### Environment Variables

Override default weights:

```bash
export IMPORTANCE_WEIGHT=0.7  # Default: 0.6
export SPEED_WEIGHT=0.3       # Default: 0.4
```

### Label Mappings

Add custom label scores by defining in your repo's `.github/issue-priority.json`:

```json
{
  "labels": {
    "customer-reported": 85,
    "quick-fix": 90,
    "needs-investigation": 30
  }
}
```

---

## Tuning Recommendations

### For Bug-Heavy Repos

Increase importance weight:
- `IMPORTANCE_WEIGHT=0.7`
- `SPEED_WEIGHT=0.3`

### For Rapid Iteration

Favor quick wins:
- `IMPORTANCE_WEIGHT=0.4`
- `SPEED_WEIGHT=0.6`

### For Security-Focused

Add custom label scores:
```json
{
  "labels": {
    "security": 100,
    "vulnerability": 100,
    "CVE": 100
  }
}
```

---

*Reference document for auto-issue-fixer skill*
