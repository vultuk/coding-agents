#!/bin/bash
# list-all-issues.sh - Fetch all open issues with metadata for prioritization
#
# Usage: list-all-issues.sh [--labels LABELS] [--exclude LABELS] [--limit N]
#
# Outputs JSON with issue metadata needed for priority scoring.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() { echo -e "${RED}Error: $1${NC}" >&2; }
warn() { echo -e "${YELLOW}Warning: $1${NC}" >&2; }
info() { echo -e "${GREEN}$1${NC}" >&2; }

# Parse arguments
LABELS=""
EXCLUDE=""
LIMIT=50

while [[ $# -gt 0 ]]; do
    case $1 in
        --labels)
            LABELS="$2"
            shift 2
            ;;
        --exclude)
            EXCLUDE="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: list-all-issues.sh [--labels LABELS] [--exclude LABELS] [--limit N]"
            echo ""
            echo "Options:"
            echo "  --labels LABELS    Filter to issues with these labels (comma-separated)"
            echo "  --exclude LABELS   Exclude issues with these labels (comma-separated)"
            echo "  --limit N          Maximum issues to fetch (default: 50)"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate prerequisites
if ! command -v gh &> /dev/null; then
    error "gh (GitHub CLI) is not installed"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    error "gh is not authenticated. Run: gh auth login"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    error "jq is not installed"
    exit 1
fi

# Check we're in a git repo with GitHub remote
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    error "Not in a git repository"
    exit 1
fi

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$REMOTE_URL" ]] || [[ ! "$REMOTE_URL" =~ github ]]; then
    error "No GitHub remote found"
    exit 1
fi

# Build label filter arguments
LABEL_ARGS=""
if [[ -n "$LABELS" ]]; then
    # Convert comma-separated to multiple --label args
    IFS=',' read -ra LABEL_ARRAY <<< "$LABELS"
    for label in "${LABEL_ARRAY[@]}"; do
        LABEL_ARGS="$LABEL_ARGS --label \"$(echo "$label" | xargs)\""
    done
fi

info "Fetching open issues..."

# Fetch issues with all required metadata
# Using JSON output for reliable parsing
ISSUES_JSON=$(gh issue list \
    --state open \
    --limit "$LIMIT" \
    --json number,title,body,labels,author,assignees,createdAt,updatedAt,comments,milestone \
    $LABEL_ARGS 2>/dev/null || echo "[]")

# Check if we got any issues
ISSUE_COUNT=$(echo "$ISSUES_JSON" | jq 'length')

if [[ "$ISSUE_COUNT" == "0" ]]; then
    warn "No open issues found"
    echo '{"issues": [], "metadata": {"total": 0, "filtered": 0}}'
    exit 0
fi

info "Found $ISSUE_COUNT open issues"

# Filter out excluded labels if specified
if [[ -n "$EXCLUDE" ]]; then
    IFS=',' read -ra EXCLUDE_ARRAY <<< "$EXCLUDE"
    for exclude_label in "${EXCLUDE_ARRAY[@]}"; do
        exclude_label=$(echo "$exclude_label" | xargs)  # Trim whitespace
        ISSUES_JSON=$(echo "$ISSUES_JSON" | jq --arg label "$exclude_label" \
            '[.[] | select(.labels | map(.name) | index($label) | not)]')
    done
    FILTERED_COUNT=$(echo "$ISSUES_JSON" | jq 'length')
    info "After exclusions: $FILTERED_COUNT issues"
fi

# Always exclude issues with auto-fixer labels (prevent duplicate processing)
DEFAULT_EXCLUDE_LABELS=("auto-fixing" "auto-fixed" "wontfix" "duplicate" "blocked" "on-hold")
for exclude_label in "${DEFAULT_EXCLUDE_LABELS[@]}"; do
    ISSUES_JSON=$(echo "$ISSUES_JSON" | jq --arg label "$exclude_label" \
        '[.[] | select(.labels | map(.name) | index($label) | not)]')
