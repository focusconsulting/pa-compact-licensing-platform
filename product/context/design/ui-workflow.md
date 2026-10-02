---
artifact: design-workflow
status: draft
authored-by: Service Designer (Moe)
last-revised: 2026-10-02
inputs: [Focus operating model (focus-pm, focus-designer, focus-engineer, focus-delivery plugins), product/context/flows/ FLOW-01..07, product/context/reference/compactconnect-crosswalk.md, product/backlog/mvp-ticket-breakdown.md v4.2]
see-also: [product/context/design/README.md, product/context/design/figma-working-guide.md, product/context/design/parts-crosswalk.md]
---

# UI workflow: from flows to screens to code

How a screen is made for the MVP, who does each step, and where the work lives. It sits downstream of the flows: a flow says what happens and which rule forces it; this file says how that becomes a screen engineering can build.

There is no dedicated UX resource (Jira SCRUM-35 plans for AI-assisted UX). The workflow is built so a service designer and a PM can produce draft screens with AI help, without a second copy of the design system to maintain.

## Principles

1. **The repo is the source of truth for parts.** Figma shows them; code defines them. If the two disagree, the code wins and Figma is fixed.
2. **Rules decide what a screen does; experience shapes how.** Every behaviour is tagged **rule-required** (with its citation, as in the flows) or **Focus preference** (with its reason). A preference presented as a rule is a defect.
3. **Follow CompactConnect by default** (`compactconnect-crosswalk.md`). Screens differ only where the crosswalk says Adapt, New or Deviate.
4. **Content before colour.** Screens use the USWDS default colours until branding is decided, and each screen's status tag (Draft, In review, Agreed) says how settled it is. The Commission reacts to content and order first. When branding is decided, the same screens switch to it without being redrawn.
5. **No rubber stamp.** Every AI-drafted screen gets a human review. If more are produced than can be reviewed, fewer are produced.

## Steps (inside the Focus operating model)

Screens are not a separate track. They are made inside the operating model's story → spec → plan path, using the Focus plugin commands. Figma is where a spec's screens are drawn; the spec is where they are decided.

| # | Stage | Command | Who | What the screens add | Gate |
|---|---|---|---|---|---|
| 1 | **Story** | `/draft-story` → `product/stories/<story-id>/story.md` | PM (Nebi) | Nothing yet. The story names the flow (FLOW-0x) and tickets it serves | `/story-completeness-check`; selected at `/run-sprint-planning` |
| 2 | **Spec** | `/draft-spec` → `product/stories/<story-id>/spec.md` | Designer (Moe); Claude drafts screens | Draft-look screens in Figma, one per step of the spec's **Flows**, covering every **Submission state**. The spec links the Figma frames by screen ID | `/spec-completeness-check` |
| 3 | **Design rigor** | `/spec-design-rigor-check` | Designer | The check accepts Figma references as design citations (its pass P5). Screens are checked for states, journey, accessibility and unresolved decisions | All 8 passes clean or with recorded deviations |
| 4 | **Spec review** | `/run-spec-review` (30 min) | Designer, PM, engineer | Reviewers walk the draft screens. Every behaviour is tagged rule-required (with citation) or Focus preference | Spec status `accepted` |
| 5 | **Client walkthrough** | none; feedback log in `product/context/design/feedback/` | Moe, Nebi, Jamie; arranged with Carl | The same draft screens, presented as backed preferences | Agreed, or back to stage 2 |
| 6 | **Mark agreed** | none; change the screen's status tag to AGREED in Figma | Claude, light UI reviewer | Same screens, no redrawing | Visual check, then the code check below if the screen already has code |
| 7 | **Design decisions** | `/author-design-adr` → the decision records folder (`category: design`; folder to confirm, see below) | Designer | Anything that isn't a standard part, or departs from USWDS | ADR accepted |
| 8 | **Build** | `/create-plan` or `/draft-plan`, then `/implement-plan` | Engineering | The spec names the parts used (see `parts-crosswalk.md`) | Storybook accessibility check passes (once Storybook builds again, SCRUM-24, and the add-on is installed) |
| 9 | **Close** | `/close-story` | PM, engineer | Screens updated if what shipped differs | Story `delivered` |

