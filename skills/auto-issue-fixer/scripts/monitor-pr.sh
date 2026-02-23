#!/bin/bash
# monitor-pr.sh - Poll PR for reviews, comments, and review threads
#
# Usage: monitor-pr.sh <PR_NUMBER> [--timeout MINUTES] [--interval SECONDS]
#
# Monitors for all types of PR feedback including inline code review comments.
#
# Returns:
#   THREAD_RECEIVED - New inline review thread (code comment) detected
#   REVIEW_RECEIVED - New review detected (approve/request changes)
#   COMMENT_RECEIVED - New general PR comment detected
#   THREAD_UNRESOLVED - Previously resolved thread was re-opened
#   MERGED - PR was merged
#   CLOSED - PR was closed without merge
#   TIMEOUT - No activity within timeout period

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() { echo -e "${RED}Error: $1${NC}" >&2; }
warn() { echo -e "${YELLOW}Warning: $1${NC}" >&2; }
info() { echo -e "${GREEN}$1${NC}" >&2; }
status() { echo -e "${BLUE}$1${NC}" >&2; }

# Parse arguments
PR_NUMBER=""
TIMEOUT_MINUTES=30
INTERVAL_SECONDS=60
REPO_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT_MINUTES="$2"
            shift 2
            ;;
        --interval)
            INTERVAL_SECONDS="$2"
            shift 2
            ;;
        --repo|-R)
            REPO_FLAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: monitor-pr.sh <PR_NUMBER> [--timeout MINUTES] [--interval SECONDS] [--repo OWNER/REPO]"
            echo ""
            echo "Options:"
            echo "  --timeout MINUTES    Max time to wait (default: 30)"
            echo "  --interval SECONDS   Poll interval (default: 60)"
            echo "  --repo, -R           Specify repository (OWNER/REPO format)"
            echo ""
            echo "Returns:"
            echo "  THREAD_RECEIVED - New inline review thread"
            echo "  REVIEW_RECEIVED - New review detected"
            echo "  COMMENT_RECEIVED - New comment detected"
            echo "  MERGED - PR merged"
            echo "  CLOSED - PR closed"
            echo "  TIMEOUT - No activity"
            exit 0
            ;;
        *)
            if [[ -z "$PR_NUMBER" ]]; then
                PR_NUMBER="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$PR_NUMBER" ]]; then
    error "PR number required"
    echo "Usage: monitor-pr.sh <PR_NUMBER> [--timeout MINUTES]"
    exit 1
fi

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

# Get repo info for GraphQL queries
if [[ -n "$REPO_FLAG" ]]; then
    OWNER=$(echo "$REPO_FLAG" | cut -d'/' -f1)
    REPO=$(echo "$REPO_FLAG" | cut -d'/' -f2)
else
    REPO_INFO=$(gh repo view --json owner,name 2>/dev/null)
    if [[ -z "$REPO_INFO" ]]; then
        error "Not in a git repository. Use --repo OWNER/REPO to specify."
        exit 1
    fi
    OWNER=$(echo "$REPO_INFO" | jq -r '.owner.login')
    REPO=$(echo "$REPO_INFO" | jq -r '.name')
fi

# GraphQL query to get PR state, reviews, and comments
STATE_QUERY='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      state
      updatedAt
      reviews(first: 50) {
        nodes {
          id
          state
          body
          author { login }
          createdAt
        }
      }
      comments(first: 100) {
        nodes {
          id
          body
          author { login }
          createdAt
        }
      }
    }
  }
}
'

# GraphQL query to get review threads with pagination
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
          comments(first: 1) {
            nodes { id body author { login } }
          }
        }
      }
    }
  }
}
'

# Function to get current feedback state
get_feedback_state() {
    gh api graphql \
        -f query="$STATE_QUERY" \
        -f owner="$OWNER" \
        -f repo="$REPO" \
        -F pr="$PR_NUMBER" 2>/dev/null
}

