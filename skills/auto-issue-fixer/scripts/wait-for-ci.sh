#!/bin/bash
# wait-for-ci.sh - Wait for CI checks to complete with timeout
#
# Usage: wait-for-ci.sh <PR_NUMBER> [--timeout MINUTES] [--interval SECONDS]
#
# Returns:
#   PASS - All checks passed
#   FAIL - One or more checks failed (outputs failure details)
#   TIMEOUT - Checks didn't complete within timeout
#   PENDING - Checks still running (only with --no-wait)

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
TIMEOUT_MINUTES=15
INTERVAL_SECONDS=30
NO_WAIT=false

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
        --no-wait)
            NO_WAIT=true
            shift
            ;;
        -h|--help)
            echo "Usage: wait-for-ci.sh <PR_NUMBER> [--timeout MINUTES] [--interval SECONDS]"
            echo ""
            echo "Options:"
            echo "  --timeout MINUTES    Max wait time (default: 15)"
            echo "  --interval SECONDS   Poll interval (default: 30)"
            echo "  --no-wait            Check once and return immediately"
            echo ""
            echo "Returns:"
            echo "  PASS - All checks passed"
            echo "  FAIL - Checks failed"
            echo "  TIMEOUT - Checks didn't complete"
            echo "  PENDING - Checks still running (--no-wait only)"
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
    echo "Usage: wait-for-ci.sh <PR_NUMBER> [--timeout MINUTES]"
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

info "Waiting for CI on PR #$PR_NUMBER (timeout: $TIMEOUT_MINUTES min)..."

START_TIME=$(date +%s)
MAX_SECONDS=$((TIMEOUT_MINUTES * 60))

check_ci_status() {
    # Get all checks for the PR
    CHECKS=$(gh pr checks "$PR_NUMBER" --json name,bucket,description,detailsUrl,startedAt,completedAt 2>/dev/null || echo "[]")

    if [[ "$CHECKS" == "[]" ]] || [[ -z "$CHECKS" ]]; then
        echo "NO_CHECKS"
        return
    fi

    # Count by status
    TOTAL=$(echo "$CHECKS" | jq 'length')
    PASSED=$(echo "$CHECKS" | jq '[.[] | select(.bucket == "pass")] | length')
    FAILED=$(echo "$CHECKS" | jq '[.[] | select(.bucket == "fail")] | length')
    PENDING=$(echo "$CHECKS" | jq '[.[] | select(.bucket == "pending")] | length')
    SKIPPED=$(echo "$CHECKS" | jq '[.[] | select(.bucket == "skipped")] | length')

    if [[ "$FAILED" -gt 0 ]]; then
        echo "FAIL"
        echo "$CHECKS" | jq '{
            status: "fail",
            summary: {
                total: '$TOTAL',
                passed: '$PASSED',
                failed: '$FAILED',
                pending: '$PENDING'
            },
            failed_checks: [.[] | select(.bucket == "fail") | {name, description, url: .detailsUrl}]
        }'
        return
    fi

    if [[ "$PENDING" -gt 0 ]]; then
        echo "PENDING"
        return
    fi

    if [[ "$PASSED" -eq "$TOTAL" ]] || [[ "$((PASSED + SKIPPED))" -eq "$TOTAL" ]]; then
        echo "PASS"
        echo "$CHECKS" | jq '{
            status: "pass",
            summary: {
                total: '$TOTAL',
                passed: '$PASSED',
                skipped: '$SKIPPED'
            },
            checks: [.[] | {name, bucket}]
        }'
        return
    fi

    echo "UNKNOWN"
}

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [[ $ELAPSED -gt $MAX_SECONDS ]]; then
        echo "TIMEOUT"
        echo '{"status": "timeout", "elapsed_minutes": '$TIMEOUT_MINUTES'}'
        exit 2
    fi

    # Check CI status
    RESULT=$(check_ci_status)
    STATUS=$(echo "$RESULT" | head -1)

    case "$STATUS" in
        "PASS")
            info "All CI checks passed!"
            echo "PASS"
            echo "$RESULT" | tail -n +2
            exit 0
            ;;
        "FAIL")
            error "CI checks failed"
            echo "FAIL"
            echo "$RESULT" | tail -n +2
            exit 1
            ;;
        "PENDING")
            if [[ "$NO_WAIT" == "true" ]]; then
                echo "PENDING"
                echo '{"status": "pending", "message": "Checks still running"}'
                exit 0
            fi
            MINS_ELAPSED=$((ELAPSED / 60))
            status "CI pending... ($MINS_ELAPSED min elapsed)"
            ;;
        "NO_CHECKS")
            warn "No CI checks found for this PR"
            if [[ "$NO_WAIT" == "true" ]]; then
                echo "PASS"
                echo '{"status": "pass", "message": "No CI checks configured"}'
                exit 0
            fi
            # Wait a bit in case checks are being registered
            if [[ $ELAPSED -gt 120 ]]; then
                echo "PASS"
                echo '{"status": "pass", "message": "No CI checks configured"}'
                exit 0
            fi
            ;;
        *)
            warn "Unknown CI status: $STATUS"
            ;;
    esac

    sleep "$INTERVAL_SECONDS"
done
