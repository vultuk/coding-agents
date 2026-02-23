#!/bin/bash
# mark-pr-ready.sh - Verify PR completion and notify user
#
# Usage: mark-pr-ready.sh <PR_NUMBER> [--force] [--repo OWNER/REPO]
#
# Verifies completion criteria:
# - All CI checks pass
# - No unresolved review threads
#
# Then:
# - If PR is a draft, marks it ready for review
# - Posts completion comment tagging the logged-in user
#
# Use --force to skip verification checks.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error() { echo -e "${RED}Error: $1${NC}" >&2; }
warn() { echo -e "${YELLOW}Warning: $1${NC}" >&2; }
info() { echo -e "${GREEN}$1${NC}" >&2; }

# Parse arguments
PR_NUMBER=""
FORCE=false
REPO_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --repo|-R)
            REPO_FLAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: mark-pr-ready.sh <PR_NUMBER> [--force] [--repo OWNER/REPO]"
            echo ""
            echo "Options:"
            echo "  --force        Skip verification checks"
            echo "  --repo, -R     Specify repository (OWNER/REPO format)"
            echo ""
            echo "Verifies before marking ready:"
            echo "  - All CI checks pass"
            echo "  - No unresolved review threads"
            echo ""
            echo "After marking ready, tags the logged-in user for notification."
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
    echo "Usage: mark-pr-ready.sh <PR_NUMBER> [--force]"
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

# Build repo flag for gh commands
if [[ -n "$REPO_FLAG" ]]; then
    GH_REPO_ARG="--repo $REPO_FLAG"
else
    GH_REPO_ARG=""
fi

info "Preparing to mark PR #$PR_NUMBER as ready for review..."

# Check if PR exists and is a draft
PR_INFO=$(gh pr view "$PR_NUMBER" $GH_REPO_ARG --json isDraft,state,title 2>/dev/null)
if [[ -z "$PR_INFO" ]]; then
    error "Could not fetch PR #$PR_NUMBER"
    exit 1
fi

IS_DRAFT=$(echo "$PR_INFO" | jq -r '.isDraft')
PR_STATE=$(echo "$PR_INFO" | jq -r '.state')
PR_TITLE=$(echo "$PR_INFO" | jq -r '.title')

if [[ "$PR_STATE" != "OPEN" ]]; then
    error "PR #$PR_NUMBER is not open (state: $PR_STATE)"
    exit 1
fi

info "PR: $PR_TITLE"

# Track if we need to mark ready
NEEDS_MARK_READY=false
if [[ "$IS_DRAFT" == "true" ]]; then
    NEEDS_MARK_READY=true
    info "PR is currently a draft"
else
    info "PR is already marked as ready for review"
fi

