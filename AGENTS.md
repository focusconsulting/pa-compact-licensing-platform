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
- `just worker` — the Worker, which delivers events and sends email
- `just job <name>` — run one scheduled job once
- `just infra` / `just infra-down` — the local services: Postgres, maildev, RustFS, Cognito mock (resets data)
- `just up` (repo root) — the whole system locally, with no AWS account
- `just --list` — full recipe list

When iterating on the client, use these commands from
`engineering/client/`:

- `pnpm lint` / `pnpm exec tsc --noEmit` — lint and type check
- `pnpm test:coverage` — tests with coverage
- `pnpm dev` — Next.js dev server
- `pnpm storybook` — component catalogue

When iterating on the infrastructure, use these commands from
`engineering/infrastructure/`:

- `just check` — `tofu fmt -check` and `tofu validate`, with no AWS credentials
- `just plan <component> <env>` / `just apply <component> <env>` — against
  an environment (needs AWS credentials for its account)
- `just deploy <env>` — what a merge to `main` runs for `dev`: image, apply,
  client

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
| Parallel work | `/create_worktree` | |

When stuck: re-read this file and the constitution, look for an
existing implementation to follow, and ask rather than guess.

## Issue tracking in Jira

All work is tracked in the Jira project **SCRUM** at
<https://focusdigital.atlassian.net/browse/SCRUM>. Do not keep markdown
TODO lists or a second tracker.

- The ticket key (for example `SCRUM-78`) is the `<task-id>` in branch
  names, plan and handoff filenames, commit messages, and PR titles.
- Write tickets with the
  [Jira ticket template](product/backlog/jira-ticket-template.md): every
  ticket has a summary and acceptance criteria, and links the flows and
  rules it encodes.
- Epics hold tasks. Each epic starts with a product step (`.0`) and a
  contract step (`.1`); its other tasks build against the contract.
- Link tickets instead of describing order in prose: **Blocks** for
  "builds on", **Relates** for work found while doing another ticket,
  **Duplicate** when one ticket absorbs another.
- Statuses: To Do → In Progress → In Review → Done. Move the ticket to In
  Progress when you start it and In Review when its PR opens; it is Done
  when the PR merges.
- Agents read and write tickets with the Atlassian MCP tools
  (`searchJiraIssuesUsingJql`, `getJiraIssue`, `createJiraIssue`,
  `editJiraIssue`, `transitionJiraIssue`, `createIssueLink`,
  `addCommentToJiraIssue`). If they are not connected, ask the user to
  run `/mcp` and connect Atlassian.
- Use only labels that already exist in SCRUM; ask before adding one.

## Session completion

Before ending a work session:

1. Create Jira tickets for any follow-up work, linked to the ticket that
   found it.
2. Run the quality gates for every component you changed.
3. Update ticket status: close finished work and note where in-progress
   work stands.
4. Push the branch:

   ```bash
   git pull --rebase
   git push
   git status  # must show "up to date with origin"
   ```

5. Clear stashes and prune merged branches.
6. Use `/create_handoff` if work is still in progress.

Work is not complete until `git push` succeeds. If it fails, resolve and
retry.
