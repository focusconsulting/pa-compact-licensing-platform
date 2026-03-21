---
description: Create handoff document for transferring work to another session
---

# Create Handoff

You are tasked with writing a handoff document to hand off your work to another agent in a new session. You will create a handoff document that is thorough, but also **concise**. The goal is to compact and summarize your context without losing any of the key details of what you're working on.

## Process

### 1. Gather Metadata

Run these commands to collect information:

```bash
# Get current date/time
date -Iseconds

# Get git info
git rev-parse HEAD
git branch --show-current
basename $(git remote get-url origin 2>/dev/null || echo "local-repo") .git

# Get beads task info (if working on a task)
bd show ${BEADS_ID} --json 2>/dev/null || echo "No active beads task"
```

### 2. Determine Filepath

Create the handoff at: `thoughts/shared/handoffs/<task-id>/YYYY-MM-DD_HH-MM-SS_description.md`

Where:
- `<task-id>` is the beads ID (e.g., `bd-a1b2`), GitHub issue (e.g., `issue-123`), or `general`
- `YYYY-MM-DD` is today's date
- `HH-MM-SS` is current time in 24-hour format
- `description` is a brief kebab-case description

Examples:
- `thoughts/shared/handoffs/bd-a1b2/2025-01-22_14-30-00_implementing-auth.md`
- `thoughts/shared/handoffs/issue-123/2025-01-22_14-30-00_refactor-parser.md`
- `thoughts/shared/handoffs/general/2025-01-22_14-30-00_exploring-options.md`

### 3. Write the Handoff Document

Use this template:

```markdown
---
date: [ISO format date-time with timezone]
git_commit: [Current commit hash]
branch: [Current branch name]
repository: [Repository name]
task_id: [Beads ID or GitHub issue, if applicable]
status: handoff
---

# Handoff: [Task ID] [Brief Description]

## Task(s)

[Description of the task(s) you were working on, with status of each:]
- **Completed**: [Tasks finished]
- **In Progress**: [Tasks partially done]
- **Planned**: [Tasks discussed but not started]

If working on an implementation plan, note which phase you're on and reference the plan document.

## Critical References

[List 2-3 most important files/documents that must be read to continue:]
- `thoughts/shared/plans/YYYY-MM-DD-xxx.md` - The implementation plan
- `src/module/file.py` - Key file being modified

## Recent Changes

[Describe changes made to the codebase in file:line format:]
- `src/auth/handler.py:45-67` - Added token validation logic
- `tests/test_auth.py:12-34` - Added unit tests for validation

## Learnings

[Important discoveries that the next agent should know:]
- Pattern: The codebase uses X pattern for Y
- Gotcha: Don't forget to Z when doing W
- Root cause: The bug was caused by...

## Artifacts

[Exhaustive list of files created or updated:]
- `thoughts/shared/plans/2025-01-22-issue-123-auth.md` - Implementation plan
- `thoughts/shared/research/2025-01-22-auth-patterns.md` - Research findings
- `src/auth/handler.py` - Modified for new validation

## Action Items & Next Steps

[Prioritized list for the next agent:]
1. [ ] Complete Phase 2 of the plan (add error handling)
2. [ ] Run manual testing for edge cases
3. [ ] Create PR when tests pass

## Other Notes

[Anything else useful:]
- Related files: `src/utils/validators.py` has similar patterns
- The user prefers approach X over Y
- Blocked on: waiting for API documentation
```

### 4. Commit the Handoff

```bash
# Create directory if needed
mkdir -p thoughts/shared/handoffs/${TASK_ID}

# After writing the file
git add thoughts/shared/handoffs/
git commit -m "docs: handoff for ${TASK_ID}"
```

### 5. Respond to User

After creating and committing:

```
Handoff created and committed! You can resume from this handoff in a new session with:

```bash
/resume_handoff thoughts/shared/handoffs/<task-id>/YYYY-MM-DD_HH-MM-SS_description.md
```

Or to resume the latest handoff for this task:
```bash
/resume_handoff <task-id>
```
```

## Guidelines

- **More information, not less** - This defines the minimum; include more if needed
- **Be thorough and precise** - Include both high-level objectives and low-level details
- **Avoid excessive code snippets** - Prefer `file:line` references over large code blocks
- **Include file paths** - Use exact paths so the next agent can navigate easily
- **Note blockers** - If waiting on something, document it clearly
- **Reference plans** - If working from a plan, always reference which phase

## Common Scenarios

### Mid-Implementation Handoff
Focus on:
- Exactly where you stopped
- What's left to do in current phase
- Any issues encountered

### End of Feature Handoff
Focus on:
- Summary of all changes
- Testing that was done
- PR readiness

### Exploratory/Research Handoff
Focus on:
- What was explored
- Conclusions reached
- Recommended next steps
