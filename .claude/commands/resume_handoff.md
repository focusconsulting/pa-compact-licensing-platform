---
description: Resume work from handoff document with context analysis and validation
---

# Resume work from a handoff document

You are tasked with resuming work from a handoff document through an interactive process. These handoffs contain critical context, learnings, and next steps from previous work sessions that need to be understood and continued.

## Initial Response

When this command is invoked:

1. **If the path to a handoff document was provided**:
   - Immediately read the handoff document FULLY
   - Immediately read any research or plan documents that it links to under `thoughts/shared/plans` or `thoughts/shared/research`. Do NOT use a sub-agent to read these critical files.
   - Begin the analysis process by ingesting relevant context from the handoff document, reading additional files it mentions
   - Then propose a course of action to the user and confirm, or ask for clarification on direction.

2. **If a task ID (like bd-XXXX or issue-XXX) was provided**:
   - Pull latest changes: `git pull`
   - Locate the most recent handoff document for the task in `thoughts/shared/handoffs/<task-id>/`
   - List the directory contents to find the most recent file (by timestamp in filename)
   - **If no files exist**: tell the user "I can't find any handoff documents for that task. Can you provide a path?"
   - **If one file exists**: proceed with that handoff
   - **If multiple files exist**: use the most recent one (latest timestamp in filename)
   - Read the handoff document FULLY
   - Read any linked plans or research documents
   - Propose a course of action

3. **If no parameters provided**, respond with:
   ```
   I'll help you resume work from a handoff document. 
   
   You can provide:
   - A full path: `/resume_handoff thoughts/shared/handoffs/bd-a1b2/2025-01-22_14-30-00_description.md`
   - A task ID: `/resume_handoff bd-a1b2` or `/resume_handoff issue-123`
   
   Let me check for recent handoffs...
   ```
   Then run `ls -lt thoughts/shared/handoffs/*/` to show available handoffs.

## Process Steps

### Step 1: Read and Analyze Handoff

1. **Read handoff document completely**:
   - Use the Read tool WITHOUT limit/offset parameters
   - Extract all sections:
     - Task(s) and their statuses
     - Recent changes
     - Learnings
     - Artifacts
     - Action items and next steps
     - Other notes

2. **Spawn focused research tasks** if needed:
   Based on the handoff content, spawn parallel research tasks to verify current state:

   ```
   Task 1 - Gather artifact context:
   Read all artifacts mentioned in the handoff.
   1. Read feature documents listed in "Artifacts"
   2. Read implementation plans referenced
   3. Read any research documents mentioned
   4. Extract key requirements and decisions
   Use tools: Read
   Return: Summary of artifact contents and key decisions
   ```

3. **Wait for ALL sub-tasks to complete** before proceeding

4. **Read critical files identified**:
   - Read files from "Learnings" section completely
   - Read files from "Recent changes" to understand modifications
   - Read any new related files discovered during research

### Step 2: Verify Current State

```bash
# Check git state
git status
git log --oneline -5

# Check if we're on the right branch
git branch --show-current

# Check beads task status
bd show ${TASK_ID} --json 2>/dev/null

# Verify recent changes still exist
git diff --name-only HEAD~3..HEAD
```

### Step 3: Synthesize and Present Analysis

Present comprehensive analysis:

```
I've analyzed the handoff from [date]. Here's the current situation:

**Original Tasks:**
- [Task 1]: [Status from handoff] → [Current verification]
- [Task 2]: [Status from handoff] → [Current verification]

**Key Learnings Validated:**
- [Learning with file:line reference] - [Still valid/Changed]
- [Pattern discovered] - [Still applicable/Modified]

**Recent Changes Status:**
- [Change 1] - [Verified present/Missing/Modified]
- [Change 2] - [Verified present/Missing/Modified]

**Artifacts Reviewed:**
- [Document 1]: [Key takeaway]
- [Document 2]: [Key takeaway]

**Recommended Next Actions:**
Based on the handoff's action items and current state:
1. [Most logical next step based on handoff]
2. [Second priority action]
3. [Additional tasks discovered]

**Potential Issues Identified:**
- [Any conflicts or regressions found]
- [Missing dependencies or broken code]

Shall I proceed with [recommended action 1], or would you like to adjust the approach?
```

Get confirmation before proceeding.

### Step 4: Create Action Plan

1. **Use TodoWrite to create task list**:
   - Convert action items from handoff into todos
   - Add any new tasks discovered during analysis
   - Prioritize based on dependencies and handoff guidance

2. **Present the plan**:
   ```
   I've created a task list based on the handoff and current analysis:

   [Show todo list]

   Ready to begin with the first task: [task description]?
   ```

### Step 5: Begin Implementation

1. **Start with the first approved task**
2. **Reference learnings from handoff** throughout implementation
3. **Apply patterns and approaches documented** in the handoff
4. **Update progress** as tasks are completed

## Guidelines

1. **Be Thorough in Analysis**:
   - Read the entire handoff document first
   - Verify ALL mentioned changes still exist
   - Check for any regressions or conflicts
   - Read all referenced artifacts

2. **Be Interactive**:
   - Present findings before starting work
   - Get buy-in on the approach
   - Allow for course corrections
   - Adapt based on current state vs handoff state

3. **Leverage Handoff Wisdom**:
   - Pay special attention to "Learnings" section
   - Apply documented patterns and approaches
   - Avoid repeating mistakes mentioned
   - Build on discovered solutions

4. **Track Continuity**:
   - Use TodoWrite to maintain task continuity
   - Reference the handoff document in commits
   - Document any deviations from original plan
   - Consider creating a new handoff when done

5. **Validate Before Acting**:
   - Never assume handoff state matches current state
   - Verify all file references still exist
   - Check for breaking changes since handoff
   - Confirm patterns are still valid

## Common Scenarios

### Scenario 1: Clean Continuation
- All changes from handoff are present
- No conflicts or regressions
- Clear next steps in action items
- Proceed with recommended actions

### Scenario 2: Diverged Codebase
- Some changes missing or modified
- New related code added since handoff
- Need to reconcile differences
- Adapt plan based on current state

### Scenario 3: Incomplete Handoff Work
- Tasks marked as "in_progress" in handoff
- Need to complete unfinished work first
- May need to re-understand partial implementations
- Focus on completing before new work

### Scenario 4: Stale Handoff
- Significant time has passed
- Major refactoring has occurred
- Original approach may no longer apply
- Need to re-evaluate strategy
