#!/bin/bash
# fetch-pr-comments.sh - Fetch all PR comments, reviews, and review threads
#
# Usage: fetch-pr-comments.sh <PR_NUMBER> [--unresolved-only] [--json]
#
# Fetches:
# - Review comments (inline code comments)
# - PR reviews (approve/request changes/comment)
# - General PR comments
# - Review thread resolution status
#
# Tracks each comment's state for the feedback loop.

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
debug() { echo -e "${BLUE}$1${NC}" >&2; }

# Parse arguments
PR_NUMBER=""
UNRESOLVED_ONLY=false
JSON_OUTPUT=false
REPO_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --unresolved-only)
            UNRESOLVED_ONLY=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --repo|-R)
            REPO_FLAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: fetch-pr-comments.sh <PR_NUMBER> [--unresolved-only] [--json] [--repo OWNER/REPO]"
            echo ""
            echo "Options:"
            echo "  --unresolved-only  Only show unresolved review threads"
            echo "  --json             Output as JSON (for programmatic use)"
            echo "  --repo, -R         Specify repository (OWNER/REPO format)"
            echo ""
            echo "Fetches all PR feedback including:"
            echo "  - Inline code review comments"
            echo "  - PR reviews (approvals, change requests)"
            echo "  - General PR comments"
            echo "  - Review thread resolution status"
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
    echo "Usage: fetch-pr-comments.sh <PR_NUMBER> [--unresolved-only] [--json]"
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

# Get repo info
if [[ -n "$REPO_FLAG" ]]; then
    # Parse OWNER/REPO format
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

if [[ "$JSON_OUTPUT" != "true" ]]; then
    info "Fetching feedback for PR #$PR_NUMBER..."
fi

# GraphQL query to fetch PR metadata, reviews, and comments
PR_QUERY='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      title
      state
      reviews(first: 50) {
        nodes {
          id
          author {
            login
          }
          body
          state
          createdAt
          comments(first: 50) {
            nodes {
              id
              body
              path
              line
            }
          }
        }
      }
      comments(first: 100) {
        nodes {
          id
          author {
            login
          }
          body
          createdAt
        }
      }
    }
  }
}
'

# GraphQL query to fetch review threads with pagination
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
          startLine
          diffSide
          comments(first: 50) {
            nodes {
              id
              author {
                login
              }
              body
              createdAt
              updatedAt
              state
              replyTo {
                id
              }
            }
          }
        }
      }
    }
  }
}
'

# Fetch PR metadata and reviews/comments
RESULT=$(gh api graphql \
    -f query="$PR_QUERY" \
    -f owner="$OWNER" \
    -f repo="$REPO" \
    -F pr="$PR_NUMBER" 2>/dev/null)

if [[ -z "$RESULT" ]]; then
    error "Failed to fetch PR data"
    exit 1
fi

# Extract PR info
PR_TITLE=$(echo "$RESULT" | jq -r '.data.repository.pullRequest.title')
PR_STATE=$(echo "$RESULT" | jq -r '.data.repository.pullRequest.state')

REVIEWS=$(echo "$RESULT" | jq '.data.repository.pullRequest.reviews.nodes // []')
COMMENTS=$(echo "$RESULT" | jq '.data.repository.pullRequest.comments.nodes // []')

# Fetch review threads with pagination
REVIEW_THREADS="[]"
CURSOR=""
HAS_NEXT=true

