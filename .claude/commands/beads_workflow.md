---
description: Common beads workflow commands and patterns
---

# Beads Workflow

Quick reference and helper for beads (`bd`) task management in a monorepo.

## Session Start

When beginning a work session:

```bash
# 1. Sync latest from git
bd sync

# 2. See what's ready to work on (no blockers)
bd ready

# 3. Filter by area if needed
bd ready -l client        # Client tasks only
bd ready -l api           # API tasks only
bd ready -l iac           # Infrastructure tasks only

# 4. Pick a task and claim it
bd update <id> --status in_progress

# 5. Check task details
bd show <id>
```

## Creating Tasks

```bash
# Create tasks with area labels
bd create "Add user endpoint" -t feature -p 1 -l api
bd create "Set up staging env" -t task -p 2 -l iac
bd create "Document auth flow" -t task -p 3 -l docs
bd create "Add login page" -t feature -p 1 -l client

# Cross-cutting tasks get multiple labels
bd create "Add CI/CD pipeline" -t task -p 1 -l api -l iac

# Link to GitHub issue in title
bd create "Implement auth (#123)" -t feature -p 1 -l api
```

### Area Labels
- `client` - Frontend application work (Next.js)
- `api` - Backend application work (Python/FastAPI)
- `iac` - Infrastructure as Code
- `docs` - Documentation
- Use multiple labels for cross-cutting work

### Task Types
- `bug` - Something broken
- `feature` - New functionality  
- `task` - General work item
- `chore` - Maintenance/cleanup

### Priority Levels
- `1` - Critical, do first
- `2` - Important
- `3` - Normal
- `4` - Low priority

## Managing Dependencies

```bash
# Add blocking dependency (B blocks A)
bd dep add <blocked-id> <blocker-id>

# View dependency tree
bd tree <id>

# Remove dependency
bd dep remove <blocked-id> <blocker-id>
```

### Dependency Types
- **blocks** - Task A blocks Task B (B can't start until A is done)
- **related** - Tasks are related but independent
- **parent-child** - Hierarchical relationship

## During Work

```bash
# Add comments/notes to a task
bd comment <id> "Found the root cause - see file.py:123"
bd comment <id> "Blocked waiting for API response"

# Update task status
bd update <id> --status in_progress
bd update <id> --status blocked
bd update <id> --status review

# Create sub-tasks discovered during work
bd create "Edge case: empty input" -t bug -p 2
bd dep add <new-id> <parent-id>
```

## Session End

```bash
# 1. Close completed work
bd close <id> --reason "Completed in PR #123"

# 2. Sync changes to git
bd sync

# 3. Commit beads changes (if not auto-synced)
git add .beads/issues.jsonl
git commit -m "beads: update task status"
git push
```

## Useful Queries

```bash
# Ready work (no blockers)
bd ready
bd ready -l api           # Ready API tasks only

# All in-progress work
bd list --status=in_progress

# Filter by area
bd list -l client         # Client tasks
bd list -l api            # API tasks
bd list -l iac            # Infrastructure tasks
bd list -l docs           # Documentation tasks

# High priority items
bd list --priority=1

# Bugs only
bd list --type=bug

# Combined filters
bd list -l api --type=bug --priority=1

# Everything
bd list

# Task details with history
bd show <id>

# Project statistics
bd stats
```

## Worktree Integration

When working in a git worktree:

```bash
# Always use no-daemon mode
export BEADS_NO_DAEMON=1

# Or per-command
bd --no-daemon ready
bd --no-daemon sync
```

## Troubleshooting

```bash
# Check beads health
bd doctor

# Force sync
bd sync --force

# Import from JSONL (after git pull)
bd import -i .beads/issues.jsonl

# Check which database is being used
bd where
```

## Integration with Claude Code Commands

### With `/create_plan`
```bash
# After creating a plan, link it to a task
bd comment <id> "Plan: thoughts/shared/plans/2025-01-22-feature.md"
```

### With `/implement_plan`
```bash
# Update status when starting
bd update <id> --status in_progress

# Close when done
bd close <id> --reason "Implemented per plan, PR #123"
```

### With `/create_handoff`
```bash
# Note the handoff in the task
bd comment <id> "Handoff: thoughts/shared/handoffs/<id>/2025-01-22.md"
```

## Quick Reference Card

| Action | Command |
|--------|---------|
| See available work | `bd ready` |
| Start a task | `bd update <id> --status in_progress` |
| Add a note | `bd comment <id> "note"` |
| Complete a task | `bd close <id> --reason "done"` |
| Create linked task | `bd create "title" && bd dep add <new> <parent>` |
| Sync with git | `bd sync` |
| Check health | `bd doctor` |
