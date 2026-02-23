#!/usr/bin/env bash
# Create a GitHub issue with a code audit report or recommendation.
#
# Usage:
#   ./create_issue.sh --project "Name" --body "Content"
#   ./create_issue.sh --project "Name" --title "Custom Title" --label "label1,label2" --body "Content"
#   ./create_issue.sh --project "Name" --body "Content" --repo "owner/repo"

set -euo pipefail

PROJECT=""
TITLE=""
BODY=""
LABEL=""
REPO=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT="$2"
            shift 2
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        --body)
            BODY="$2"
            shift 2
            ;;
        --label)
            LABEL="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$PROJECT" ]]; then
    echo "Error: --project is required" >&2
    exit 1
fi

if [[ -z "$BODY" ]]; then
    echo "Error: --body is required" >&2
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

if [[ -z "$REPO" ]]; then
    if ! gh repo view &> /dev/null; then
        echo "Error: Not in a GitHub repository. Use --repo OWNER/REPO." >&2
        exit 1
    fi
fi

# Use provided title or generate default
if [[ -z "$TITLE" ]]; then
    DATE=$(date +%Y-%m-%d)
    TITLE="Code Audit Report - ${PROJECT} - ${DATE}"
fi

# Build command arguments
ARGS=(issue create --title "$TITLE" --body "$BODY")

if [[ -n "$REPO" ]]; then
    ARGS+=(--repo "$REPO")
fi

# Add labels if provided
if [[ -n "$LABEL" ]]; then
    if gh "${ARGS[@]}" --label "$LABEL" 2>/dev/null; then
        exit 0
    fi
    # If labels fail, try without (labels may not exist)
    echo "Warning: Some labels may not exist, creating without labels" >&2
fi

gh "${ARGS[@]}"
