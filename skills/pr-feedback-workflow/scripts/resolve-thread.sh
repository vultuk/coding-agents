#!/bin/bash
# Resolve a PR review thread by its GraphQL ID
#
# Usage: resolve-thread.sh <THREAD_ID>
#
# Thread IDs look like: PRRT_kwDOxxxxxx
# Get them from load-pr-feedback.sh output

THREAD_ID="$1"

if [ -z "$THREAD_ID" ]; then
    echo "Usage: resolve-thread.sh <THREAD_ID>"
    echo "Example: resolve-thread.sh PRRT_kwDOABCD1234"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "Error: gh (GitHub CLI) is not installed" >&2
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Error: gh is not authenticated. Run: gh auth login" >&2
    exit 1
fi

echo "Resolving thread: $THREAD_ID"

RESULT=$(gh api graphql -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}' -f threadId="$THREAD_ID" 2>&1)

if echo "$RESULT" | grep -q '"isResolved":true'; then
    echo "✅ Thread resolved successfully"
else
    echo "❌ Failed to resolve thread:"
    echo "$RESULT"
    exit 1
fi