while [[ "$HAS_NEXT" == "true" ]]; do
    if [[ -n "$CURSOR" ]]; then
        THREADS_RESULT=$(gh api graphql \
            -f query="$THREADS_QUERY" \
            -f owner="$OWNER" \
            -f repo="$REPO" \
            -F pr="$PR_NUMBER" \
            -f cursor="$CURSOR" 2>/dev/null)
    else
        THREADS_RESULT=$(gh api graphql \
            -f query="$THREADS_QUERY" \
            -f owner="$OWNER" \
            -f repo="$REPO" \
            -F pr="$PR_NUMBER" 2>/dev/null)
    fi

    if [[ -z "$THREADS_RESULT" ]]; then
        error "Failed to fetch review threads"
        exit 1
    fi

    THREAD_NODES=$(echo "$THREADS_RESULT" | jq '.data.repository.pullRequest.reviewThreads.nodes // []')
    REVIEW_THREADS=$(echo "$REVIEW_THREADS $THREAD_NODES" | jq -s 'add')

    HAS_NEXT=$(echo "$THREADS_RESULT" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false')
    CURSOR=$(echo "$THREADS_RESULT" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // ""')
done

# Process review threads (inline code comments)
THREAD_COUNT=$(echo "$REVIEW_THREADS" | jq 'length')
UNRESOLVED_THREADS=$(echo "$REVIEW_THREADS" | jq '[.[] | select(.isResolved == false)]')
UNRESOLVED_COUNT=$(echo "$UNRESOLVED_THREADS" | jq 'length')

# Process reviews (approve/request changes)
# CRITICAL: Get the LATEST review from each author, not all historical reviews
# GitHub shows the latest review per reviewer - we must match this behavior
REVIEW_COUNT=$(echo "$REVIEWS" | jq 'length')

# Get latest review per author (sorted by createdAt, grouped by author, take last)
LATEST_REVIEWS_PER_AUTHOR=$(echo "$REVIEWS" | jq '
  map(select(.author != null and .author.login != null)) |
  sort_by(.author.login) |
  group_by(.author.login) |
  map(sort_by(.createdAt) | last) |
  [.[] | select(. != null)]
')

# Check for CHANGES_REQUESTED in the LATEST reviews (not historical ones)
CHANGES_REQUESTED=$(echo "$LATEST_REVIEWS_PER_AUTHOR" | jq '[.[] | select(.state == "CHANGES_REQUESTED")]')
CHANGES_REQUESTED_COUNT=$(echo "$CHANGES_REQUESTED" | jq 'length')
APPROVED_COUNT=$(echo "$LATEST_REVIEWS_PER_AUTHOR" | jq '[.[] | select(.state == "APPROVED")] | length')

COMMENT_COUNT=$(echo "$COMMENTS" | jq 'length')

# Build structured output
if [[ "$JSON_OUTPUT" == "true" ]]; then
    # JSON output for programmatic use

    # Build actionable items list
    ACTIONABLE_ITEMS='[]'

    # Add unresolved review threads as actionable
    if [[ "$UNRESOLVED_COUNT" -gt 0 ]]; then
        ACTIONABLE_ITEMS=$(echo "$UNRESOLVED_THREADS" | jq '
            [.[] | {
                type: "review_thread",
                id: .id,
                path: .path,
                line: .line,
                is_resolved: .isResolved,
                is_outdated: .isOutdated,
                comments: [.comments.nodes[] | {
                    id: .id,
                    author: .author.login,
                    body: .body,
                    created_at: .createdAt,
                    is_reply: (.replyTo != null)
                }],
                requires_action: true,
                action_type: (if (.comments.nodes | length) > 0 then
                    (if (.comments.nodes[-1].body | test("(?i)(fix|change|update|remove|add|please|should|must|need)")) then
                        "code_change"
                    else
                        "response"
                    end)
                else "unknown" end)
            }]
        ')
    fi

    # Add change requests as actionable
    if [[ "$CHANGES_REQUESTED_COUNT" -gt 0 ]]; then
        CHANGE_REQUEST_ITEMS=$(echo "$CHANGES_REQUESTED" | jq '
            [.[] | {
                type: "review",
                id: .id,
                author: .author.login,
                state: .state,
                body: .body,
                created_at: .createdAt,
                requires_action: true,
                action_type: "address_review",
                inline_comments: [.comments.nodes[] | {
                    path: .path,
                    line: .line,
                    body: .body
                }]
            }]
        ')
        ACTIONABLE_ITEMS=$(echo "$ACTIONABLE_ITEMS $CHANGE_REQUEST_ITEMS" | jq -s 'add')
    fi

    # Extract actionable items from general comments (code reviews with recommendations)
    # Look for comments containing structured feedback sections
    COMMENT_ACTIONABLES=$(echo "$COMMENTS" | jq '
        [.[] |
        # Check if comment looks like a code review with recommendations
        select(.body | test("(?i)(potential issue|recommendation|fix|should|must|need to|please|blocker|critical|p[0-3])")) |
        {
            type: "comment_review",
            id: .id,
            author: .author.login,
            created_at: .createdAt,
            body: .body,
            requires_action: true,
            action_type: "review_comment",
            # Extract specific recommendations/issues from the body
            extracted_items: (
                .body |
                # Try to find numbered recommendations or issues
                [scan("(?:^|\\n)\\s*(?:\\d+\\.\\s*\\*\\*|####?\\s*\\d+\\.?\\s*\\*\\*|\\*\\*(?:Fix|Issue|Recommendation|Potential Issue)[^*]*\\*\\*)([^\\n]+(?:\\n(?!\\s*(?:\\d+\\.|####?|\\*\\*(?:Fix|Issue))).[^\\n]*)*)")]
                | if length == 0 then
                    # Fallback: look for "**Fix:**" or similar patterns
                    [scan("\\*\\*(?:Fix|Recommendation|Suggested)(?::|\\*\\*:?)\\s*([^\\n]+)")]
                  else . end
                | map(.[0] | gsub("^\\s+|\\s+$"; ""))
                | if length == 0 then null else . end
            )
        }
        | select(.extracted_items != null or (.body | test("(?i)blocker|critical|must fix|p0|p1")))]
    ')

    COMMENT_ACTIONABLE_COUNT=$(echo "$COMMENT_ACTIONABLES" | jq 'length')
    if [[ "$COMMENT_ACTIONABLE_COUNT" -gt 0 ]]; then
        ACTIONABLE_ITEMS=$(echo "$ACTIONABLE_ITEMS $COMMENT_ACTIONABLES" | jq -s 'add')
    fi

    # Final JSON structure
    jq -n \
        --arg pr_number "$PR_NUMBER" \
        --arg pr_title "$PR_TITLE" \
        --arg pr_state "$PR_STATE" \
        --argjson thread_count "$THREAD_COUNT" \
        --argjson unresolved_count "$UNRESOLVED_COUNT" \
        --argjson review_count "$REVIEW_COUNT" \
        --argjson changes_requested_count "$CHANGES_REQUESTED_COUNT" \
        --argjson approved_count "$APPROVED_COUNT" \
        --argjson comment_count "$COMMENT_COUNT" \
        --argjson actionable_comment_count "$COMMENT_ACTIONABLE_COUNT" \
        --argjson actionable_items "$ACTIONABLE_ITEMS" \
        --argjson all_threads "$REVIEW_THREADS" \
        --argjson all_reviews "$REVIEWS" \
        --argjson all_comments "$COMMENTS" \
        '{
            pr: {
                number: ($pr_number | tonumber),
                title: $pr_title,
                state: $pr_state
            },
            summary: {
                total_threads: $thread_count,
                unresolved_threads: $unresolved_count,
                total_reviews: $review_count,
                changes_requested: $changes_requested_count,
                approved: $approved_count,
                general_comments: $comment_count,
                actionable_comments: $actionable_comment_count,
                requires_action: ($unresolved_count > 0 or $changes_requested_count > 0 or $actionable_comment_count > 0)
            },
            actionable_items: $actionable_items,
            raw: {
                threads: $all_threads,
                reviews: $all_reviews,
                comments: $all_comments
            }
        }'
else
    # Human-readable output

    # Check for actionable comments (need to do this for human output too)
    ACTIONABLE_COMMENTS=$(echo "$COMMENTS" | jq '
        [.[] |
        select(.body | test("(?i)(potential issue|recommendation|fix the|should fix|must fix|blocker|critical|p[0-1])")) |
        {
            id: .id,
            author: .author.login,
            created_at: .createdAt,
            preview: (.body | split("\n")[0:3] | join(" ") | if length > 200 then .[0:200] + "..." else . end)
        }]
    ')
    ACTIONABLE_COMMENT_COUNT=$(echo "$ACTIONABLE_COMMENTS" | jq 'length')

    echo ""
    echo "========================================"
    echo "PR #$PR_NUMBER: $PR_TITLE"
    echo "State: $PR_STATE"
    echo "========================================"
    echo ""

    echo "## Summary"
    echo "- Review threads: $THREAD_COUNT total, $UNRESOLVED_COUNT unresolved"
    echo "- Reviews: $REVIEW_COUNT total ($APPROVED_COUNT approved, $CHANGES_REQUESTED_COUNT requesting changes)"
    echo "- General comments: $COMMENT_COUNT ($ACTIONABLE_COMMENT_COUNT with actionable feedback)"
    echo ""

    if [[ "$UNRESOLVED_COUNT" -gt 0 ]] || [[ "$CHANGES_REQUESTED_COUNT" -gt 0 ]] || [[ "$ACTIONABLE_COMMENT_COUNT" -gt 0 ]]; then
        echo "## Action Required"
        echo ""

        # Show unresolved threads
        if [[ "$UNRESOLVED_COUNT" -gt 0 ]]; then
            echo "### Unresolved Review Threads ($UNRESOLVED_COUNT)"
            echo ""
            echo "$UNRESOLVED_THREADS" | jq -r '
                .[] |
                "---\n" +
                "**File**: \(.path):\(.line // "N/A")\n" +
                "**Thread ID**: \(.id)\n" +
                "**Outdated**: \(.isOutdated)\n" +
                "\n**Comments**:\n" +
                (.comments.nodes | map("  - @\(.author.login): \(.body | gsub("\n"; "\n    "))") | join("\n")) +
                "\n"
            '
        fi

        # Show change requests
        if [[ "$CHANGES_REQUESTED_COUNT" -gt 0 ]]; then
            echo "### Change Requests ($CHANGES_REQUESTED_COUNT)"
            echo ""
            echo "$CHANGES_REQUESTED" | jq -r '
                .[] |
                "---\n" +
                "**From**: @\(.author.login)\n" +
                "**Date**: \(.createdAt)\n" +
                "**Review Body**:\n\(.body)\n" +
                (if (.comments.nodes | length) > 0 then
                    "\n**Inline Comments**:\n" +
                    (.comments.nodes | map("  - \(.path):\(.line): \(.body)") | join("\n"))
                else "" end) +
                "\n"
            '
        fi

        # Show actionable comments (code reviews with recommendations)
        if [[ "$ACTIONABLE_COMMENT_COUNT" -gt 0 ]]; then
            echo "### Comments with Actionable Feedback ($ACTIONABLE_COMMENT_COUNT)"
            echo ""
            echo "$ACTIONABLE_COMMENTS" | jq -r '
                .[] |
                "---\n" +
                "**From**: @\(.author)\n" +
                "**Date**: \(.created_at)\n" +
                "**Preview**: \(.preview)\n" +
                "\n(Full comment contains recommendations/issues to address)\n"
            '
            echo ""
            echo "**Note**: Read full comments above to extract specific action items."
        fi
    else
        echo "## Status: All Clear"
        echo "No unresolved threads, change requests, or actionable feedback."
        if [[ "$APPROVED_COUNT" -gt 0 ]]; then
            echo "PR has $APPROVED_COUNT approval(s)."
        fi
    fi

    # Show recent activity if not filtering
    if [[ "$UNRESOLVED_ONLY" != "true" ]] && [[ "$COMMENT_COUNT" -gt 0 ]]; then
        echo ""
        echo "### Recent General Comments"
        echo ""
        echo "$COMMENTS" | jq -r '
            .[-5:] | .[] |
            "- @\(.author.login) (\(.createdAt | split("T")[0])): \(.body | split("\n")[0])"
        '
    fi
fi
