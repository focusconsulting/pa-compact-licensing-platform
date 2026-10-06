# Repository guidance

This is the single instruction file for AI coding agents in this repo.
`CLAUDE.md` imports it; edit this file, not that one.

## Engineering work

Before producing any technical plan, ADR, or code change under
`engineering/`, read
[`engineering/engineering-constitution.md`](engineering/engineering-constitution.md).
It is binding. Every PR is evaluated against it.

ADRs live in
[`engineering/adrs/`](engineering/adrs/)
— read those that relate to your change before designing.

Before changing code, read the existing code in that area and reuse its
patterns and utilities rather than adding new ones.

### Verification

First-time setup is in the root [`README.md`](README.md#getting-started):
copy each component's `.env.example`, start Docker, and run
`just infra` before the API or its tests.

When iterating on the API, use these commands from `engineering/api/`:

- `just lint` — ruff check, ruff format check, pyright
- `just format` / `just typecheck` / `just test` — individual stages
- `just test-coverage` — tests with branch coverage
- `just dev` — API with hot reload
- `just infra` / `just infra-down` — Postgres + Redis (resets data)
- `just --list` — full recipe list

When iterating on the client, use these commands from
`engineering/client/`:

- `pnpm lint` / `pnpm exec tsc --noEmit` — lint and type check
- `pnpm test:coverage` — tests with coverage
- `pnpm dev` — Next.js dev server
- `pnpm storybook` — component catalogue

Run the lint, type check, and coverage commands for every component you
changed before declaring a change complete. If a test fails, fix the
code, not the test, unless the test is wrong.

## Prose discipline

All prose — code comments, docstrings, ADRs, plans — follows the
"Prose earns its keep" principle in the constitution: say only what
the artifact itself cannot.

## Product work

For changes under `product/`, no engineering verification is required.
Run `pre-commit run --files <changed files>` so markdownlint passes.

## Workflow

### Git

- `main` is protected. Work on a branch named
  `feature/<task-id>-short-description` or `fix/<task-id>-short-description`,
  and check `git branch --show-current` before committing.
- One logical change per commit. Use the `/commit` skill.
- Never add co-author information or Claude attribution to commits or
  PRs.
- Never force-push a shared branch.
- Never use `git commit --no-verify`. If a hook fails, fix the cause, or
  change the hook config with the team's approval.

### Pull requests

1. Run the verification commands above for every component you changed.
2. Generate the description with `/describe_pr`; it embeds the plan.
3. Push and open the PR against `main`:
   `gh pr create --base main --body-file engineering/thoughts/shared/prs/<task-id>_description.md`.
4. A PR needs review before it merges.
5. After it merges, run `/cleanup <task-id>` to delete its plan and
   handoff files.

### Plans, handoffs, and research

Working documents live in `engineering/thoughts/shared/`:

| Document | Location | Keep |
|---|---|---|
| ADRs | `engineering/adrs/` | Forever |
| Plans | `engineering/thoughts/shared/plans/` | Until the PR merges (the PR embeds it) |
| Handoffs | `engineering/thoughts/shared/handoffs/` | Until the task closes |
| PR descriptions | `engineering/thoughts/shared/prs/` | Never committed |
| Research | `engineering/thoughts/shared/research/` | If reusable |

Use `/create_plan` for work that spans sessions, and `/implement_plan`
when a plan exists. Use `/create_handoff` before ending a session with
work in progress, and `/resume_handoff` to pick it up.

### Agents and skills

Prefer the project's own tools:

| Task | Use | Avoid |
|---|---|---|
| Find files or components | `codebase-locator` | generic `Explore` |
| Understand an implementation | `codebase-analyzer` | |
| Find a pattern to copy | `codebase-pattern-finder` | |
| Research and notes | `research_codebase`, `thoughts-locator` | |
| Planning | `/create_plan` | `EnterPlanMode` (ephemeral) |
| Committing and PRs | `/commit`, `/describe_pr` | |
| Parallel work | `/create_worktree` (use `BEADS_NO_DAEMON=1` in worktrees) | |

When stuck: re-read this file and the constitution, look for an
existing implementation to follow, and ask rather than guess.

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
