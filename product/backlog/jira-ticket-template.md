# Jira ticket template

How to write a ticket in the SCRUM project
(<https://focusdigital.atlassian.net/browse/SCRUM>). Every epic and task
follows this shape so a reader finds the same things in the same place.
[`mvp-jira-tickets.md`](mvp-jira-tickets.md) and
[`engineering-tickets-at-a-glance.md`](engineering-tickets-at-a-glance.md)
hold the content the epics are written from.

## Fields

| Field | Epic | Task |
|---|---|---|
| Issue type | Epic | Task. SCRUM has no Bug type: a bug is a Task with the `security` or area label. |
| Summary | `Epic N · <name>` | An imperative phrase: "Build the app shell". The first two tasks end in `(epic N product step)` and `(epic N contract step)`. |
| Parent | — | The epic. A one-off ticket has no parent. |
| Priority | High for MVP scope; Medium for work the Commission may trade (epics 13, 14, renewal); Low for blocked or polish work. | Same as its epic unless the backlog says otherwise. |
| Labels | Two to four existing labels for the epic's area. | Two or three existing labels for the task's area. |
| Assignee | The owner, or empty. | The person doing it, or empty until someone starts it. |
| Status | To Do → In Progress → In Review → Done. | Same. In Review once its PR opens; Done when the PR merges. |
| Links | — | See [Links](#links). |

Use existing labels only; ask before adding one. The ones in use:
`acceptance`, `accessibility`, `ai-assisted-design`, `api`, `backlog`,
`ci`, `client`, `client-dependency`, `compliance`, `data`, `database`,
`delivery`, `devops`, `dx`, `handoff`, `infra`, `infrastructure`,
`ingestion`, `integrations`, `jira-setup`, `payments`, `pilot-scope`,
`qa-acceptance`, `refinement`, `research`, `security`, `sow`, `ux`,
`working-agreement`.

## Links

| Link type | Use it when |
|---|---|
| Blocks | This ticket must land before the other can start ("builds on"). Cross-epic blocks are fine. |
| Relates | The ticket was found while working on another, or the two touch the same thing. |
| Duplicate | One ticket absorbed another; close the absorbed one as Done. |

## Epic description

```markdown
## Summary

<What the epic delivers, in one or two sentences.>

## User story

As <a PA | state staff | the Commission | an engineer>, I want <capability>,
so that <outcome>.

## Tasks

<Which task to start with and the order of the rest, by task number
(.0 product step, .1 contract step, then .2 onwards).>

**When.** <Sprint(s), and which epics it waits on.>

## Acceptance criteria

- <Observable, testable outcome.>
- <Keep any "⚠ Under review" note from the backlog on the line it qualifies.>

## Flows and rules

**Flows.** [FLOW-0N <name>](<link>) · … (or "None directly.")

**Rules and references.** [Rule N §N.N <name>](<link>) · [SOW](<link>) · …

Full card: [Engineering tickets at a glance](<link>)

---

Source: [MVP epics and tickets](<link>) (epic N) · [MVP ticket breakdown](<link>)
```

## Task description

```markdown
## Summary

<What the task builds or decides.>

**Why.** <The reason it matters, usually the rule, contract, or dependent epic.>

## Includes

- <Scope item.>

**Builds on.** <The tickets it needs first, by task number or SCRUM key.
"Nothing" for a first step.>

## Acceptance criteria

- <Observable, testable outcome.>

## Flows and rules

**Flows.** [FLOW-0N <name>](<link>) · …

**Rules and references.** [Rule N §N.N <name>](<link>) · …

## Design notes

<Optional: implementation decisions already made.>

## Notes

<Optional: PRs, branches, and status that matter to whoever picks it up.>

---

Source: [MVP epics and tickets](<link>) (epic N) · [MVP ticket breakdown](<link>)
```

Leave out a section that would be empty, except Summary and Acceptance
criteria, which every ticket has. A one-off ticket ends with
"Found while … (SCRUM-N)." in place of the Source line.

### The two first steps of every epic

- **Product step (`.0`).** Includes lists the "Clarify" questions and the
  wireframes. Acceptance criteria: every question is answered by the
  Commission or logged in the assumptions log with its default and the
  date sent; the wireframes are attached to the tasks that build the
  screens.
- **Contract step (`.1`).** Includes lists the names, shapes, and events
  the other tasks build against. Acceptance criteria: they are committed
  and documented, and the epic's tasks build against them.

## Reference links

Link to `main` on GitHub so the link works from Jira:
`https://github.com/focusconsulting/pa-compact-licensing-platform/blob/main/<path>`.

| Reference | Path |
|---|---|
| Flows FLOW-01 to FLOW-07 | `product/context/flows/` |
| Rule 3 (compact privilege) | `product/context/research-corpus/sources/rule-3-compact-privilege.md` |
| Rule 4 (data system, confidentiality) | `product/context/research-corpus/sources/rule-4-compact-data-system--confidentiality-information-sharing.md` |
| SOW (redline response v2) | `product/context/PA Compact Data System SOW - Focus Consulting.md` |
| Engineering constitution | `engineering/engineering-constitution.md` |
| CompactConnect crosswalk | `product/context/reference/compactconnect-crosswalk.md` |
| Tensions | `product/context/evidence/tensions/` |

Confluence pages that tickets cite:
[License data: what Rule 4.3(c) asks for](https://focusdigital.atlassian.net/wiki/spaces/PC/pages/71663618)
and
[Q17 Rules status and rules contact](https://focusdigital.atlassian.net/wiki/spaces/PC/pages/63504406).