get_review_threads() {
    local all_threads="[]"
    local cursor=""
    local has_next=true
    local result
    local nodes

    while [[ "$has_next" == "true" ]]; do
        if [[ -n "$cursor" ]]; then
            result=$(gh api graphql \
                -f query="$THREADS_QUERY" \
                -f owner="$OWNER" \
                -f repo="$REPO" \
                -F pr="$PR_NUMBER" \
                -f cursor="$cursor" 2>/dev/null)
        else
            result=$(gh api graphql \
                -f query="$THREADS_QUERY" \
                -f owner="$OWNER" \
                -f repo="$REPO" \
                -F pr="$PR_NUMBER" 2>/dev/null)
        fi

        if [[ -z "$result" ]]; then
            echo ""
            return 1
        fi

        nodes=$(echo "$result" | jq '.data.repository.pullRequest.reviewThreads.nodes // []')
        all_threads=$(echo "$all_threads $nodes" | jq -s 'add')

        has_next=$(echo "$result" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false')
        cursor=$(echo "$result" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // ""')
    done

    echo "$all_threads"
}

# Get initial state
info "Getting initial PR state for #$PR_NUMBER..."

INITIAL_RESULT=$(get_feedback_state)
if [[ -z "$INITIAL_RESULT" ]] || [[ "$(echo "$INITIAL_RESULT" | jq '.data.repository.pullRequest')" == "null" ]]; then
    error "Could not fetch PR #$PR_NUMBER"
    exit 1
fi

INITIAL_STATE=$(echo "$INITIAL_RESULT" | jq '.data.repository.pullRequest')
INITIAL_REVIEW_COUNT=$(echo "$INITIAL_STATE" | jq '.reviews.nodes | length')
INITIAL_COMMENT_COUNT=$(echo "$INITIAL_STATE" | jq '.comments.nodes | length')
INITIAL_UPDATED=$(echo "$INITIAL_STATE" | jq -r '.updatedAt')

# Fetch initial review threads (paged)
INITIAL_THREADS=$(get_review_threads)
if [[ -z "$INITIAL_THREADS" ]]; then
    error "Could not fetch review threads for PR #$PR_NUMBER"
    exit 1
fi

INITIAL_THREAD_COUNT=$(echo "$INITIAL_THREADS" | jq 'length')
INITIAL_UNRESOLVED=$(echo "$INITIAL_THREADS" | jq '[.[] | select(.isResolved == false)] | length')

# Track IDs to detect new items (not just count changes)
INITIAL_REVIEW_IDS=$(echo "$INITIAL_STATE" | jq '[.reviews.nodes[].id] | sort')
INITIAL_COMMENT_IDS=$(echo "$INITIAL_STATE" | jq '[.comments.nodes[].id] | sort')
INITIAL_THREAD_IDS=$(echo "$INITIAL_THREADS" | jq '[.[].id] | sort')

info "Initial state: $INITIAL_REVIEW_COUNT reviews, $INITIAL_COMMENT_COUNT comments, $INITIAL_THREAD_COUNT threads ($INITIAL_UNRESOLVED unresolved)"
info "Monitoring for $TIMEOUT_MINUTES minutes (polling every $INTERVAL_SECONDS seconds)..."

START_TIME=$(date +%s)
MAX_SECONDS=$((TIMEOUT_MINUTES * 60))

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    REMAINING=$((MAX_SECONDS - ELAPSED))

    if [[ $ELAPSED -gt $MAX_SECONDS ]]; then
        echo "TIMEOUT"
        echo '{"status": "timeout", "elapsed_minutes": '$TIMEOUT_MINUTES', "reviews": '$INITIAL_REVIEW_COUNT', "comments": '$INITIAL_COMMENT_COUNT'}'
        exit 2
    fi

    # Fetch current state using GraphQL
    CURRENT_RESULT=$(get_feedback_state)

    if [[ -z "$CURRENT_RESULT" ]]; then
        warn "Failed to fetch PR state, retrying..."
        sleep "$INTERVAL_SECONDS"
        continue
    fi

    CURRENT_STATE=$(echo "$CURRENT_RESULT" | jq '.data.repository.pullRequest')

    # Check if merged or closed
    PR_STATE=$(echo "$CURRENT_STATE" | jq -r '.state')
    if [[ "$PR_STATE" == "MERGED" ]]; then
        echo "MERGED"
        echo '{"status": "merged", "pr_number": '$PR_NUMBER'}'
        exit 0
    fi

    if [[ "$PR_STATE" == "CLOSED" ]]; then
        echo "CLOSED"
        echo '{"status": "closed", "pr_number": '$PR_NUMBER'}'
        exit 0
    fi

    # Get current counts and IDs
    CURRENT_REVIEW_COUNT=$(echo "$CURRENT_STATE" | jq '.reviews.nodes | length')
    CURRENT_COMMENT_COUNT=$(echo "$CURRENT_STATE" | jq '.comments.nodes | length')

    CURRENT_THREADS=$(get_review_threads)
    if [[ -z "$CURRENT_THREADS" ]]; then
        warn "Failed to fetch review threads, retrying..."
        sleep "$INTERVAL_SECONDS"
        continue
    fi

    CURRENT_THREAD_COUNT=$(echo "$CURRENT_THREADS" | jq 'length')
    CURRENT_UNRESOLVED=$(echo "$CURRENT_THREADS" | jq '[.[] | select(.isResolved == false)] | length')

    CURRENT_REVIEW_IDS=$(echo "$CURRENT_STATE" | jq '[.reviews.nodes[].id] | sort')
    CURRENT_COMMENT_IDS=$(echo "$CURRENT_STATE" | jq '[.comments.nodes[].id] | sort')
    CURRENT_THREAD_IDS=$(echo "$CURRENT_THREADS" | jq '[.[].id] | sort')

    # Check for new review threads (inline code comments)
    if [[ "$CURRENT_THREAD_IDS" != "$INITIAL_THREAD_IDS" ]]; then
        # Find new thread IDs
        NEW_THREAD_IDS=$(jq -n --argjson current "$CURRENT_THREAD_IDS" --argjson initial "$INITIAL_THREAD_IDS" \
            '$current - $initial')
        NEW_THREAD_COUNT=$(echo "$NEW_THREAD_IDS" | jq 'length')

        if [[ "$NEW_THREAD_COUNT" -gt 0 ]]; then
            echo "THREAD_RECEIVED"
            # Get details of new threads
            echo "$CURRENT_THREADS" | jq --argjson new_ids "$NEW_THREAD_IDS" '{
                status: "thread_received",
                new_thread_count: ($new_ids | length),
                new_threads: [.[] | select(.id as $id | $new_ids | contains([$id]))],
                total_threads: (length),
                unresolved_threads: ([.[] | select(.isResolved == false)] | length)
            }'
            exit 0
        fi
    fi

    # Check for new reviews
    if [[ "$CURRENT_REVIEW_IDS" != "$INITIAL_REVIEW_IDS" ]]; then
        NEW_REVIEW_IDS=$(jq -n --argjson current "$CURRENT_REVIEW_IDS" --argjson initial "$INITIAL_REVIEW_IDS" \
            '$current - $initial')
        NEW_REVIEW_COUNT=$(echo "$NEW_REVIEW_IDS" | jq 'length')

        if [[ "$NEW_REVIEW_COUNT" -gt 0 ]]; then
            echo "REVIEW_RECEIVED"
            echo "$CURRENT_STATE" | jq --argjson new_ids "$NEW_REVIEW_IDS" '{
                status: "review_received",
                new_review_count: ($new_ids | length),
                new_reviews: [.reviews.nodes[] | select(.id as $id | $new_ids | contains([$id]))],
                total_reviews: (.reviews.nodes | length),
                changes_requested: ([.reviews.nodes[] | select(.state == "CHANGES_REQUESTED")] | length),
                approved: ([.reviews.nodes[] | select(.state == "APPROVED")] | length)
            }'
            exit 0
        fi
    fi

    # Check for new general comments
    if [[ "$CURRENT_COMMENT_IDS" != "$INITIAL_COMMENT_IDS" ]]; then
        NEW_COMMENT_IDS=$(jq -n --argjson current "$CURRENT_COMMENT_IDS" --argjson initial "$INITIAL_COMMENT_IDS" \
            '$current - $initial')
        NEW_COMMENT_COUNT=$(echo "$NEW_COMMENT_IDS" | jq 'length')

        if [[ "$NEW_COMMENT_COUNT" -gt 0 ]]; then
            echo "COMMENT_RECEIVED"
            echo "$CURRENT_STATE" | jq --argjson new_ids "$NEW_COMMENT_IDS" '{
                status: "comment_received",
                new_comment_count: ($new_ids | length),
                new_comments: [.comments.nodes[] | select(.id as $id | $new_ids | contains([$id]))],
                total_comments: (.comments.nodes | length)
            }'
            exit 0
        fi
    fi

    # Check if unresolved count changed (threads being resolved/unresolved)
    if [[ "$CURRENT_UNRESOLVED" != "$INITIAL_UNRESOLVED" ]]; then
        if [[ "$CURRENT_UNRESOLVED" -gt "$INITIAL_UNRESOLVED" ]]; then
            echo "THREAD_UNRESOLVED"
            echo '{"status": "thread_unresolved", "previous_unresolved": '$INITIAL_UNRESOLVED', "current_unresolved": '$CURRENT_UNRESOLVED'}'
            # Update baseline to continue monitoring
            INITIAL_UNRESOLVED=$CURRENT_UNRESOLVED
        fi
        # If threads were resolved, don't exit - just update baseline and continue
        INITIAL_UNRESOLVED=$CURRENT_UNRESOLVED
    fi

    # Status update
    MINS_REMAINING=$((REMAINING / 60))
    status "Waiting... ($MINS_REMAINING min remaining)"

    sleep "$INTERVAL_SECONDS"
done
