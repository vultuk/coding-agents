#!/bin/bash
# Clean up after an issue is complete
#
# Usage: cleanup-issue.sh <issue-number> [--force]
#
# Options:
#   --force    Skip confirmation prompts
#
# This script:
# 1. Finds the PR for the issue branch
# 2. Merges it if approved but not yet merged (with confirmation)
# 3. Removes the worktree
# 4. Deletes the local branch
# 5. Updates main
# 6. Prunes stale worktree references

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

success() {
    echo -e "${GREEN}$1${NC}"
}

info() {
    echo -e "${CYAN}$1${NC}"
}

# Parse arguments
ISSUE_NUMBER=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            if [ -z "$ISSUE_NUMBER" ]; then
                ISSUE_NUMBER="$1"
            else
                error "Unexpected argument: $1"
            fi
            shift
            ;;
    esac
done

if [ -z "$ISSUE_NUMBER" ]; then
    echo "Usage: cleanup-issue.sh <issue-number> [--force]"
    echo ""
    echo "Options:"
    echo "  --force, -f    Skip confirmation prompts"
    exit 1
fi

# Validate issue number is numeric
if ! [[ "$ISSUE_NUMBER" =~ ^[0-9]+$ ]]; then
    error "Issue number must be numeric, got: $ISSUE_NUMBER"
fi

# Check prerequisites
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    error "Not in a git repository"
fi

if ! command -v gh &> /dev/null; then
    error "GitHub CLI (gh) is not installed"
fi

if ! gh auth status &> /dev/null; then
    error "GitHub CLI is not authenticated. Run 'gh auth login' first."
fi

# Confirmation prompt function
confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    local prompt="$1"
    local response
    
    echo -e -n "${YELLOW}$prompt [y/N]: ${NC}"
    read -r response
    
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

REPO_ROOT=$(git rev-parse --show-toplevel)
BRANCH_NAME="issue-$ISSUE_NUMBER"
WORKTREE_PATH="$REPO_ROOT/.worktrees/issue-$ISSUE_NUMBER"

echo "=== Cleaning up issue #$ISSUE_NUMBER ==="
echo "Branch: $BRANCH_NAME"
echo "Worktree: $WORKTREE_PATH"
echo ""

# Step 1: Check if we're in the worktree (need to leave first)
CURRENT_DIR=$(pwd)
if [[ "$CURRENT_DIR" == "$WORKTREE_PATH"* ]]; then
    info "Currently in worktree, moving to repo root..."
    cd "$REPO_ROOT"
fi

# Determine the default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
if ! git show-ref --verify --quiet "refs/heads/$DEFAULT_BRANCH"; then
    if git show-ref --verify --quiet "refs/heads/master"; then
        DEFAULT_BRANCH="master"
    fi
fi

# Step 2: Find and check PR status
info "=== Checking PR status ==="
PR_INFO=$(gh pr list --head "$BRANCH_NAME" --json number,state,mergeStateStatus,reviewDecision --jq '.[0]' 2>/dev/null || echo "")

if [ -z "$PR_INFO" ] || [ "$PR_INFO" == "null" ]; then
    echo "No open PR found for branch $BRANCH_NAME"
    echo "Checking for merged PR..."
    
    MERGED_PR=$(gh pr list --head "$BRANCH_NAME" --state merged --json number --jq '.[0].number' 2>/dev/null || echo "")
    
    if [ -n "$MERGED_PR" ] && [ "$MERGED_PR" != "null" ]; then
        success "PR #$MERGED_PR was already merged."
    else
        warn "No PR found. Proceeding with local cleanup only."
        
        if ! confirm "Continue with local cleanup (remove worktree and branch)?"; then
            echo "Aborted."
            exit 0
        fi
    fi
else
    PR_NUMBER=$(echo "$PR_INFO" | jq -r '.number')
    PR_STATE=$(echo "$PR_INFO" | jq -r '.state')
    MERGE_STATUS=$(echo "$PR_INFO" | jq -r '.mergeStateStatus')
    REVIEW_DECISION=$(echo "$PR_INFO" | jq -r '.reviewDecision')
    
    echo "Found PR #$PR_NUMBER"
    echo "State: $PR_STATE"
    echo "Merge status: $MERGE_STATUS"
    echo "Review decision: $REVIEW_DECISION"
    
    if [ "$PR_STATE" == "OPEN" ]; then
        if [ "$MERGE_STATUS" == "CLEAN" ]; then
            echo ""
            
            if [ "$REVIEW_DECISION" != "APPROVED" ]; then
                warn "PR has not been approved (decision: $REVIEW_DECISION)"
            fi
            
            if confirm "Merge PR #$PR_NUMBER?"; then
                info "=== Merging PR #$PR_NUMBER ==="
                gh pr merge "$PR_NUMBER" --merge --delete-branch --yes
                success "PR merged successfully!"
            else
                echo "Skipping merge."
                
                if ! confirm "Continue with cleanup anyway (will not delete remote branch)?"; then
                    echo "Aborted."
                    exit 0
                fi
            fi
        else
            echo ""
            warn "PR is not ready to merge (status: $MERGE_STATUS)"
            
            if [ "$MERGE_STATUS" == "BLOCKED" ]; then
                echo "The PR may be blocked by:"
                echo "  - Required reviews not met"
                echo "  - Required status checks not passed"
                echo "  - Branch protection rules"
            elif [ "$MERGE_STATUS" == "BEHIND" ]; then
                echo "The branch is behind the base branch. Consider updating it first."
            elif [ "$MERGE_STATUS" == "DIRTY" ]; then
                echo "There are merge conflicts that need to be resolved."
            fi
            
            if ! confirm "Continue with local cleanup only (PR will remain open)?"; then
                echo "Aborted."
                exit 0
            fi
        fi
    fi
fi

# Step 3: Remove worktree
echo ""
info "=== Removing worktree ==="
if [ -d "$WORKTREE_PATH" ]; then
    git worktree remove "$WORKTREE_PATH" --force
    success "Worktree removed."
else
    echo "Worktree not found at $WORKTREE_PATH (already removed?)"
fi

# Step 4: Delete local branch
echo ""
info "=== Cleaning up local branch ==="
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [ "$CURRENT_BRANCH" = "$BRANCH_NAME" ]; then
    echo "Currently on $BRANCH_NAME, switching to $DEFAULT_BRANCH first..."
    git checkout "$DEFAULT_BRANCH"
fi

if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    git branch -D "$BRANCH_NAME" 2>/dev/null && success "Local branch deleted." || warn "Could not delete local branch"
else
    echo "Local branch $BRANCH_NAME not found (already deleted?)"
fi

# Step 5: Update default branch
echo ""
info "=== Updating $DEFAULT_BRANCH ==="
git checkout "$DEFAULT_BRANCH" 2>/dev/null || true

if git pull --ff-only origin "$DEFAULT_BRANCH" 2>/dev/null; then
    success "$DEFAULT_BRANCH is up to date."
else
    warn "Could not fast-forward $DEFAULT_BRANCH. You may need to update it manually."
fi

# Step 6: Prune worktree references
echo ""
info "=== Pruning stale worktree references ==="
git worktree prune
success "Done."

echo ""
success "=== Cleanup complete ==="
echo ""
echo "Current worktrees:"
git worktree list
echo ""
echo "Ready for next task. If using Claude Code, run /new to start fresh."
