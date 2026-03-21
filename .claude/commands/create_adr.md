---
description: Create an Architecture Decision Record (ADR) to document significant technical decisions
---

# Create ADR

You are tasked with creating an Architecture Decision Record (ADR) to document a significant technical decision. ADRs capture the context, options considered, and rationale for architectural choices.

## When to Create an ADR

ADRs should be created for decisions that:
- Affect the overall system architecture
- Introduce new patterns or conventions
- Add significant dependencies
- Change how components interact
- Have long-term implications that future developers need to understand
- Were contentious or required significant discussion

## Initial Response

When this command is invoked:

1. **If context/decision was provided** (e.g., `/create_adr use SQLAlchemy for ORM`):
   - Acknowledge the decision topic
   - Ask clarifying questions if needed
   - Proceed to research and drafting

2. **If no parameters provided**:
   ```
   I'll help you create an Architecture Decision Record.

   What decision do you need to document? Please describe:
   1. The decision or choice that was made
   2. Brief context on why this decision was needed

   Example: "We decided to use SQLAlchemy instead of raw SQL for database access"
   ```

## Process Steps

### Step 1: Determine ADR Number

```bash
# Find the next ADR number
ls docs/architecture_decision_records/ | grep -E '^[0-9]{4}-' | sort -r | head -1

# If no ADRs exist, start with 0001
# Otherwise, increment the highest number
```

### Step 2: Gather Context

If the decision came from a planning session or has related context:

1. **Check for related documents**:
   - Recent plans in `thoughts/shared/plans/`
   - Research in `thoughts/shared/research/`
   - Related beads tasks: `bd list`

2. **Research the codebase** if needed:
   - Use **codebase-locator** to find affected areas
   - Use **codebase-analyzer** to understand current patterns

3. **Ask clarifying questions** about:
   - What problem prompted this decision?
   - What options were considered?
   - What were the key factors in choosing this option?
   - What are the expected consequences?

### Step 3: Draft the ADR

Create the file at: `docs/architecture_decision_records/NNNN-short-title.md`

Where:
- `NNNN` is the zero-padded number (0001, 0002, etc.)
- `short-title` is a kebab-case description

Examples:
- `0001-use-fastapi-framework.md`
- `0002-adopt-repository-pattern.md`
- `0003-terraform-for-infrastructure.md`

Use the template from `docs/architecture_decision_records/0000-adr-template.md`:

```markdown
# ADR-NNNN: [Short Title]

## Status

Accepted

## Date

[Today's date: YYYY-MM-DD]

## Context

[Describe the situation and problem. Be specific about:
- What triggered the need for this decision
- Technical constraints
- Business requirements
- Team considerations]

## Decision Drivers

- [Key factor 1]
- [Key factor 2]
- [Key factor 3]

## Considered Options

### Option 1: [Name]

[Description]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

### Option 2: [Name]

[Description]

**Pros:**
- [Pro 1]

**Cons:**
- [Con 1]

## Decision

**Chosen option:** [Option N], because [clear reasoning].

[Elaborate on the decision rationale. Connect back to the decision drivers.]

## Consequences

### Positive

- [Benefit 1]
- [Benefit 2]

### Negative

- [Drawback 1] — Mitigation: [how we'll handle it]
- [Drawback 2] — Mitigation: [how we'll handle it]

## Related

- GitHub Issue: #XXX (if applicable)
- Beads Task: bd-XXXX (if applicable)
- Implementation Plan: `thoughts/shared/plans/YYYY-MM-DD-xxx.md` (if applicable)

## Notes

[Additional context, links, or references]
```

### Step 4: Review with User

Present the draft:

```
I've drafted ADR-NNNN: [Title]

**Summary:**
- Decision: [one-line summary]
- Key driver: [main reason]
- Trade-off accepted: [main downside and mitigation]

Please review the full ADR at `docs/architecture_decision_records/NNNN-title.md`.

Would you like me to adjust anything before we finalize it?
```

### Step 5: Commit the ADR

```bash
git add docs/architecture_decision_records/
git commit -m "docs(adr): ADR-NNNN [short title]

[One-line summary of the decision]"
```

### Step 6: Link Related Items

If there's a related beads task or plan:

```bash
# Add comment to related beads task
bd comment <id> "ADR-NNNN documents the architectural decision: docs/architecture_decision_records/NNNN-title.md"
```

If created during `/create_plan`, remind the user to reference the ADR in the plan.

## Guidelines

### Good ADR Characteristics

- **Concise but complete** — Include enough context for someone unfamiliar with the discussion
- **Honest about trade-offs** — Document the downsides of the chosen option
- **Forward-looking** — Note consequences that will affect future work
- **Well-linked** — Reference related documents, issues, and code

### What Makes a Decision "Architectural"

Consider documenting decisions about:
- **Technology choices**: Frameworks, libraries, databases
- **Patterns**: Repository pattern, event sourcing, CQRS
- **Structure**: Module organization, API design, data models
- **Integration**: How systems communicate, authentication approaches
- **Conventions**: Coding standards, naming conventions, error handling

### What NOT to Document as ADRs

- Implementation details that don't affect the broader system
- Temporary workarounds (unless they become permanent)
- Decisions that can be easily reversed without impact
- Bug fixes or minor refactoring choices

## Updating ADRs

ADRs are immutable records of decisions at a point in time. If a decision changes:

1. **Don't modify the original ADR** (except to update Status)
2. **Create a new ADR** that supersedes the old one
3. **Update the old ADR's status** to "Superseded by ADR-XXXX"

```markdown
## Status

Superseded by [ADR-0015](0015-switch-to-different-orm.md)
```

## Integration with Other Commands

### From `/create_plan`

When `/create_plan` identifies an architectural decision:
```
This plan involves an architectural decision about [topic].

I recommend creating ADR-NNNN to document why we chose [approach].
Shall I create the ADR now?
```

### From `/research_codebase`

When research reveals undocumented architectural decisions:
```
I found an undocumented architectural pattern: [pattern].

Consider creating an ADR to document why this approach was chosen.
```
