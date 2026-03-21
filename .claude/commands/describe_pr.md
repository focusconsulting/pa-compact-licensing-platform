---
description: Generate comprehensive PR descriptions following repository templates
---

# Generate PR Description

You are tasked with generating a comprehensive pull request description.

## Steps to follow:

### 1. Identify the PR to describe

```bash
# Check if current branch has a PR
gh pr view --json url,number,title,state 2>/dev/null

# If no PR exists, check current branch
git branch --show-current

# List open PRs if needed
gh pr list --limit 10 --json number,title,headRefName,author
```

If no PR exists for the current branch and not on main, inform the user they can create one after generating the description.

### 2. Gather PR information

```bash
# Get the full diff against main
git diff origin/main...HEAD

# Get commit history
git log origin/main..HEAD --oneline

# Get changed files
git diff origin/main...HEAD --name-only

# If PR exists, get metadata
gh pr view --json url,title,number,state,baseRefName
```

### 3. Check for related context

Look for:
- Implementation plan in `thoughts/shared/plans/`
- Related beads task: `bd show <id>`
- GitHub issue: `gh issue view <number>`

**Important**: If an implementation plan exists, read it fully. You will embed it in the PR description.

### 4. Analyze the changes thoroughly

Think deeply about:
- The purpose and impact of each change
- User-facing changes vs internal implementation
- Breaking changes or migration requirements
- Test coverage

### 5. Run verification checks

```bash
# Client checks
cd client && pnpm test && pnpm tsc --noEmit && pnpm lint && cd ..

# API checks
cd api && uv run pytest && uv run pyright && uv run ruff check . && uv run ruff format --check . && cd ..

# IaC checks (if applicable)
cd iac && terraform validate && cd ..
```

Document which checks pass/fail.

### 6. Generate the description

Write to `thoughts/shared/prs/<task-id>_description.md`:

```markdown
## Summary

[2-3 sentence summary of what this PR does and why]

## Related

- Closes #XXX (GitHub issue)
- Beads: bd-XXXX
- ADR: [Link to ADR if applicable]

## Changes

### [Category 1: e.g., Core Changes]
- Change description with context
- Another change

### [Category 2: e.g., Tests]
- Test additions/modifications

### [Category 3: e.g., Documentation]
- Doc updates

## How to Test

### Automated
```bash
pytest tests/test_feature.py
```

### Manual
1. Step to verify the feature
2. Another verification step
3. Edge case to check

## Checklist

- [x] Client tests pass (`cd client && pnpm test`)
- [x] API tests pass (`cd api && uv run pytest`)
- [x] Type checking passes
- [x] Linting passes
- [ ] Documentation updated (if applicable)
- [ ] Manual testing completed

## Screenshots / Examples

[If applicable, add screenshots or example output]

## Notes for Reviewers

[Any specific areas to focus review on, known limitations, or context]

---

<details>
<summary>📋 Implementation Plan</summary>

[EMBED THE FULL IMPLEMENTATION PLAN CONTENT HERE]

</details>
```

**Important**: The `<details>` section embeds the implementation plan directly in the PR. This is the audit trail - after the PR merges, the plan file in `thoughts/shared/plans/` can be deleted.

### 7. Use the description (DO NOT COMMIT)

The PR description file is a **local working file** - do not commit it to git.

```bash
# Create or update the PR with the description
gh pr create --base main --body-file thoughts/shared/prs/<task-id>_description.md

# Or if PR already exists:
gh pr edit ${PR_NUMBER} --body-file thoughts/shared/prs/<task-id>_description.md
```

### 8. Present to user

```
I've generated the PR description at:
`thoughts/shared/prs/<task-id>_description.md`

**Verification Status:**
- ✅ Tests pass
- ✅ Type checking passes  
- ✅ Linting passes
- ⬜ Manual testing (please verify)

The implementation plan has been embedded in the PR description.

[If PR exists:]
The PR description has been updated. View at: [PR URL]

[If no PR yet:]
Create the PR with:
```bash
gh pr create --base main --body-file thoughts/shared/prs/<task-id>_description.md
```

**After PR merges**, you can delete the plan file:
```bash
rm thoughts/shared/plans/<component>/<plan-file>.md
git add -A && git commit -m "chore: cleanup plan after merge"
```
```

## Important Notes

- Focus on the "why" as much as the "what"
- Include breaking changes prominently
- If PR touches multiple components, organize the description accordingly
- Always attempt to run verification commands
- Be clear about which verification steps need manual testing
- **Embed the implementation plan** in a collapsible section - this is your audit trail
- **Do not commit** `thoughts/shared/prs/` - these are local working files
- **Plan files can be deleted** after the PR merges (the PR preserves the content)
