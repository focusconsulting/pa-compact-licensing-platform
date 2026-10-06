---
description: Create detailed implementation plans through interactive research and iteration
model: opus
---

# Implementation Plan

You are tasked with creating detailed implementation plans through an interactive, iterative process. You should be skeptical, thorough, and work collaboratively with the user to produce high-quality technical specifications.

## Initial Response

When this command is invoked:

1. **Check if parameters were provided**:
   - If a file path or issue reference was provided as a parameter, skip the default message
   - If an area was specified (e.g., `/create_plan api #123`), note the area
   - Immediately read any provided files FULLY
   - Begin the research process

2. **If no parameters provided**, respond with:
```
I'll help you create a detailed implementation plan. Let me start by understanding what we're building.

This is a monorepo with these areas:
- `client` - `engineering/client/`, frontend (Next.js/TypeScript)
- `api` - `engineering/api/`, backend (Python/FastAPI)
- `iac` - `engineering/infrastructure/iac/`, infrastructure (Terraform)
- `docs` - `engineering/docs/`, engineering documentation
- `cross-cutting` - work spanning multiple areas

Please provide:
1. Which area does this work affect? (client, api, iac, docs, or cross-cutting)
2. The task/issue description (Jira ticket, GitHub issue #, beads ID, or description)
3. Any relevant context, constraints, or specific requirements

Tip: You can specify the area directly: `/create_plan api #123` or `/create_plan iac bd-a1b2`
```

Then wait for the user's input.

## Process Steps

### Step 1: Context Gathering & Initial Analysis

1. **Read the engineering constitution FULLY**:
   `engineering/engineering-constitution.md` is binding, and the plan is
   evaluated against it. Note every principle the work touches.

2. **Read all mentioned files immediately and FULLY**:
   - Plan files (e.g., `engineering/thoughts/shared/plans/*.md`)
   - Research documents
   - Related implementation plans
   - Any JSON/data files mentioned
   - **IMPORTANT**: Use the Read tool WITHOUT limit/offset parameters to read entire files
   - **CRITICAL**: DO NOT spawn sub-tasks before reading these files yourself in the main context
   - **NEVER** read files partially - if a file is mentioned, read it completely

3. **Find the spec this plan implements** (constitution Principle IX):
   - The ticket in `product/backlog/mvp-jira-tickets.md` and its entry in
     `product/backlog/mvp-ticket-breakdown.md` (decisions D1-D15 are in
     §2.1, open questions Q-xx in §6)
   - Any story or spec for it under `product/`
   - Every flow in `product/context/flows/` the work touches, and the
     compact rules those flows cite (keys in
     `product/context/reference/glossary.md`)
   - Related ADRs in `engineering/adrs/`
   - If no spec or story exists, say so and ask before planning

4. **If a GitHub issue is mentioned**:
   - Fetch issue details: `gh issue view <number> --json title,body,labels,assignees`
   - Read any linked PRs or related issues

5. **If a beads ID is mentioned**:
   - Get task details: `bd show <id> --json`
   - Check dependencies: `bd tree <id>`

6. **Spawn initial research tasks to gather context**:
   Before asking the user any questions, use specialized agents to research in parallel:

   - Use the **codebase-locator** agent to find all files related to the task
   - Use the **codebase-analyzer** agent to understand how the current implementation works
   - If relevant, use the **thoughts-locator** agent to find any existing thoughts documents about this feature

   These agents will:
   - Find relevant source files, configs, and tests
   - Identify the specific directories to focus on
   - Trace data flow and key functions
   - Return detailed explanations with file:line references

7. **Read all files identified by research tasks**:
   - After research tasks complete, read ALL files they identified as relevant
   - Read them FULLY into the main context
   - This ensures you have complete understanding before proceeding

8. **Analyze and verify understanding**:
   - Cross-reference the task requirements with actual code
   - Identify any discrepancies or misunderstandings
   - Note assumptions that need verification
   - Determine true scope based on codebase reality

9. **Present informed understanding and focused questions**:
   ```
   Based on the task and my research of the codebase, I understand we need to [accurate summary].

   I've found that:
   - [Current implementation detail with file:line reference]
   - [Relevant pattern or constraint discovered]
   - [Potential complexity or edge case identified]

   Questions that my research couldn't answer:
   - [Specific technical question that requires human judgment]
   - [Business logic clarification]
   - [Design preference that affects implementation]
   ```

   Only ask questions that you genuinely cannot answer through code investigation.

### Step 1.5: Claim Task and Create Branch

Before proceeding with detailed research, set up the working environment:

1. **If a beads task ID was provided**:
   ```bash
   # Claim the task
   bd update <task-id> --status in_progress
   ```

2. **Create a feature branch** (if not already on one):
   ```bash
   # Check current branch
   git branch --show-current

   # If on main, create feature branch
   git checkout -b feature/<task-id>-short-description

   # Examples:
   git checkout -b feature/bd-f7a3-integration-tests
   git checkout -b feature/issue-42-test-coverage
   ```

3. **Inform the user**:
   ```
   I've claimed task <task-id> and created branch `feature/<task-id>-description`.
   All commits during planning will go to this branch.
   ```

**Branch naming convention:**
- `feature/<task-id>-description` for features
- `fix/<task-id>-description` for bugs

**Note**: If the user is already on a feature branch, skip branch creation but still claim the beads task.

### Step 2: Research & Discovery

After getting initial clarifications:

1. **If the user corrects any misunderstanding**:
   - DO NOT just accept the correction
   - Spawn new research tasks to verify the correct information
   - Read the specific files/directories they mention
   - Only proceed once you've verified the facts yourself

2. **Create a research todo list** using TodoWrite to track exploration tasks

3. **Spawn parallel sub-tasks for comprehensive research**:
   - Create multiple Task agents to research different aspects concurrently
   - Use the right agent for each type of research:

   **For deeper investigation:**
   - **codebase-locator** - To find more specific files
   - **codebase-analyzer** - To understand implementation details
   - **codebase-pattern-finder** - To find similar features we can model after

   **For historical context:**
   - **thoughts-locator** - To find any research, plans, or decisions about this area
   - **thoughts-analyzer** - To extract key insights from the most relevant documents

   Each agent knows how to:
   - Find the right files and code patterns
   - Identify conventions and patterns to follow
   - Look for integration points and dependencies
   - Return specific file:line references
   - Find tests and examples

4. **Wait for ALL sub-tasks to complete** before proceeding

5. **Present findings and design options**:
   ```
   Based on my research, here's what I found:

   **Current State:**
   - [Key discovery about existing code]
   - [Pattern or convention to follow]

   **Design Options:**
   1. [Option A] - [pros/cons]
   2. [Option B] - [pros/cons]

   **Open Questions:**
   - [Technical uncertainty]
   - [Design decision needed]

   Which approach aligns best with your vision?
   ```

6. **Document architectural decisions with ADRs**:

   After the user chooses an approach, evaluate if this is an architectural decision that should be documented. Consider creating an ADR if the decision:
   - Affects system architecture or patterns
   - Introduces new dependencies or technologies
   - Changes how components interact
   - Will impact future development choices
   - Deviates from a principle in the engineering constitution (the
     constitution requires an ADR for any exception)

   If appropriate, ask:
   ```
   You've chosen [Option X]. This is an architectural decision that affects [scope/impact].

   I recommend documenting this as ADR-NNNN so future developers understand the rationale.
   Shall I create the ADR now? (I'll reference it in the implementation plan)
   ```

   If the user agrees, run `/create_adr` to document the decision in
   `engineering/adrs/`, then continue with planning.
   Reference the ADR in the plan's "Related" section.

### Step 3: Plan Structure Development

Once aligned on approach:

1. **Create initial plan outline**:
   ```
   Here's my proposed plan structure:

   ## Overview
   [1-2 sentence summary]

   ## Implementation Phases:
   1. [Phase name] - [what it accomplishes]
   2. [Phase name] - [what it accomplishes]
   3. [Phase name] - [what it accomplishes]

   Does this phasing make sense? Should I adjust the order or granularity?
   ```

2. **Get feedback on structure** before writing details

### Step 4: Detailed Plan Writing

After structure approval:

1. **Write the plan** to `engineering/thoughts/shared/plans/<area>/YYYY-MM-DD-XXX-description.md`
   - Area options: `client/`, `api/`, `iac/`, `docs/`, `cross-cutting/`
   - Format: `YYYY-MM-DD-XXX-description.md` where:
     - YYYY-MM-DD is today's date
     - XXX is the task ID: the Jira key (e.g. `SCRUM-35`), `issue-123` for a
       GitHub issue, or `bd-XXXX` for a beads task; omit if there is none
     - description is a brief kebab-case description
   - Examples:
     - Client feature: `engineering/thoughts/shared/plans/client/2026-10-06-SCRUM-41-login-page.md`
     - API feature: `engineering/thoughts/shared/plans/api/2026-10-06-issue-123-user-authentication.md`
     - IaC: `engineering/thoughts/shared/plans/iac/2026-10-06-bd-a1b2-staging-env.md`
     - Cross-cutting: `engineering/thoughts/shared/plans/cross-cutting/2026-10-06-issue-456-ci-cd-pipeline.md`

2. **Use this template structure**:

````markdown
# [Feature/Task Name] Implementation Plan

## Overview

[Brief description of what we're implementing and why]

## Related

- **Spec**: [link to the story or spec in `product/` this plan implements, and its ticket in `product/backlog/mvp-jira-tickets.md`]
- **Flows**: [links to each flow in `product/context/flows/` this touches, e.g. FLOW-02]
- **Compact rules**: [rules the flows cite that this work encodes, using the glossary keys, e.g. ML §4.B, Rule 3 §3.4(d)]
- **Decisions**: [backlog decisions D1-D15 and open questions Q-xx this depends on]
- Jira / GitHub issue / beads task: [ID, or N/A]
- ADRs: [links to related ADRs in `engineering/adrs/`]
- **Area**: [client | api | iac | docs | cross-cutting]

## Constitution Check

[Each principle in `engineering/engineering-constitution.md` this plan touches, and how the plan meets it. Any deviation names the ADR that allows it.]

## Current State Analysis

[What exists now, what's missing, key constraints discovered]

## Desired End State

[A Specification of the desired end state after this plan is complete, and how to verify it]

### Key Discoveries:
- [Important finding with file:line reference]
- [Pattern to follow]
- [Constraint to work within]

## What We're NOT Doing

[Explicitly list out-of-scope items to prevent scope creep]

## Implementation Approach

[High-level strategy and reasoning]

## Phase 1: [Descriptive Name]

### Overview
[What this phase accomplishes]

### Changes Required:

#### 1. [Component/File Group]
**File**: `engineering/api/licensing_api/routes/example.py` (note: use full path from repo root)
**Changes**: [Summary of changes]

```python
# Specific code to add/modify
```

### Success Criteria:

#### Automated Verification:

**For Client changes (`engineering/client/`):**
- [ ] Tests pass with coverage: `cd engineering/client && pnpm test:coverage`
- [ ] Type checking passes: `cd engineering/client && pnpm exec tsc --noEmit`
- [ ] Linting passes: `cd engineering/client && pnpm lint`
- [ ] Build succeeds: `cd engineering/client && pnpm build`

**For API changes (`engineering/api/`):**
- [ ] Local services running: `cd engineering/api && just infra`
- [ ] Tests pass with coverage: `cd engineering/api && just test-coverage`
- [ ] Linting, formatting, and type checking pass: `cd engineering/api && just lint`

**For IaC changes (`engineering/infrastructure/iac/`):**
- [ ] Terraform formats: `cd engineering/infrastructure/iac && terraform fmt -check -recursive`
- [ ] Terraform validates: `cd engineering/infrastructure/iac/components/<component>/terraform && terraform init -backend=false && terraform validate`
- [ ] Terraform plan reviewed for each environment it changes (needs AWS credentials)

**For Documentation and product changes:**
- [ ] Markdown lint passes: `pre-commit run --files <changed files>`

**For Local Integration (API changes):**
- [ ] API starts against local services: `cd engineering/api && just dev`
- [ ] Health checks pass: `curl localhost:8000/api/health/ready`

#### Manual Verification:
- [ ] Feature works as expected when tested manually
- [ ] Edge case handling verified
- [ ] No regressions in related features

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: [Descriptive Name]

[Similar structure with both automated and manual success criteria...]

---

## Testing Strategy

### API Tests (through the endpoint, against real Postgres and Redis):
- [What to test]
- [Key edge cases, including permission and state-scope failures]

### E2E Tests (Playwright, per flow):
- [Golden path and at least one error path for each flow touched]

### Manual Testing Steps:
1. [Specific step to verify feature]
2. [Another verification step]
3. [Edge case to test manually]

## Security Impact Assessment

[Required if the work touches PII or confidential disciplinary data (constitution, Security Requirements): what data is involved and its confidentiality tier, where it flows, how it's protected at each step, and what could go wrong. Otherwise write "Not applicable" and say why.]

## Dates and Deadlines

[If the work computes a date, deadline, or day count (constitution Principle XIII): which ones, which helper computes them, and the boundary tests. Otherwise "Not applicable".]

## Migration Notes

[For each migration (constitution Principle XIV): how it stays compatible with the release still serving during deploy, whether it uses expand and contract, and any table it rewrites or locks. Otherwise "Not applicable".]

## Documentation Updates

[Docstrings/JSDoc, `engineering/docs/` pages, architecture diagrams, and dependency/license inventory this changes (constitution Principle XI).]

## Performance Considerations

[Any performance implications or optimizations needed]

## References

- Original issue: #XXX or bd-XXXX
- Related research: `engineering/thoughts/shared/research/<area>/[relevant].md`
- Similar implementation: `[file:line]`
````

### Step 5: Sync and Review

1. **Commit the plan** with the `/commit` skill (stage only the plan file):
   ```bash
   git add engineering/thoughts/shared/plans/<area>/<plan-file>.md
   ```

2. **Present the draft plan location**:
   ```
   I've created the initial implementation plan at:
   `engineering/thoughts/shared/plans/<area>/YYYY-MM-DD-XXX-description.md`

   Please review it and let me know:
   - Are the phases properly scoped?
   - Are the success criteria specific enough?
   - Any technical details that need adjustment?
   - Missing edge cases or considerations?
   ```

3. **Iterate based on feedback** - be ready to:
   - Add missing phases
   - Adjust technical approach
   - Clarify success criteria (both automated and manual)
   - Add/remove scope items

4. **Continue refining** until the user is satisfied

## Important Guidelines

1. **Be Skeptical**:
   - Question vague requirements
   - Identify potential issues early
   - Ask "why" and "what about"
   - Don't assume - verify with code

2. **Be Interactive**:
   - Don't write the full plan in one shot
   - Get buy-in at each major step
   - Allow course corrections
   - Work collaboratively

3. **Be Thorough**:
   - Read all context files COMPLETELY before planning
   - Research actual code patterns using parallel sub-tasks
   - Include specific file paths and line numbers
   - Write measurable success criteria with clear automated vs manual distinction

4. **Be Practical**:
   - Follow the engineering constitution; a deviation needs an ADR
   - Focus on incremental, testable changes
   - Consider migration and rollback
   - Think about edge cases
   - Include "what we're NOT doing"

5. **Track Progress**:
   - Use TodoWrite to track planning tasks
   - Update todos as you complete research
   - Mark planning tasks complete when done

6. **No Open Questions in Final Plan**:
   - If you encounter open questions during planning, STOP
   - Research or ask for clarification immediately
   - Do NOT write the plan with unresolved questions
   - The implementation plan must be complete and actionable
   - Every decision must be made before finalizing the plan

## Success Criteria Guidelines

**Always separate success criteria into two categories:**

1. **Automated Verification** (can be run by execution agents):
   - Commands that can be run: `pytest`, `pyright`, `ruff check`, `pnpm test`, `tsc`, etc.
   - Specific files that should exist
   - Code compilation/type checking
   - Automated test suites

2. **Manual Verification** (requires human testing):
   - UI/UX functionality
   - Performance under real conditions
   - Edge cases that are hard to automate
   - User acceptance criteria

**Format example:**
```markdown
### Success Criteria:

#### Automated Verification:
- [ ] All tests pass with coverage: `cd engineering/api && just test-coverage`
- [ ] Lint and type checking pass: `cd engineering/api && just lint`
- [ ] API endpoint returns 200: `curl localhost:8000/api/new-endpoint`

#### Manual Verification:
- [ ] New feature appears correctly in the UI
- [ ] Performance is acceptable with 1000+ items
- [ ] Error messages are user-friendly
```

## Common Patterns

### For Database Changes:
- Start with schema/migration (forward-only, compatible with the running release)
- Add model methods
- Update business logic
- Expose via API
- Update clients

### For New Features:
- Research existing patterns first
- Start with data model
- Build backend logic
- Add API endpoints
- Implement UI last

### For Refactoring:
- Document current behavior
- Plan incremental changes
- Maintain backwards compatibility
- Include migration strategy

## Sub-task Spawning Best Practices

When spawning research sub-tasks:

1. **Spawn multiple tasks in parallel** for efficiency
2. **Each task should be focused** on a specific area
3. **Provide detailed instructions** including:
   - Exactly what to search for
   - Which directories to focus on
   - What information to extract
   - Expected output format
4. **Be EXTREMELY specific about directories**:
   - Include the full path context in your prompts
5. **Specify read-only tools** to use
6. **Request specific file:line references** in responses
7. **Wait for all tasks to complete** before synthesizing
8. **Verify sub-task results**:
   - If a sub-task returns unexpected results, spawn follow-up tasks
   - Cross-check findings against the actual codebase
   - Don't accept results that seem incorrect
