---
description: Implement technical plans from thoughts/shared/plans with verification
---

# Implement Plan

You are tasked with implementing an approved technical plan from `thoughts/shared/plans/`. These plans contain phases with specific changes and success criteria.

## Getting Started

When given a plan path:
- Read the plan completely and check for any existing checkmarks (- [x])
- Read the original issue/task and all files mentioned in the plan
- **Read files fully** - never use limit/offset parameters, you need complete context
- Think deeply about how the pieces fit together
- Create a todo list to track your progress
- Start implementing if you understand what needs to be done

If no plan path provided, ask for one or list available plans:
```bash
# List plans by component
echo "=== Client Plans ===" && ls -lt thoughts/shared/plans/client/ 2>/dev/null | head -5
echo "=== API Plans ===" && ls -lt thoughts/shared/plans/api/ 2>/dev/null | head -5
echo "=== IaC Plans ===" && ls -lt thoughts/shared/plans/iac/ 2>/dev/null | head -5
echo "=== Docs Plans ===" && ls -lt thoughts/shared/plans/docs/ 2>/dev/null | head -5
echo "=== Cross-cutting Plans ===" && ls -lt thoughts/shared/plans/cross-cutting/ 2>/dev/null | head -5
```

## Implementation Philosophy

Plans are carefully designed, but reality can be messy. Your job is to:
- Follow the plan's intent while adapting to what you find
- Implement each phase fully before moving to the next
- Verify your work makes sense in the broader codebase context
- Update checkboxes in the plan as you complete sections

When things don't match the plan exactly, think about why and communicate clearly. The plan is your guide, but your judgment matters too.

If you encounter a mismatch:
- STOP and think deeply about why the plan can't be followed
- Present the issue clearly:
  ```
  Issue in Phase [N]:
  Expected: [what the plan says]
  Found: [actual situation]
  Why this matters: [explanation]

  How should I proceed?
  ```

## Verification Approach

After implementing a phase:

1. **Identify the affected area(s)** from the plan's "Area" field and file paths

2. **Run the area-specific success criteria checks**:

   **For Client (`client/`) changes:**
   ```bash
   cd client
   pnpm test                 # Run tests
   pnpm tsc --noEmit         # Type checking
   pnpm lint                 # Linting
   pnpm build                # Build check
   cd ..
   ```

   **For API (`api/`) changes:**
   ```bash
   cd api
   uv run pytest             # Run tests
   uv run pyright            # Type checking
   uv run ruff check .       # Linting
   uv run ruff format --check .  # Format check
   cd ..
   ```

   **For IaC (`iac/`) changes:**
   ```bash
   cd iac
   terraform validate
   terraform fmt -check
   terraform plan            # Review the plan output
   cd ..
   ```

   **For Documentation (`docs/`) changes:**
   ```bash
   cd docs
   mkdocs build              # or equivalent doc build command
   cd ..
   ```

3. **Fix any issues before proceeding**

3. **Update your progress**:
   - Check off completed items in the plan file itself using Edit
   - Update your todo list

4. **Pause for human verification**:
   After completing all automated verification for a phase, pause and inform the human:
   ```
   Phase [N] Complete - Ready for Manual Verification

   Automated verification passed:
   - [List automated checks that passed]

   Please perform the manual verification steps listed in the plan:
   - [List manual verification items from the plan]

   Let me know when manual testing is complete so I can proceed to Phase [N+1].
   ```

If instructed to execute multiple phases consecutively, skip the pause until the last phase. Otherwise, assume you are doing one phase at a time.

Do not check off items in the manual testing steps until confirmed by the user.

## Beads Integration

When working on a beads-tracked task:

```bash
# At start of implementation - claim task and create branch
bd update ${BEADS_ID} --status in_progress

# Create feature branch (if not already on one)
git checkout -b feature/${BEADS_ID}-short-description
# Example: git checkout -b feature/bd-f7a3-integration-tests

bd comment ${BEADS_ID} "Starting implementation on branch feature/${BEADS_ID}-..."

# If you discover new tasks
bd create "Discovered issue: description" -t bug -p 2
bd dep add ${NEW_ID} ${BEADS_ID}

# At completion
bd close ${BEADS_ID} --reason "Completed - PR #XXX"
bd sync
```

**Branch naming convention:**
- `feature/<task-id>-short-description` for features
- `fix/<task-id>-short-description` for bugs

Always verify you're on the correct branch before committing:
```bash
git branch --show-current
```

## If You Get Stuck

When something isn't working as expected:
- First, make sure you've read and understood all the relevant code
- Consider if the codebase has evolved since the plan was written
- Present the mismatch clearly and ask for guidance

Use sub-tasks sparingly - mainly for targeted debugging or exploring unfamiliar territory.

## Resuming Work

If the plan has existing checkmarks:
- Trust that completed work is done
- Pick up from the first unchecked item
- Verify previous work only if something seems off

## Committing Progress

After completing a phase or significant milestone:

```bash
# Stage changes
git add .

# Commit with descriptive message referencing the plan
git commit -m "feat: implement Phase N - [description]

- Change 1
- Change 2

Plan: thoughts/shared/plans/YYYY-MM-DD-xxx.md
Task: bd-XXXX or #XXX"
```

## Completion

When all phases are complete:

1. **Run full verification for affected components**:

   **For Client changes:**
   ```bash
   cd client && pnpm test && pnpm tsc --noEmit && pnpm lint && pnpm build && cd ..
   ```

   **For API changes:**
   ```bash
   cd api && uv run pytest && uv run pyright && uv run ruff check . && uv run ruff format --check . && cd ..
   ```

   **For IaC changes:**
   ```bash
   cd iac && terraform validate && terraform fmt && cd ..
   ```

   **For Documentation changes:**
   ```bash
   cd docs && mkdocs build && cd ..
   ```

   **For local integration (all changes):**
   ```bash
   docker compose build
   docker compose up -d
   docker compose ps  # verify all services healthy
   ```

2. **Update beads task**:
   ```bash
   bd comment ${BEADS_ID} "Implementation complete, all tests passing"
   ```

3. **Suggest next steps**:
   ```
   Implementation complete! All phases finished and verified.

   Next steps:
   1. Run `/describe_pr` to generate PR description
   2. Create PR: `gh pr create --fill`
   3. Close beads task after PR is merged

   Would you like me to proceed with the PR description?
   ```

Remember: You're implementing a solution, not just checking boxes. Keep the end goal in mind and maintain forward momentum.
