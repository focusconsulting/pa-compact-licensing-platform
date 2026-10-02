---
artifact: design-index
status: draft
authored-by: Service Designer (Moe)
last-revised: 2026-10-02
see-also: [ui-workflow.md, figma-working-guide.md, parts-crosswalk.md, ../flows/README.md, ../reference/compactconnect-crosswalk.md]
---

# Design: how the MVP's screens get made

This folder explains how screens are designed for the PA Compact Data System MVP. It sits under the flows (`../flows/`, FLOW-01..07) and the CompactConnect crosswalk (`../reference/compactconnect-crosswalk.md`): those say *what* happens and which rule forces it, and this folder says *how* it becomes screens engineering can build.

| File | Read it for |
|---|---|
| `README.md` (this file) | Why we work this way, the pieces, where each stands, what's next |
| `ui-workflow.md` | The steps, inside the story → spec path, with owners and gates |
| `figma-working-guide.md` | How to work in the Figma files, for people and for Claude |
| `parts-crosswalk.md` | Which Figma part matches which Trussworks part and which of our components |
| `samples/` | Pictures of the FLOW-02 sample (screens, SBB board, START HERE), exported from Figma 2026-10-02 |
| `uswds-3.13-theme-colors.json` | The 57 USWDS 3.13.0 theme colors the Figma screens are set to (provenance) |

## Why this approach

**The team.** There is no dedicated UX resource. Draft screens come from the Service Designer and the PM with AI help (Jira SCRUM-35). The approach has to work without a UI specialist and without a second copy of the design system to maintain.

**The design system already exists.** The app is built on USWDS through `@trussworks/react-uswds` (^11.0.1, on `@uswds/uswds` 3.13.0). The parts, their accessibility and their look are already decided. Design work is upstream (flows, content, states) plus recorded departures from USWDS.

**The model we follow.** The New York State Design System (Jesse Gardner, NYS ITS) runs a design system for 45+ agencies with AI in the loop. Four parts, checked in their public repo `ITS-HCD/nysds` on 2026-10-01:

1. **Figma parts mirror the code parts one to one**, so a drawing is a preview of the build.
2. **Every part has written rules**: what it's for, when to use something else, the accessibility rule.
3. **An AI lookup tool serves those rules**, so AI builds from approved parts instead of guessing. Their own warning: the output is only as good as the part docs.
4. **Branding later with one switch** ("Fidelity Modes"), with people reviewing every screen. Gardner: when AI produces more than people can review, "'human in the loop' becomes a rubber stamp" (plasticmind.com, 2026-03-17).

Colorado's design system (`coloradodigitalservice/colorado-design-system`) takes the same line: code and tokens in Git are the source of truth, and Figma is for display.

## The loop: five jobs

| Job | What does it | Status (2026-10-02) |
|---|---|---|
| **1. Codebook**: rules for each part | A short entry per component: purpose, when not to use it, accessibility rule, example. Written into the component's code comments and its Figma description | Not started. Writing work for the Service Designer; engineering wires it in |
| **2. Lookup**: AI reads the codebook | `focus-digital/react-uswds-mcp` (Anteneh, v0.1.0, 2025-12-16), strengthened to read our components and the codebook. Later, Storybook's own MCP add-on | Proposed. The Storybook add-on needs Storybook 10.6; the repo is on 8.6 |
| **3. Make**: screens | Figma: the Parts Library; screens in USWDS default colours with status tags (Draft, In review, Agreed). Optional code route: Story UI (Southleft), which writes Storybook stories from our parts and renders each to check it | Parts Library built. Story UI needs an Anthropic API key (Jamie or Phedra decide) |
| **4. Check (automated)** | `@storybook/addon-a11y@8.6.18` on every story; Figma accessibility checks; `ux-critique`, `plain-copy`; vetted USWDS/GSA accessibility skills | Add-on not installed yet. Skills vetted and staged, not installed |
| **5. Review (people)** | Designer and PM review every AI-drafted screen; manual keyboard and screen-reader checks on the highest-priority flows | Defined in `ui-workflow.md` |

## What's built (2026-10-02)

- **Figma "PA Compact Parts Library"**: the official USWDS Design Kit (Beta 0.3, 73 component sets) in the Focus team. It is set to USWDS 3.13.0 (branding to follow after Q9). Each part's description names its Trussworks and repo match. Details in `figma-working-guide.md`.
- **Parts crosswalk**: `parts-crosswalk.md`.
- **The worked example**: the Parts Library page "🧪 DRAFT SAMPLE (not representative): FLOW-02 workflow example", with START HERE, the Source → Build → Break board and two screens (pictures in `samples/`). Screen 2 also has reference code in `samples/code/`.
- **Journey maps file**: "PA Compact Journey Maps & Workflows" (empty scaffold, Focus team).

## What's next

1. A one-page `product/product-constitution.md`, so the design-rigor check runs fully.
2. The first stories and specs for the Sprint Zero work items, with draft-look screens drawn from FLOW-01..07.
3. Codebook entries for the components those screens use.
4. Engineering, if agreed: the Storybook accessibility add-on, and the strengthened lookup tool.
5. Error parts (`ErrorMessage`, `ValidationChecklist`) drawn in Figma with the first form.

## Who does what

| Role | Part |
|---|---|
| Service Designer (Moe) | Flows to specs, codebook writing, review, client walkthroughs, design decision records |
| PM (Nebi) | Stories, sprint selection, review, acceptance before demos |
| Claude (on either account) | Drafts screens in Figma from the Parts Library, runs the checks, keeps the crosswalk current. Follows `figma-working-guide.md` |
| Engineering | Builds from the same parts, wires the codebook and checks, owns the lookup tool |
| Light UI reviewer (to be named) | Visual check when screens are promoted; screen-reader testing |

## Open questions

- Will pilot states record decisions on our screens (FLOW-02 assumes yes) or from their own licensing systems?
- Does a non-federal Commission show the USWDS federal banner and identifier? (Confluence Q9, brand)
- Who is the light UI reviewer?