**Prerequisite the plugins expect:** `product/product-constitution.md` (outcomes, voice and interaction principles, compliance commitments). Without it, `/spec-design-rigor-check` runs in a degraded mode. Proposed: a one-page constitution, drafted by Moe, before the first spec.

## For engineers: from a Figma screen to Trussworks code

The Figma screen is a picture of what to build. The **spec** (`product/stories/<story-id>/spec.md`) is the instruction: behaviour, states and acceptance criteria. Read both.

1. **Open the screen from the spec.** The spec links each Figma frame by its screen ID. Look at the agreed screen.
2. **Find the code piece for each part.** Click a part in Figma. Its description, under "PA COMPACT CROSSWALK", names the Trussworks component and the repo wrapper to use (also in `parts-crosswalk.md`). Example: a text box → our `TextField` (Trussworks `TextInput` + `Label`).
3. **Build the page from those pieces only.**
   - Use our wrappers where they exist, otherwise the Trussworks component.
   - Don't add colours, fonts or spacing by hand. They come from `_uswds-theme.scss`, which the Figma screens already match. A page built from the right pieces looks like the drawing without styling work.
4. **Build every state the spec lists.** Empty, filled, error, waiting, done, denied: each drawn state is a separate Figma frame named with the screen ID plus the state.
5. **Add a Storybook story per state.** The story name includes the screen ID, so reviewers can match code to drawing.
6. **Run the checks:**
   - tests and `pre-commit`;
   - the Storybook accessibility check, once `@storybook/addon-a11y` is added (proposed);
   - a keyboard pass on any new form.
