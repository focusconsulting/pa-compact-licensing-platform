---
description: Clean up plans and handoffs after PR merge or task completion
---

# Post-Merge Cleanup

This command helps clean up working documents after a PR has been merged or a task has been completed.

## Retention Policy

| Document Type | Retention | Reason |
|---------------|-----------|--------|
| ADRs (`docs/architecture_decision_records/`) | **Forever** | Architectural decisions - reference value |
| Plans (`thoughts/shared/plans/`) | **Delete after PR merge** | Embedded in PR description |
| Handoffs (`thoughts/shared/handoffs/`) | **Delete after task closes** | Session continuity only |
| PR descriptions (`thoughts/shared/prs/`) | **Never commit** | Local working files |
| Research (`thoughts/shared/research/`) | **Keep if reusable** | Delete one-off research |

## Steps

### 1. Identify what to clean up

```bash
# Check for merged PRs with associated plans
gh pr list --state merged --limit 10 --json number,title,mergedAt,headRefName

# Check for closed beads tasks
bd list --status=closed --limit 10

# List current plans
ls -la thoughts/shared/plans/*/

# List current handoffs
ls -la thoughts/shared/handoffs/*/
```

### 2. For a specific merged PR / closed task

If the user specifies a task ID (e.g., `bd-f7a3`):

```bash
# Find associated files
find thoughts/shared/plans -name "*bd-f7a3*" -o -name "*<task-id>*"
find thoughts/shared/handoffs -name "*bd-f7a3*" -o -name "*<task-id>*"

# Verify the PR was merged
gh pr list --state merged --search "bd-f7a3"
```

### 3. Delete plan files (after confirming PR merged)

```bash
# Remove plan file(s) for the task
rm thoughts/shared/plans/<component>/<date>-<task-id>-*.md

# Remove any empty directories
find thoughts/shared/plans -type d -empty -delete
```

### 4. Delete handoff files (after confirming task closed)

```bash
# Remove handoff directory for the task
rm -rf thoughts/shared/handoffs/<task-id>/

# Remove any empty directories
find thoughts/shared/handoffs -type d -empty -delete
```

### 5. Clean up stale research (optional)

Ask the user if any research docs should be kept:

```bash
# List research files
ls -la thoughts/shared/research/*/

# Remove one-off research (with user confirmation)
rm thoughts/shared/research/<component>/<file>.md
```

### 6. Commit the cleanup

```bash
git add -A
git commit -m "chore: cleanup working docs after <task-id> merge"
git push
```

### 7. Report to user

```
**Cleanup complete for <task-id>:**

Deleted:
- thoughts/shared/plans/<component>/<plan-file>.md
- thoughts/shared/handoffs/<task-id>/

Retained:
- docs/architecture_decision_records/NNNN-*.md (architectural decisions - kept forever)

The implementation plan content is preserved in PR #XX.
```

## Bulk Cleanup

For periodic maintenance, clean up all stale files:

```bash
# Delete plans older than 30 days (assumes PR is merged by then)
find thoughts/shared/plans -name "*.md" -mtime +30 -type f

# Delete handoffs older than 14 days
find thoughts/shared/handoffs -name "*.md" -mtime +14 -type f

# Preview before deleting
find thoughts/shared/plans -name "*.md" -mtime +30 -type f -exec echo "Would delete: {}" \;

# Actually delete (with user confirmation)
find thoughts/shared/plans -name "*.md" -mtime +30 -type f -delete
find thoughts/shared/handoffs -name "*.md" -mtime +14 -type f -delete
```

## Important Notes

- **Always verify the PR was merged** before deleting a plan
- **ADRs are never deleted** - they document architectural decisions
- **The PR description contains the embedded plan** - that's your audit trail
- **Research docs**: Ask before deleting - some may have ongoing value
