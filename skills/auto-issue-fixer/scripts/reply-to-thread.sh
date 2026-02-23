#!/bin/bash
# reply-to-thread.sh - Reply to a PR review thread and optionally resolve it
#
# Usage: reply-to-thread.sh <THREAD_ID> <REPLY_TEXT> [--resolve] [--repo OWNER/REPO]
#
# Arguments:
#   THREAD_ID    The GraphQL thread ID (e.g., PRRT_kwDOxxxxxx)
#   REPLY_TEXT   The reply message to post
#
# Options:
#   --resolve    Also resolve the thread after replying
#   --repo       Specify repository (OWNER/REPO format)
#
# Examples:
#   reply-to-thread.sh PRRT_kwDO123 "Done - fixed the null check"
#   reply-to-thread.sh PRRT_kwDO123 "Fixed in latest commit" --resolve
#   reply-to-thread.sh PRRT_kwDO123 "This is out of scope" --resolve --repo owner/repo

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error() { echo -e "${RED}Error: $1${NC}" >&2; }
success() { echo -e "${GREEN}$1${NC}" >&2; }
warn() { echo -e "${YELLOW}$1${NC}" >&2; }

# Parse arguments
THREAD_ID=""
REPLY_TEXT=""
RESOLVE_AFTER=false
REPO_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --resolve)
            RESOLVE_AFTER=true
            shift
            ;;
        --repo|-R)
            REPO_FLAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: reply-to-thread.sh <THREAD_ID> <REPLY_TEXT> [--resolve] [--repo OWNER/REPO]"
            echo ""
            echo "Arguments:"
            echo "  THREAD_ID    The GraphQL thread ID (e.g., PRRT_kwDOxxxxxx)"
            echo "  REPLY_TEXT   The reply message to post"
            echo ""
            echo "Options:"
            echo "  --resolve    Also resolve the thread after replying"
            echo "  --repo       Specify repository (OWNER/REPO format)"
            echo ""
            echo "Examples:"
            echo "  reply-to-thread.sh PRRT_kwDO123 \"Done - fixed the null check\""
            echo "  reply-to-thread.sh PRRT_kwDO123 \"Fixed in latest commit\" --resolve"
            exit 0
            ;;
        *)
            if [[ -z "$THREAD_ID" ]]; then
                THREAD_ID="$1"
            elif [[ -z "$REPLY_TEXT" ]]; then
                REPLY_TEXT="$1"
            fi
            shift
            ;;
    esac
done

# Validate inputs
if [[ -z "$THREAD_ID" ]]; then
    error "Thread ID required"
    echo "Usage: reply-to-thread.sh <THREAD_ID> <REPLY_TEXT> [--resolve]"
    exit 1
fi

if [[ -z "$REPLY_TEXT" ]]; then
    error "Reply text required"
    echo "Usage: reply-to-thread.sh <THREAD_ID> <REPLY_TEXT> [--resolve]"
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

# Post reply to thread
echo "Replying to thread: $THREAD_ID" >&2

REPLY_RESULT=$(gh api graphql -f query='
mutation($body: String!, $threadId: ID!) {
  addPullRequestReviewThreadReply(input: {
    body: $body,
    pullRequestReviewThreadId: $threadId
  }) {
    comment {
      id
      body
      author {
        login
      }
      createdAt
    }
  }
}' -f body="$REPLY_TEXT" -f threadId="$THREAD_ID" 2>&1)

# Check if reply succeeded
if echo "$REPLY_RESULT" | grep -q '"id":'; then
    COMMENT_ID=$(echo "$REPLY_RESULT" | jq -r '.data.addPullRequestReviewThreadReply.comment.id')
    success "Reply posted successfully (comment ID: $COMMENT_ID)"
else
    error "Failed to post reply:"
    echo "$REPLY_RESULT" >&2
    exit 1
fi

# Resolve thread if requested
if [[ "$RESOLVE_AFTER" == "true" ]]; then
    echo "Resolving thread..." >&2

    RESOLVE_RESULT=$(gh api graphql -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}' -f threadId="$THREAD_ID" 2>&1)

    if echo "$RESOLVE_RESULT" | grep -q '"isResolved":true'; then
        success "Thread resolved successfully"
    else
        warn "Reply posted but failed to resolve thread:"
        echo "$RESOLVE_RESULT" >&2
        # Don't exit with error - reply was successful
    fi
fi

# Output JSON result
echo "$REPLY_RESULT" | jq '{
    success: true,
    comment_id: .data.addPullRequestReviewThreadReply.comment.id,
    thread_id: "'"$THREAD_ID"'",
    resolved: '$([[ "$RESOLVE_AFTER" == "true" ]] && echo "true" || echo "false")'
}'
