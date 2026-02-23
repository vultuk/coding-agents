#!/bin/bash
# Load all PR feedback: review comments, threads, and CI status
#
# Usage: load-pr-feedback.sh [PR_NUMBER]
# If PR_NUMBER not provided, detects from current branch
#
# Features:
# - Fetches PR details, conversation comments, review comments
# - Fetches review threads with resolution status
# - Fetches CI/CD status and failure logs
# - Handles pagination for large PRs
# - Includes rate limit handling

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}Warning: $1${NC}" >&2
}

info() {
    echo -e "${CYAN}$1${NC}"
}

# Check prerequisites
if ! command -v gh &> /dev/null; then
    error "GitHub CLI (gh) is not installed. Install it from https://cli.github.com/"
fi

if ! gh auth status &> /dev/null; then
    error "GitHub CLI is not authenticated. Run 'gh auth login' first."
fi

if ! command -v jq &> /dev/null; then
    error "jq is not installed. Install it before continuing."
fi

# Check rate limit before proceeding
check_rate_limit() {
    local remaining
    remaining=$(gh api rate_limit --jq '.resources.core.remaining' 2>/dev/null || echo "0")
    if [ "$remaining" -lt 10 ]; then
        local reset_time
        reset_time=$(gh api rate_limit --jq '.resources.core.reset' 2>/dev/null || echo "0")
        local reset_date
        reset_date=$(date -d "@$reset_time" 2>/dev/null || date -r "$reset_time" 2>/dev/null || echo "soon")
        error "GitHub API rate limit nearly exhausted ($remaining remaining). Resets at $reset_date"
    fi
}

check_rate_limit

# Get repo owner and name
REPO_INFO=$(gh repo view --json owner,name -q '"\(.owner.login)/\(.name)"' 2>/dev/null) || error "Not in a GitHub repository or cannot determine repo info"
OWNER=$(echo "$REPO_INFO" | cut -d'/' -f1)
REPO=$(echo "$REPO_INFO" | cut -d'/' -f2)

# Get PR number (from argument or current branch)
if [ -n "$1" ]; then
    PR_NUMBER="$1"
    # Validate PR number is numeric
    if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
        error "PR number must be numeric, got: $PR_NUMBER"
    fi
else
    PR_NUMBER=$(gh pr view --json number -q '.number' 2>/dev/null || echo "")
    if [ -z "$PR_NUMBER" ]; then
        error "No PR found for current branch. Specify PR number as argument or switch to a branch with an open PR."
    fi
fi

# Verify PR exists
if ! gh pr view "$PR_NUMBER" &>/dev/null; then
    error "PR #$PR_NUMBER not found in $OWNER/$REPO"
fi

echo "========================================"
echo "PR FEEDBACK REPORT: #$PR_NUMBER"
echo "Repository: $OWNER/$REPO"
echo "========================================"

echo ""
info "=== PR DETAILS ==="
gh pr view "$PR_NUMBER" --json title,state,author,headRefName,baseRefName,reviewDecision,mergeable \
    -q '"Title: \(.title)\nState: \(.state)\nAuthor: \(.author.login)\nBranch: \(.headRefName) -> \(.baseRefName)\nReview Decision: \(.reviewDecision // "NONE")\nMergeable: \(.mergeable // "UNKNOWN")"'

echo ""
info "=== PR CONVERSATION COMMENTS ==="
COMMENTS=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" --paginate 2>/dev/null || echo "[]")
COMMENT_COUNT=$(echo "$COMMENTS" | jq 'length')

if [ "$COMMENT_COUNT" -eq 0 ]; then
    echo "No conversation comments."
else
    echo "$COMMENTS" | jq -r '.[] | "---\nComment ID: \(.id)\nType: conversation\nAuthor: \(.user.login)\nCreated: \(.created_at)\n\nBody:\n\(.body)\n"'
    echo ""
    echo "Total conversation comments: $COMMENT_COUNT"
fi

echo ""
info "=== CODE REVIEW COMMENTS (with IDs for replies) ==="
REVIEW_COMMENTS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" --paginate 2>/dev/null || echo "[]")
REVIEW_COMMENT_COUNT=$(echo "$REVIEW_COMMENTS" | jq 'length')

if [ "$REVIEW_COMMENT_COUNT" -eq 0 ]; then
    echo "No code review comments."
else
    echo "$REVIEW_COMMENTS" | jq -r '.[] | "---\nComment ID: \(.id)\nType: review\nFile: \(.path):\(.line // .original_line // "N/A")\nAuthor: \(.user.login)\nCreated: \(.created_at)\nIn-Reply-To: \(.in_reply_to_id // "none")\n\nBody:\n\(.body)\n"'
    echo ""
    echo "Total review comments: $REVIEW_COMMENT_COUNT"
fi

echo ""
info "=== REVIEW THREADS (with IDs for resolution) ==="

# Paginate through review threads (max 100 per request)
THREADS_QUERY='
query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          comments(first: 10) {
            nodes {
              id
              author { login }
              body
              createdAt
            }
          }
        }
      }
    }
  }
}'

