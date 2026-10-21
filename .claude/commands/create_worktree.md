---
description: Create worktree for parallel feature development on a Jira ticket
---

# Create Worktree

Create an isolated git worktree for implementing a feature in parallel. This allows multiple Claude Code agents to work on different features simultaneously without conflicts.

## Initial Response

When invoked:

1. **If a Jira key or GitHub issue provided** (e.g., `/create_worktree SCRUM-78` or `/create_worktree #123`):
   - Extract the task/issue identifier
   - Look up details in Jira or GitHub
   - Proceed to create the worktree

2. **If no parameters provided**:
   ```
   I'll help you create a worktree for parallel development.

   First, let me check what tasks are ready:
   ```
   Then search Jira with the Atlassian MCP `searchJiraIssuesUsingJql` tool, for example
   `project = SCRUM AND status = "To Do" AND issuetype = Task ORDER BY priority DESC, key ASC`,
   and show the tickets whose blockers are Done.

   Ask: "Which task would you like to work on? Provide a Jira key (e.g., SCRUM-78) or GitHub issue number (e.g., #123)"

## Process Steps

### Step 1: Gather Information

- Jira key: fetch the ticket with the Atlassian MCP `getJiraIssue` tool, including `issuelinks`.
- GitHub issue: `gh issue view ${ISSUE_NUM} --json number,title,labels`

Determine:
- Task/issue identifier for naming
- Brief description for branch name
- Any blockers (Blocks links whose blocking ticket is not Done)

### Step 2: Create Worktree

```bash
# Set variables
TASK_ID="SCRUM-78"  # the Jira key, or "issue-123"
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
cd engineering/api && uv sync && cd ../..

# Install client dependencies
cd engineering/client && pnpm install && cd ../..
```

### Step 4: Claim the Task

With the Atlassian MCP tools:

- `transitionJiraIssue` to **In Progress** (look the transition ID up with `getTransitionsForJiraIssue`).
- Assign the ticket to the user if it is unassigned (`editJiraIssue`, after confirming with them).

### Step 5: Confirm with User

Present the summary:

```
✅ Worktree created successfully!

**Location**: ${WORKTREE_PATH}
**Branch**: ${BRANCH_NAME}
**Task**: ${TASK_ID} - ${TASK_TITLE}

## Next Steps

1. **Open a new terminal** and navigate to the worktree:
   ```bash
   cd ${WORKTREE_PATH}
   ```

2. **Start Claude Code** in the worktree:
   ```bash
   claude
   ```

3. **Or launch with a plan** (for automated execution):
   ```bash
   claude "/implement_plan engineering/thoughts/shared/plans/PLAN_FILE.md"
   ```

## Useful Commands

- Check worktree status: `git worktree list`
- Remove when done: `git worktree remove ${WORKTREE_PATH}`
```

## Notes

### Worktree Isolation
- Each worktree has its own working directory
- They share the same `.git` directory
- Each should have its own dependencies installed (api via uv, client via pnpm)

### Naming Conventions
- Worktree path: `../<repo>-worktrees/<task-id>/`
- Branch name: `feature/<task-id>-<short-description>`

### After Work is Complete

```bash
# In the worktree
# 1. Commit final changes (use the /commit skill)

# 2. Push branch
git push -u origin ${BRANCH_NAME}

# 3. Create PR (use /describe_pr for the body)
gh pr create --base main --body-file engineering/thoughts/shared/prs/${TASK_ID}_description.md

# 4. Move the Jira ticket to In Review; it moves to Done when the PR merges

# 5. Return to main repo
cd /path/to/main/repo

# 6. Remove worktree (after PR is merged)
git worktree remove ${WORKTREE_PATH}
git branch -d ${BRANCH_NAME}  # Delete local branch
```

### Troubleshooting

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
