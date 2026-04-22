---
description: Create worktree for parallel feature development with beads
---

# Create Worktree

Create an isolated git worktree for implementing a feature in parallel. This allows multiple Claude Code agents to work on different features simultaneously without conflicts.

## Initial Response

When invoked:

1. **If a beads ID or GitHub issue provided** (e.g., `/create_worktree bd-a1b2` or `/create_worktree #123`):
   - Extract the task/issue identifier
   - Look up details from beads or GitHub
   - Proceed to create the worktree

2. **If no parameters provided**:
   ```
   I'll help you create a worktree for parallel development.

   First, let me check what tasks are ready:
   ```
   Then run `bd ready` and show available tasks.

   Ask: "Which task would you like to work on? Provide a beads ID (e.g., bd-a1b2) or GitHub issue number (e.g., #123)"

## Process Steps

### Step 1: Gather Information

```bash
# If beads ID provided
bd show ${BEADS_ID} --json

# If GitHub issue provided
gh issue view ${ISSUE_NUM} --json number,title,labels
```

Determine:
- Task/issue identifier for naming
- Brief description for branch name
- Any dependencies or blockers

### Step 2: Create Worktree

```bash
# Set variables
TASK_ID="${BEADS_ID}"  # e.g., "bd-a1b2" or "issue-123"
SHORT_DESC="brief-description"  # from task title, kebab-case
BRANCH_NAME="feature/${TASK_ID}-${SHORT_DESC}"
REPO_NAME=$(basename $(git rev-parse --show-toplevel))
WORKTREE_PATH="../${REPO_NAME}-worktrees/${TASK_ID}"

# Ensure we're on latest main
git fetch origin main

# Create the worktree with a new branch based on origin/main
git worktree add -b "${BRANCH_NAME}" "${WORKTREE_PATH}" origin/main
```

### Step 3: Set Up Environment

```bash
cd "${WORKTREE_PATH}"

# Install API dependencies
cd api && uv sync && cd ..

# Install client dependencies
cd client && pnpm install && cd ..

# Set beads to no-daemon mode for worktrees
export BEADS_NO_DAEMON=1

# Verify beads works (shares database with main repo)
bd ready
```

### Step 4: Claim the Task

```bash
# Update task status in beads
bd update ${BEADS_ID} --status in_progress

# Add comment noting worktree
bd comment ${BEADS_ID} "Starting work in worktree: ${WORKTREE_PATH}"

# Sync changes
bd sync
```

### Step 5: Confirm with User

Present the summary:

```
✅ Worktree created successfully!

**Location**: ${WORKTREE_PATH}
**Branch**: ${BRANCH_NAME}
**Task**: ${BEADS_ID} - ${TASK_TITLE}

## Next Steps

1. **Open a new terminal** and navigate to the worktree:
   ```bash
   cd ${WORKTREE_PATH}
   export BEADS_NO_DAEMON=1
   ```

2. **Start Claude Code** in the worktree:
   ```bash
   claude
   ```

3. **Or launch with a plan** (for automated execution):
   ```bash
   claude "/implement_plan thoughts/shared/plans/PLAN_FILE.md"
   ```

## Useful Commands

- Check worktree status: `git worktree list`
- Remove when done: `git worktree remove ${WORKTREE_PATH}`
- Sync beads: `bd sync`
```

## Notes

### Worktree Isolation
- Each worktree has its own working directory
- They share the same `.git` directory and beads database
- Each should have its own dependencies installed (api via uv, client via pnpm)
- Use `BEADS_NO_DAEMON=1` to avoid database locking issues

### Naming Conventions
- Worktree path: `../<repo>-worktrees/<task-id>/`
- Branch name: `feature/<task-id>-<short-description>`

### After Work is Complete

```bash
# In the worktree
# 1. Commit final changes
git add .
git commit -m "feat: complete <description> - ${BEADS_ID}"

# 2. Push branch
git push -u origin ${BRANCH_NAME}

# 3. Create PR
gh pr create --fill

# 4. Close beads task
bd close ${BEADS_ID} --reason "Completed in PR #XXX"
bd sync

# 5. Return to main repo
cd /path/to/main/repo

# 6. Remove worktree (after PR is merged)
git worktree remove ${WORKTREE_PATH}
git branch -d ${BRANCH_NAME}  # Delete local branch
```

### Troubleshooting

**Beads database locked**:
```bash
export BEADS_NO_DAEMON=1
bd --no-daemon ready
```

**Worktree out of sync**:
```bash
git fetch origin
git rebase origin/main
```

**Can't delete worktree**:
```bash
# Force remove if needed
git worktree remove --force ${WORKTREE_PATH}
git worktree prune
```