ALL_THREADS="[]"
CURSOR=""
HAS_NEXT=true

while [ "$HAS_NEXT" = "true" ]; do
    if [ -z "$CURSOR" ]; then
        RESULT=$(gh api graphql -f query="$THREADS_QUERY" -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" 2>/dev/null || echo '{"data":null}')
    else
        RESULT=$(gh api graphql -f query="$THREADS_QUERY" -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" -f cursor="$CURSOR" 2>/dev/null || echo '{"data":null}')
    fi
    
    if [ "$(echo "$RESULT" | jq '.data')" = "null" ]; then
        warn "Could not fetch review threads (may require additional permissions)"
        break
    fi
    
    THREADS=$(echo "$RESULT" | jq '.data.repository.pullRequest.reviewThreads.nodes')
    ALL_THREADS=$(echo "$ALL_THREADS $THREADS" | jq -s 'add')
    
    HAS_NEXT=$(echo "$RESULT" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')
    CURSOR=$(echo "$RESULT" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor')
done

THREAD_COUNT=$(echo "$ALL_THREADS" | jq 'length')
UNRESOLVED_COUNT=$(echo "$ALL_THREADS" | jq '[.[] | select(.isResolved == false)] | length')

if [ "$THREAD_COUNT" -eq 0 ]; then
    echo "No review threads."
else
    echo "$ALL_THREADS" | jq -r '.[] |
        "---\nThread ID: \(.id)\nFile: \(.path):\(.line // "N/A")\nResolved: \(.isResolved)\nOutdated: \(.isOutdated)\nComments:\n\(.comments.nodes | map("  [\(.author.login)] \(.body)") | join("\n"))\n"'
    echo ""
    echo "Total threads: $THREAD_COUNT (Unresolved: $UNRESOLVED_COUNT)"
fi

echo ""
info "=== CI/CD STATUS ==="
CI_STATUS=$(gh pr checks "$PR_NUMBER" --json name,bucket,description,detailsUrl 2>/dev/null || echo "[]")

if [ "$CI_STATUS" = "[]" ] || [ -z "$CI_STATUS" ]; then
    echo "No CI checks found."
else
    echo "$CI_STATUS" | jq -r '.[] | "\(.name): \(.bucket) - \(.description // "no description")"'
    
    FAILED_COUNT=$(echo "$CI_STATUS" | jq '[.[] | select(.bucket == "fail")] | length')
    PENDING_COUNT=$(echo "$CI_STATUS" | jq '[.[] | select(.bucket == "pending")] | length')
    PASS_COUNT=$(echo "$CI_STATUS" | jq '[.[] | select(.bucket == "pass")] | length')
    
    echo ""
    echo "Summary: $PASS_COUNT passed, $FAILED_COUNT failed, $PENDING_COUNT pending"
fi

echo ""
info "=== FAILING CI RUNS ==="
HEAD_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName -q '.headRefName' 2>/dev/null || echo "")

if [ -z "$HEAD_BRANCH" ]; then
    warn "Could not determine head branch for CI logs"
else
    FAILED_RUNS=$(gh run list --branch "$HEAD_BRANCH" --limit 10 --json databaseId,name,conclusion,event \
        --jq '[.[] | select(.conclusion == "failure")]' 2>/dev/null || echo "[]")
    
    FAILED_RUN_COUNT=$(echo "$FAILED_RUNS" | jq 'length')
    
    if [ "$FAILED_RUN_COUNT" -eq 0 ]; then
        echo "No recent failures found."
    else
        echo "Found $FAILED_RUN_COUNT failed run(s):"
        echo ""
        
        # Get details for the most recent failure
        LATEST_FAILURE=$(echo "$FAILED_RUNS" | jq -r 'first')
        RUN_ID=$(echo "$LATEST_FAILURE" | jq -r '.databaseId')
        RUN_NAME=$(echo "$LATEST_FAILURE" | jq -r '.name')
        
        echo "Latest failure: $RUN_NAME (Run ID: $RUN_ID)"
        echo ""
        info "=== FAILURE LOGS (truncated) ==="
        
        # Try to get logs, handle errors gracefully
        LOGS=$(gh run view "$RUN_ID" --log 2>/dev/null || echo "")
        
        if [ -n "$LOGS" ]; then
            echo "$LOGS" | grep -i -A 20 "error\|failed\|failure\|exception" | head -100 || echo "No error patterns found in logs"
        else
            echo "Could not retrieve logs. View online:"
            gh run view "$RUN_ID" --json url -q '.url' 2>/dev/null || echo "  gh run view $RUN_ID --web"
        fi
    fi
fi

echo ""
echo "========================================"
info "SUMMARY"
echo "========================================"
echo "Conversation comments: $COMMENT_COUNT"
echo "Review comments: $REVIEW_COMMENT_COUNT"
echo "Review threads: $THREAD_COUNT (Unresolved: $UNRESOLVED_COUNT)"
echo "CI checks: $PASS_COUNT passed, $FAILED_COUNT failed, $PENDING_COUNT pending"
echo "========================================"
echo ""
echo "END OF FEEDBACK REPORT"
echo "========================================"