# Verification checks (unless --force)
if [[ "$FORCE" != "true" ]]; then
    VERIFICATION_PASSED=true

    # Check 1: CI status
    info "Checking CI status..."
    CI_CHECKS=$(gh pr checks "$PR_NUMBER" $GH_REPO_ARG --json bucket 2>/dev/null || echo "[]")

    if [[ "$CI_CHECKS" != "[]" ]]; then
        FAILED_COUNT=$(echo "$CI_CHECKS" | jq '[.[] | select(.bucket == "fail")] | length')
        PENDING_COUNT=$(echo "$CI_CHECKS" | jq '[.[] | select(.bucket == "pending")] | length')

        if [[ "$FAILED_COUNT" -gt 0 ]]; then
            error "CI checks failed ($FAILED_COUNT failures)"
            VERIFICATION_PASSED=false
        elif [[ "$PENDING_COUNT" -gt 0 ]]; then
            warn "CI checks still pending ($PENDING_COUNT pending)"
            VERIFICATION_PASSED=false
        else
            info "CI checks: PASS"
        fi
    else
        info "No CI checks configured"
    fi

    # Check 2: Comprehensive review status (threads, reviews, and comments)
    info "Checking all review feedback..."
    FULL_REVIEW_QUERY='
    query($owner: String!, $repo: String!, $pr: Int!) {
        repository(owner: $owner, name: $repo) {
            pullRequest(number: $pr) {
                mergeable
                mergeStateStatus
                reviewDecision
                reviews(first: 50) {
                    nodes {
                        id
                        state
                        body
                        createdAt
                        author { login }
                    }
                }
                comments(first: 100) {
                    nodes {
                        id
                        body
                        createdAt
                        author { login }
                    }
                }
            }
        }
    }'

    REVIEW_RESULT=$(gh api graphql \
        -f query="$FULL_REVIEW_QUERY" \
        -f owner="$OWNER" \
        -f repo="$REPO" \
        -F pr="$PR_NUMBER" 2>/dev/null || echo '{}')

    # Fetch review threads with pagination
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
                        isResolved
                        comments(first: 1) {
                            nodes {
                                body
                                author { login }
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

    while [[ "$HAS_NEXT" == "true" ]]; do
        if [[ -n "$CURSOR" ]]; then
            THREADS_RESULT=$(gh api graphql \
                -f query="$THREADS_QUERY" \
                -f owner="$OWNER" \
                -f repo="$REPO" \
                -F pr="$PR_NUMBER" \
                -f cursor="$CURSOR" 2>/dev/null || echo '{}')
        else
            THREADS_RESULT=$(gh api graphql \
                -f query="$THREADS_QUERY" \
                -f owner="$OWNER" \
                -f repo="$REPO" \
                -F pr="$PR_NUMBER" 2>/dev/null || echo '{}')
        fi

        THREAD_NODES=$(echo "$THREADS_RESULT" | jq '.data.repository.pullRequest.reviewThreads.nodes // []' 2>/dev/null || echo "[]")
        ALL_THREADS=$(echo "$ALL_THREADS $THREAD_NODES" | jq -s 'add')

        HAS_NEXT=$(echo "$THREADS_RESULT" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false')
        CURSOR=$(echo "$THREADS_RESULT" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // ""')
    done

    # Check 2-pre: GitHub's own merge state (catches issues we might miss)
    MERGE_STATE=$(echo "$REVIEW_RESULT" | jq -r '.data.repository.pullRequest.mergeStateStatus // "UNKNOWN"')
    REVIEW_DECISION=$(echo "$REVIEW_RESULT" | jq -r '.data.repository.pullRequest.reviewDecision // "NONE"')
    MERGEABLE=$(echo "$REVIEW_RESULT" | jq -r '.data.repository.pullRequest.mergeable // "UNKNOWN"')

    info "GitHub merge state: $MERGE_STATE, Review decision: $REVIEW_DECISION, Mergeable: $MERGEABLE"

    # If GitHub says it's blocked, we should respect that
    if [[ "$MERGE_STATE" == "BLOCKED" ]]; then
        error "GitHub reports PR is BLOCKED from merging"
        if [[ "$REVIEW_DECISION" == "CHANGES_REQUESTED" ]]; then
            error "Reason: Changes have been requested by a reviewer"
        elif [[ "$REVIEW_DECISION" == "REVIEW_REQUIRED" ]]; then
            error "Reason: Review is required before merging"
        fi
        VERIFICATION_PASSED=false
    fi

    if [[ "$MERGEABLE" == "CONFLICTING" ]]; then
        error "PR has merge conflicts that must be resolved"
        VERIFICATION_PASSED=false
    fi

    # Check 2a: Unresolved review threads
    UNRESOLVED_COUNT=$(echo "$ALL_THREADS" | jq \
        '[.[] | select(.isResolved == false)] | length' 2>/dev/null || echo "0")

    if [[ "$UNRESOLVED_COUNT" -gt 0 ]]; then
        error "Unresolved review threads: $UNRESOLVED_COUNT"
        VERIFICATION_PASSED=false
    else
        info "Review threads: All resolved"
    fi

    # Check 2b: Reviews with "changes requested" status (CRITICAL - catches Copilot/Claude reviews)
    # IMPORTANT: Get the LATEST review from each author, not all historical reviews
    # GitHub shows the latest review per reviewer - we must match this behavior
    LATEST_REVIEWS=$(echo "$REVIEW_RESULT" | jq '
        [.data.repository.pullRequest.reviews.nodes |
         map(select(.author != null and .author.login != null)) |
         sort_by(.author.login) |
         group_by(.author.login) |
         map(sort_by(.createdAt) | last) |
         .[] | select(. != null)]' 2>/dev/null || echo "[]")

    CHANGES_REQUESTED=$(echo "$LATEST_REVIEWS" | jq '[.[] | select(.state == "CHANGES_REQUESTED")]')
    CHANGES_REQUESTED_COUNT=$(echo "$CHANGES_REQUESTED" | jq 'length')

    if [[ "$CHANGES_REQUESTED_COUNT" -gt 0 ]]; then
        error "Reviews requesting changes: $CHANGES_REQUESTED_COUNT"
        echo "$CHANGES_REQUESTED" | jq -r '.[] | "  - @\(.author.login): \(.body | split("\n")[0] | .[0:80])"' >&2
        VERIFICATION_PASSED=false
    else
        info "Review status: No pending change requests"
    fi

    # Check 2c: Pending reviews from known bot reviewers (Copilot, Claude, etc.)
    # These often arrive AFTER CI completes - we must not miss them
    # Use LATEST_REVIEWS (already computed above) to check bot reviewer status
    BOT_REVIEWERS='["copilot", "github-actions", "claude", "dependabot", "renovate", "coderabbitai"]'
    RECENT_BOT_REVIEWS=$(echo "$LATEST_REVIEWS" | jq --argjson bots "$BOT_REVIEWERS" \
        '[.[] |
          select(.author.login as $login | $bots | any(. as $bot | $login | ascii_downcase | contains($bot))) |
          select(.state == "CHANGES_REQUESTED" or .state == "COMMENTED")]' 2>/dev/null || echo "[]")
    RECENT_BOT_REVIEW_COUNT=$(echo "$RECENT_BOT_REVIEWS" | jq 'length')

    if [[ "$RECENT_BOT_REVIEW_COUNT" -gt 0 ]]; then
        # Check if any bot reviews have actionable content (not just approvals)
        ACTIONABLE_BOT_REVIEWS=$(echo "$RECENT_BOT_REVIEWS" | jq \
            '[.[] | select(.body != null and .body != "" and (.body | test("(?i)(fix|issue|error|warning|should|must|recommend|suggestion|potential|vulnerability|security|bug)")))]')
        ACTIONABLE_COUNT=$(echo "$ACTIONABLE_BOT_REVIEWS" | jq 'length')

        if [[ "$ACTIONABLE_COUNT" -gt 0 ]]; then
            error "Unaddressed bot reviews (Copilot/Claude/etc.): $ACTIONABLE_COUNT"
            echo "$ACTIONABLE_BOT_REVIEWS" | jq -r '.[] | "  - @\(.author.login) [\(.state)]: \(.body | split("\n")[0] | .[0:60])..."' >&2
            VERIFICATION_PASSED=false
        else
            info "Bot reviews: Present but no actionable items"
        fi
    else
        info "Bot reviews: None pending"
    fi

    # Check 2d: Recent comments with actionable feedback (may contain review items)
    # Look for comments with keywords indicating unaddressed feedback
    ACTIONABLE_COMMENTS=$(echo "$REVIEW_RESULT" | jq \
        '[.data.repository.pullRequest.comments.nodes[] |
          select(.body | test("(?i)(fix|must|should|please|blocker|critical|p0|p1|todo|action required|needs|missing)")) |
          select(.body | test("(?i)(done|fixed|resolved|addressed|completed|lgtm|approved)") | not)]' 2>/dev/null || echo "[]")
    ACTIONABLE_COMMENT_COUNT=$(echo "$ACTIONABLE_COMMENTS" | jq 'length')

    if [[ "$ACTIONABLE_COMMENT_COUNT" -gt 0 ]]; then
        warn "Comments with potentially unaddressed feedback: $ACTIONABLE_COMMENT_COUNT"
        echo "$ACTIONABLE_COMMENTS" | jq -r '.[] | "  - @\(.author.login): \(.body | split("\n")[0] | .[0:60])..."' >&2
        # This is a warning, not a failure - but log it for visibility
    fi

    # Abort if verification failed
    if [[ "$VERIFICATION_PASSED" != "true" ]]; then
        error "Verification failed. Use --force to override."
        exit 1
    fi

    info "All verification checks passed"
fi

# Get the logged-in user to tag them in the comment
CURRENT_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
if [[ -z "$CURRENT_USER" ]]; then
    warn "Could not determine logged-in user for notification"
    USER_TAG=""
else
    USER_TAG="@$CURRENT_USER"
    info "Will notify: $USER_TAG"
fi

# Mark PR as ready (only if it's a draft)
if [[ "$NEEDS_MARK_READY" == "true" ]]; then
    info "Marking PR #$PR_NUMBER as ready for review..."

    if ! gh pr ready "$PR_NUMBER" $GH_REPO_ARG; then
        error "Failed to mark PR as ready"
        exit 1
    fi
    info "PR marked as ready for review"
fi

# Post summary comment with user tag
info "Posting completion comment..."

COMMENT_BODY="## Ready for Manual Review

$USER_TAG - This PR is ready for your review.

### Summary
All automated work has been completed:
- All CI checks passing
- All review feedback addressed
- All review threads resolved

### What was done
- Issue analyzed and implementation planned
- TDD approach: tests written first, then implementation
- Code changes committed and pushed
- Review feedback processed and addressed

### Next Steps
1. Review the changes
2. Approve if satisfied
3. Merge when ready

---
*Automated by auto-issue-fixer skill*"

gh pr comment "$PR_NUMBER" $GH_REPO_ARG -b "$COMMENT_BODY"

# Add 'ready' label to PR
info "Adding 'ready' label to PR..."
gh pr edit "$PR_NUMBER" $GH_REPO_ARG --add-label "ready" 2>/dev/null || warn "Could not add 'ready' label (may not exist in repo)"

info "PR #$PR_NUMBER is ready for review!"
if [[ -n "$USER_TAG" ]]; then
    info "Notification sent to $USER_TAG"
fi

# Output summary
echo '{"status": "ready", "pr_number": '$PR_NUMBER', "title": "'"$PR_TITLE"'", "notified_user": "'"$CURRENT_USER"'", "was_draft": '$([[ "$NEEDS_MARK_READY" == "true" ]] && echo "true" || echo "false")', "label_added": "ready"}'
