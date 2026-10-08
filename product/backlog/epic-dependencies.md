# Epic Dependencies

What blocks what among the fourteen epics in [`mvp-jira-tickets.md`](mvp-jira-tickets.md), from each engineering ticket's **Blocked by** line. The ticket text governs; this diagram is a view of it.

```mermaid
flowchart LR
    E1["1 · Repo foundation, local stack, CI gates<br/>Sprint 1"]
    E2["2 · Backend platform<br/>data model, events, API guardrails,<br/>notifications, documents, worker, seed<br/>Sprints 1–2"]
    E3["3 · Environments, deploy pipeline,<br/>infrastructure security<br/>Sprints 1–2"]
    E4["4 · Design system and app shell<br/>Sprint 2"]
    E5["5 · Authentication, roles, accounts<br/>Sprint 3"]
    E6["6 · Participation application (PA side)<br/>Sprint 4"]
    E7["7 · License records and SQL review<br/>Sprints 3–4"]
    E8["8 · Privilege, payment, remote-state issuance<br/>Sprint 5"]
    E9["9 · Status changes, adverse actions,<br/>expiry, renewal<br/>Sprint 6"]
    E10["10 · Practitioner records, Commission<br/>dashboard, reports<br/>Sprints 5–6"]
    E11["11 · Public privilege verification<br/>Sprint 6"]
    E12["12 · Pilot readiness: accessibility, security,<br/>documentation, live operations test<br/>Sprints 6–8"]
    E13["13 · State licensee data ingestion<br/>Sprints 4–5"]
    E14["14 · NCCPA integration<br/>Sprint 6"]

    %% Critical path to "privilege issued end to end" (Sprint 5 milestone)
    E1 ==> E2
    E2 ==> E5
    E4 ==> E5
    E5 ==> E6
    E6 ==> E7
    E7 ==> E8
    E8 ==> E12

    %% Hard dependencies: "Blocked by"
    E1 --> E3
    E1 --> E4
    E5 --> E7
    E7 --> E9
    E5 --> E10
    E2 --> E11
    E4 --> E11
    E7 --> E13
    E5 --> E14
    E3 --> E12
    E9 --> E12
    E10 --> E12
    E11 --> E12
    E13 --> E12
    E14 --> E12

    %% Partial: builds on the demo seed or starts early, integrates when the dependency lands
    E8 -.->|renewal| E9
    E7 -.->|integrates| E10
    E8 -.->|integrates| E10
    E9 -.->|adverse-action section| E10
    E8 -.->|real data| E11
    E7 -.->|SQL case view| E14

    classDef techLead fill:#dbe9f6,stroke:#1a4480,color:#1b1b1b
    classDef fullstack fill:#e3f1df,stroke:#2e6b30,color:#1b1b1b
    classDef shared fill:#f0f0f0,stroke:#565c65,color:#1b1b1b
    class E1,E2,E7,E9,E10,E13 techLead
    class E3,E4,E5,E6,E8,E11,E14 fullstack
    class E12 shared
```

## Reading it

| Mark | Meaning |
|---|---|
| Thick arrow | The critical path to the Sprint 5 milestone, a privilege issued end to end in production on test data |
| Solid arrow | **Blocked by**: the epic cannot start, or a named part of it cannot start, until the other merges |
| Dotted arrow | The epic starts against the demo seed (epic 2) or its own stub, and integrates when the other lands |
| Blue | Tech lead: platform, and the state and Commission journey |
| Green | Fullstack engineer: the PA journey, the public site, and the design system |
| Grey | Both (epic 12 splits security and the live test from accessibility and documentation) |

## What the arrows leave out

- **Partial starts.** Epic 7's configuration and license records start in Sprint 3 on epic 5 alone; only its SQL review waits on epic 6. Epic 13 needs only epic 7's license-record half.
- **Epic 14 is blocked only by epic 5.** Its dotted arrow from epic 7 is the SQL case view it shows the NCCPA value on, which it consumes but does not wait for.
- **Consumes without blocking.** Every epic consumes epic 2's helpers and epic 4's primitives once they exist, and epic 11 uses epic 3's WAF rate limit. These are listed under **Consumes** in each ticket, not drawn.
- **The base data model.** F-02 (part of epic 2) lands every table the verticals share, so epics 6–14 can begin their data and API work as soon as it merges; see [`engineering/docs/data-model.md`](../../engineering/docs/data-model.md).