done
FILTERED_COUNT=$(echo "$ISSUES_JSON" | jq 'length')
info "After default exclusions: $FILTERED_COUNT issues"

# Check for issues with linked PRs (already being worked on)
info "Checking for linked PRs..."

# Transform to our output format with additional metadata
OUTPUT=$(echo "$ISSUES_JSON" | jq '
{
  "issues": [
    .[] | {
      "number": .number,
      "title": .title,
      "body": (.body // "" | .[0:2000]),
      "labels": [.labels[].name],
      "author": .author.login,
      "assignees": [.assignees[].login],
      "created_at": .createdAt,
      "updated_at": .updatedAt,
      "comment_count": (
        (.comments // 0) as $c |
        if ($c | type) == "array" then ($c | length)
        elif ($c | type) == "number" then $c
        else 0 end
      ),
      "milestone": (.milestone.title // null),
      "body_length": (.body // "" | length),
      "has_code_blocks": ((.body // "") | test("```")),
      "has_reproduction": ((.body // "") | test("(?i)(steps to reproduce|reproduction|repro steps|how to reproduce)"))
    }
  ],
  "metadata": {
    "total": length,
    "fetched_at": (now | todate)
  }
}')

# For each issue, check if there's already a linked PR using GraphQL timeline API
# This is more reliable than search-based detection
FINAL_ISSUES=$(echo "$OUTPUT" | jq '.issues')
ENRICHED_ISSUES="[]"

# Get repo owner and name
REPO_INFO=$(gh repo view --json owner,name 2>/dev/null)
OWNER=$(echo "$REPO_INFO" | jq -r '.owner.login')
REPO=$(echo "$REPO_INFO" | jq -r '.name')

for issue_num in $(echo "$FINAL_ISSUES" | jq -r '.[].number'); do
    # Check for linked PRs via timeline (cross-references and connected events)
    LINKED_PR_RESULT=$(gh api graphql -f query='
    query($owner: String!, $repo: String!, $num: Int!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $num) {
          timelineItems(first: 20, itemTypes: [CROSS_REFERENCED_EVENT, CONNECTED_EVENT]) {
            nodes {
              ... on CrossReferencedEvent {
                source {
                  ... on PullRequest {
                    number
                    state
                  }
                }
              }
              ... on ConnectedEvent {
                subject {
                  ... on PullRequest {
                    number
                    state
                  }
                }
              }
            }
          }
        }
      }
    }' -f owner="$OWNER" -f repo="$REPO" -F num="$issue_num" 2>/dev/null || echo '{}')

    # Count open PRs linked to this issue
    OPEN_PR_COUNT=$(echo "$LINKED_PR_RESULT" | jq '
        [.data.repository.issue.timelineItems.nodes[] |
         (.source // .subject) |
         select(. != null and .state == "OPEN")] | length
    ' 2>/dev/null || echo "0")

    # Get the PR numbers for reference
    LINKED_PR_NUMBERS=$(echo "$LINKED_PR_RESULT" | jq '
        [.data.repository.issue.timelineItems.nodes[] |
         (.source // .subject) |
         select(. != null and .state == "OPEN") |
         .number] | unique
    ' 2>/dev/null || echo "[]")

    # Add has_linked_pr field to this issue
    ISSUE_DATA=$(echo "$FINAL_ISSUES" | jq \
        --argjson num "$issue_num" \
        --argjson linked "$OPEN_PR_COUNT" \
        --argjson pr_nums "$LINKED_PR_NUMBERS" \
        '[.[] | select(.number == $num) | . + {
            "has_linked_pr": ($linked > 0),
            "linked_pr_count": $linked,
            "linked_prs": $pr_nums
        }][0]')

    ENRICHED_ISSUES=$(echo "$ENRICHED_ISSUES" | jq --argjson issue "$ISSUE_DATA" '. + [$issue]')
done

# Build final output
FINAL_OUTPUT=$(echo "$OUTPUT" | jq --argjson issues "$ENRICHED_ISSUES" '.issues = $issues')

# Output the JSON
echo "$FINAL_OUTPUT"

info "Issue data retrieved successfully"
