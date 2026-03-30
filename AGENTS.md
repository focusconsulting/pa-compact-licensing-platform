# AGENTS.md - Project Golden Rules

## About This File

This file contains rules that are injected into every AI coding session. Keep it focused on your "golden rules" - what should ALWAYS be done and what should NEVER be done.

> ⚠️ **Remember**: The longer this file, the less likely AI will follow everything. Be selective and prioritize.

---

## 🚫 NEVER Do (Hard Rules)

### Security

- Never put API keys, secrets, or credentials in code or version control
- Never use wildcard imports in production code
- Never disable security features without explicit approval
- Never commit sensitive data even in comments

### Code Quality

- Never use global variables
- Never leave debug/print statements in committed code
- Never catch exceptions and ignore them silently
- Never commit code with TODO comments that reference security issues

### Process

- Never add co-author information or Claude attribution
- Never commit directly to main/master branch
- Never force push to shared branches
- Never delete tests to make the build pass
- Never skip running the test suite

---

## ✅ ALWAYS Do (Mandatory Practices)

### Before Coding

- Always read existing code in the area you're modifying
- Always check for existing utilities before writing new ones
- Always understand the existing patterns in the codebase

### During Coding

- Always use the project's established patterns and conventions
- Always handle errors explicitly (no silent failures)
- Always use meaningful variable and function names
- Always write self-documenting code (comments for "why", not "what")

### After Coding

- Always run the full test suite before claiming success
- Always verify your changes work as expected
- Always clean up temporary files and debug code
- Always update documentation if behavior changes

---

## 📋 Project-Specific Conventions

### Language/Framework Rules
<!-- Python 3.12+ -->
- Avoid using `# type: ignore` if you must, leave comment as to why
- Prefer `Type | None` over `Optional[Type]`
- Use async/await for I/O operations
- Prefer `asyncio.gather` for concurrent operations
- Use `scoped_session[Session]` for web request contexts
- Prefer ORM queries over raw SQL
- Do not use explicit transactions (handled by context generators)
- Use `model_dump()` over `.dict()` for Pydantic models
- Prefer strict validation in Pydantic models
- Use specific exception types, not bare `Exception`
- Log errors before re-raising

### Monorepo Structure

This is a monorepo with the following components:

```text
api/              - Python API (Connexion/Flask)
client/           - Next.js frontend (React/TypeScript)
iac/              - Infrastructure as Code
```

### File Organization
<!-- api/licensing_api structure -->
- SQLAlchemy models go in `licensing_api/models/`
- API controllers go in `licensing_api/controllers/`
- Shared utilities go in `licensing_api/utils/`
- Database config and migrations go in `licensing_api/db/`
- Cache layer goes in `licensing_api/cache/`
- Tests mirror source structure in `api/tests/` (e.g., `api/tests/controllers/`)

### Naming Conventions

- Modules: `snake_case.py` (e.g., `license_validation.py`)
- Classes: `PascalCase` (e.g., `License`, `LicenseApplication`)
- Functions/variables: `snake_case` (e.g., `get_license_by_id`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `LICENSE_CACHE_PREFIX`)
- Test files: `test_*.py` (e.g., `test_license_validation.py`)
- Test classes: `Test*` (e.g., `TestGetLicenseById`)

### Testing Requirements

- Use pytest with class-based test organization
- Use fixtures from `api/tests/conftest.py` for database sessions and mocks
- Mock external dependencies (Redis, AWS)
- Use `testcontainers` for Postgres/Redis integration tests, `freezegun` for time-dependent tests
- Test classes: `class TestFunctionName:` with methods `def test_behavior:`
- **100% code coverage is required**
- Prefer comprehensive integration tests over small unit tests

---

## 🔧 Environment & Tools

### Python Environment

This project uses a Python virtual environment. **Always activate it before running Python commands.**

```bash
# Activate virtual environment (do this before any Python/pip/pytest commands)
source api/.venv/bin/activate
```

### Build Commands

Each component has its own tooling. Use `just` from within the `api/` directory:

```bash
# API (from api/ directory)
just install          # Install dependencies (uv sync)
just dev              # Run API with hot reload
just test             # Run tests
just test-coverage    # Run tests with coverage
just lint             # Run all linting (spectral + ruff + pyright)
just format           # Format code

# Client (from client/ directory)
pnpm install          # Install dependencies
pnpm dev              # Run dev server
pnpm test             # Run tests (vitest)
pnpm lint             # Lint
pnpm storybook        # Run Storybook
```

### Key Files to Know

```text
# API
- api/pyproject.toml              - Python dependencies and project config
- api/openapi.yaml                - OpenAPI spec (Connexion routes)
- api/justfile                    - Task runner commands
- api/licensing_api/app.py        - Flask/Connexion app factory
- api/licensing_api/__main__.py   - ASGI entry point
- api/tests/conftest.py           - Shared test fixtures

# Client
- client/package.json             - Node dependencies
- client/src/app/                 - Next.js pages
- client/src/components/          - React components
```

---

## ⚡ Quick Reference

### When You Get Stuck

1. Re-read this file
2. Check existing implementations for patterns
3. Ask for clarification rather than guessing
4. If unsure, implement the simplest solution first

### When Making Changes

1. Small, focused changes
2. One logical change per commit
3. Test before and after
4. Verify nothing else broke

### When Tests Fail