7. **Compare with the drawing.** Put the story and the agreed Figma frame side by side. Small differences in spacing are fine (the code is the authority). Different pieces, missing states or different wording are not.
8. **When something doesn't fit, stop and flag it. Don't invent.** If the drawing needs a piece Trussworks doesn't have, or the drawing and the spec disagree, raise it with the Designer. Any new part or departure from USWDS becomes a design decision record (via `/author-design-adr`) before it's built.
9. **Open the PR with the spec reference** (the repo's PR template requires it) and the screen IDs covered. `/close-story` reconciles what shipped with the spec and screens.

**Proven on the sample (2026-10-01; Screen 2 rebuilt the same day after review).** Screen 2 was written as React code straight from the Figma frame, using the crosswalk. The files are `samples/code/SqlCaseView.tsx` and its story. It passes `tsc` and ESLint, and it renders in the app (`samples/flow-02-scr-02-built-in-code.png`). Comparing it with the drawing (step 7) caught three things:

- the drawing used the wrong heading font. USWDS 3.13 headings are serif by default, so the drawing was fixed;
- the code ran a hint into its label (fixed to follow `TextField`);
- two buttons sat too tight (spacing fixed).

Moe's review then caught a design failure no check had found: the first Screen 2 was four tick boxes with nothing to check against. It was rebuilt so each check sits under the evidence it checks (the PA's answer beside the state's record), following FLOW-02's list of what staff see and the CompactConnect staff record capture. It also showed a drawing-versus-spec gap: the drawing had a checkbox for the background check, but FLOW-02 records a date. Moe's review settled it: the screen now asks for the date the check was finished, and never the results (Rule 4 §4.2(g)). The date is a Focus preference; the review itself is rule-required (Rule 3 §3.4(b)).

**Found while testing:** `pnpm build-storybook` fails on the repo as it stands (`SB_BUILDER-WEBPACK5_0002 … reading 'tap'`), with or without the sample. This is relevant to SCRUM-24.

The example to look at is the Parts Library page "🧪 DRAFT SAMPLE (not representative): FLOW-02 workflow example" (pictures in `samples/`). Screen 1 uses `Breadcrumb`, a heading, `Alert` (info, slim), `Table` and `Tag`. Screen 2 adds `Link`, `Alert` (warning), `Checkbox`, `Label` + `DatePicker`, `Label` + `Textarea`, `Button` (outline, and primary disabled) and `Radio`. All of them are in Trussworks 11. None is wrapped by a repo component yet, apart from what `FormStep` and the field wrappers already cover.

## Where the work lives

| What | Where |
|---|---|
| Stories and specs (where screens are decided) | `product/stories/<story-id>/story.md` and `spec.md` |
| Product constitution (principles the rigor check reads) | `product/product-constitution.md` (to be written) |
| Flows (what happens, which rule) | `product/context/flows/` (FLOW-01..07) |
| CompactConnect reference | `product/context/reference/compactconnect-crosswalk.md` and `compactconnect-screens/` |
| Parts Library (Figma) | "PA Compact Parts Library", Focus team. The official USWDS Design Kit (Beta 0.3), set to the USWDS 3.13.0 values our code uses: <https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9> |
| Which Figma part matches which code part | `product/context/design/parts-crosswalk.md` (also written into each part's description in Figma) |
| Journey maps | "PA Compact Journey Maps & Workflows", Focus team: <https://www.figma.com/design/rzT4ibs4oFCAVtXXVunK3F> |
| Wireframes | One Figma file per release, built from the Parts Library (created at step 2) |
| Feedback log | `product/context/design/feedback/<date>-<audience>.md`, keyed by screen ID |
| Design decisions | Decision records with `category: design`, written with `/author-design-adr`. Folder to confirm: the existing records are in `engineering/docs/architecture_decision_records/`, `AGENTS.md` says `thoughts/shared/adrs/`, and the Focus plugins expect `engineering/adrs/` |

## Status tags, not looks

There is one set of screens in the USWDS default colours (decided 2026-10-02, after trying three looks and then two). Each screen has a status tag beside its title: DRAFT, IN REVIEW or AGREED. When the Commission decides branding (Q9), the Parts Library gets a branded mode and the screens switch to it, with nothing redrawn.

## When code is checked against the drawing

Code is checked against a screen only when that screen is agreed. Draft screens change often, and checking code against each change would flag work nobody means to build yet.

1. **A screen is marked AGREED.** If code for it exists, compare every word, every part and every state on the screen with the code. Each difference goes to whoever owns that side, the drawing or the code.
2. **An agreed screen changes.** Its tag goes back to IN REVIEW, and any code for it counts as out of date until step 1 runs again.
3. **A PR builds a screen.** The engineer compares the code with the agreed screen before asking for review (step 7 of the engineer steps above).

An automatic check whenever Figma changes is possible, but it is not set up. It would need a Figma change notification, a repo check that reads the screen through the Figma API, and a Figma token stored as a secret. That is for engineering to decide.

## IDs

Screen IDs hang off the story so they line up with the spec that decides them: `<story-id>/SCR-<nn>`, for example `012-sql-verify/SCR-03`. A screen's Figma frame name, its spec reference, its review notes and its feedback log entries all use the same ID. The story names the flow (FLOW-0x) and the tickets (`L-03`, `P-01`) it serves.

## Figma and code without Code Connect

Focus is on the Figma Pro plan. Code Connect (which links a Figma part to its code automatically) needs Organization or Enterprise, so the link is kept by hand:

- Each Figma part's description names its Trussworks component and the repo wrapper that uses it.
- `parts-crosswalk.md` holds the full table.
- When a wrapper is added or changed in `engineering/client/src/components/`, the crosswalk is updated in the same PR.

## Known gaps (from the parts crosswalk)

- **Custom `Card`.** `Card.tsx` is a styled box, not the USWDS card. Keep it or switch? Needs a design decision record.
- **No step indicator.** `FormStep.tsx` does not use the USWDS step indicator. Showing progress would be a Focus preference, not rule-required.
- **Federal banner and identifier.** The Commission is not a federal agency. Whether these USWDS parts appear is open (with the brand question, Confluence Q9).
- **State staff decision screens.** FLOW-02 has SQL staff verify in the web app. The Trussworks `Table` is basic; any list beyond it is new design work and needs a design decision record.
- **Error parts.** `ErrorMessage` and `ValidationChecklist` exist in Trussworks but not in the Figma kit. They get drawn with the first form.

## Out of scope here

- Visual brand beyond USWDS defaults, until the Commission answers Q9.
- Screens for deferred flow parts (the "Deferred" headings in FLOW-04 and others).