1. Don't disable or delete the test
2. Understand why it's failing
3. Fix the code, not the test (unless test is wrong)
4. Run full suite after fix

---

## Branch Workflow

**Main branch is protected.** All work must be done on feature branches.

### Starting Work on a Task

```bash
# 1. Claim the task in beads
bd update <task-id> --status in_progress

# 2. Create feature branch
git checkout -b feature/<task-id>-short-description

# Examples:
git checkout -b feature/bd-f7a3-integration-tests
git checkout -b feature/issue-42-test-coverage
```

### Branch Naming Convention

- `feature/<task-id>-description` for features
- `fix/<task-id>-description` for bugs

### Before Any Commits

Always verify you're on the correct branch:

```bash
git branch --show-current  # Should NOT be 'main'
```

## PR Workflow

1. Create feature branch (or use worktree)
2. Make changes and commit
3. Run component-specific tests
4. Run `/describe_pr` to generate description (embeds plan in PR)
5. Create PR: `gh pr create --base main --body-file thoughts/shared/prs/<task-id>_description.md`
6. PRs require review before merge to main
7. After merge: Run `/cleanup <task-id>` to delete plan files

---

## Document Retention Policy

| Document Type | Location | Retention |
|---------------|----------|-----------|
| **ADRs** | `thoughts/shared/adrs/` | **Forever** - architectural decisions |
| **Plans** | `thoughts/shared/plans/` | Delete after PR merges (embedded in PR) |
| **Handoffs** | `thoughts/shared/handoffs/` | Delete after task closes |
| **PR Descriptions** | `thoughts/shared/prs/` | Never commit (local working files) |
| **Research** | `thoughts/shared/research/` | Keep if reusable, delete if one-off |

**Why this works:**

- ADRs document *why* decisions were made - permanent reference value
- Plans document *how* to implement - preserved in PR description, then deletable
- Handoffs bridge sessions - no value after task completion
- PR descriptions are working files - the PR itself is the record


---

## Available Commands

| Command | Purpose |
|---------|---------|
| `/create_plan` | Create implementation plan (asks for component) |
| `/implement_plan` | Execute a plan |
| `/iterate_plan` | Update existing plan |
| `/validate_plan` | Verify implementation |
| `/create_adr` | Document architectural decision |
| `/create_handoff` | Save session state |
| `/resume_handoff` | Continue from handoff |
| `/describe_pr` | Generate PR description (embeds plan) |
| `/commit` | Create git commits |
| `/research_codebase` | Document codebase |
| `/create_worktree` | Create parallel worktree |
| `/beads_workflow` | Beads quick reference |

---

## Task Tracking with Beads

This project uses `bd` (beads) for task tracking. At session start:

1. Check for ready work: `bd ready`
2. Pick a task or create one: `bd create "Task title" -t task -p 2`
3. Update status when starting: `bd update <id> --status in_progress`
4. Close when done: `bd close <id> --reason "Completed in PR #X"`
5. Sync changes: `bd sync`

## Parallel Development

For complex features, use git worktrees:

1. Create worktree: `/create_worktree` command
2. Each worktree is isolated with its own venv
3. Worktrees share the beads database
4. Use `BEADS_NO_DAEMON=1` in worktrees

## Plans and Handoffs

- Implementation plans: `thoughts/shared/plans/`
- Session handoffs: `thoughts/shared/handoffs/`
- Research docs: `thoughts/shared/research/`

Use `/create_plan` for complex features requiring multiple sessions.
Use `/create_handoff` before ending a session with work in progress.

## PR Workflow

1. Create feature branch (see Branch Workflow above)
2. Make changes and commit to feature branch
3. Run `/describe_pr` to generate PR description
4. Push and create PR:

   ```bash
   git push -u origin feature/<branch-name>
   gh pr create --base main
   ```

5. PRs require review before merge to main

---

## Agent & Skill Preferences

When exploring or planning, prefer project-specific tools over generic ones:

### For Codebase Exploration

- **Prefer**: `codebase-locator` to find files/components by description
- **Prefer**: `codebase-analyzer` for deep implementation analysis
- **Prefer**: `codebase-pattern-finder` to find examples to model after
- **Avoid**: Generic `Explore` agent unless the above don't fit

### For Research

- **Prefer**: `research_codebase` skill to document findings in `thoughts/`
- **Prefer**: `thoughts-locator` to find existing research/notes

### For Planning

- **Prefer**: `/create_plan` skill (saves to `thoughts/shared/plans/`)
- **Avoid**: `EnterPlanMode` tool (saves to `.claude/plans/`, ephemeral)

### For GIT and finishing work

- **Prefer**: `/commit` and `/describe_pr` skills

### For Implementation

- **MUST USE**: `/implement_plan` skill when a plan exists in `thoughts/shared/plans/`

---

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:

   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```

5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

*Last updated: 3/21/2026*
*Version: 1.2*

<!-- BEGIN BEADS INTEGRATION v:1 profile:full hash:f65d5d33 -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Quality
- Use `--acceptance` and `--design` fields when creating issues
- Use `--validate` to check description completeness

### Lifecycle
- `bd defer <id>` / `bd supersede <id>` for issue management
- `bd stale` / `bd orphans` / `bd lint` for hygiene
- `bd human <id>` to flag for human decisions
- `bd formula list` / `bd mol pour <name>` for structured workflows

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
