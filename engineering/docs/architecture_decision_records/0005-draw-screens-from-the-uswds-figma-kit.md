---
adr-id: 0005
category: design
status: proposed
title: Draw screens in Figma from the official USWDS kit, matched part by part to the code
authored-by: Designer (Moe)
reviewed-by: PM (Nebi), Product Engineer (Kalish)
decision-date: 2026-10-02
supersedes: none
superseded-by: none
---

<!-- markdownlint-disable-next-line MD025 -->
# ADR-0005: Draw screens in Figma from the official USWDS kit, matched part by part to the code

## Context

The app is built from the U.S. Web Design System (USWDS), through the Trussworks React library (`@trussworks/react-uswds` ^11.0.1 on `@uswds/uswds` 3.13.0). USWDS already fixes how each part looks and how it meets accessibility rules. The MVP has no dedicated UX designer: draft screens come from the Service Designer and the PM, with AI help (Jira SCRUM-35). Before anything is built, reviewers, including the Commission, need to see a screen and comment on it. Engineers then need to know which code part each drawn piece stands for.

So the screens need a place where people can look at them, and a way to tie each drawn piece to a code part. The choices are: draw in Figma, build straight in code, or describe screens in words only. If Figma is used, the drawn pieces can come from the official USWDS kit, from a kit we make ourselves, or from loose shapes.

## Decision

**Screens are drawn in Figma using only pieces from the official USWDS Design Kit, set to the same USWDS 3.13 values as our code. A hand-kept list says which Trussworks component, or which of our own components, each Figma piece stands for.**

The Figma file is "PA Compact Parts Library" (Focus team). Each piece's description in Figma names its code part, and `product/context/design/parts-crosswalk.md` holds the same list. Until the Commission decides PA Compact branding (Confluence Q9), screens use the USWDS default colours. Each screen carries a tag that says how settled it is: DRAFT, IN REVIEW or AGREED. When branding is decided, the kit gets a branded setting and the screens switch to it without being redrawn.

## Alternatives considered

**Figma with Code Connect.** Figma's Code Connect links each Figma piece to its code automatically, so no list is kept by hand. That would remove the upkeep. It needs Figma's Organization or Enterprise plan, and Focus is on the Professional plan. **Rejected**: not available on our plan. Revisit if the plan changes.

**Build screens straight in code and review them in Storybook.** Storybook shows each code part on its own page, so the drawing and the code would be one thing. Storybook doesn't build on the repo today: `pnpm build-storybook` fails with `SB_BUILDER-WEBPACK5_0002` (`@storybook/nextjs` 8.6.18 with Next 14.2.35, see SCRUM-24). Reviewers would also need a running app to comment. **Rejected for now**: revisit once Storybook builds.

**Make our own Figma kit.** We could draw only the pieces we need, styled our way. That makes a second copy of the design system, which someone has to keep in step with USWDS and with our code. The official kit already exists (USWDS Design Kit, Beta 0.3). **Rejected**: more upkeep, and no gain over the official kit.

**Describe screens in words only.** Specs could list fields and behaviour, and engineers would build from the text. It's the least work up front. Reviewers, and the Commission in particular, would have nothing to react to until code exists, so problems would show up late. **Rejected**: feedback would come after the build instead of before it.

**Three looks per screen, from rough to final.** The New York State design system shows screens in a rough, a middle and a final look, switched with one setting. We tried it on 2026-10-01 and 2026-10-02. The roughest look hid the words reviewers needed to judge, and the middle look differed from the final one only in colour. **Rejected**: one look plus a status tag says the same thing more simply.

## Consequences

### Positive

- A drawing shows what the build will look like, because both use the same parts and the same values.
- Reviewers can comment in Figma without design skills, before any code is written.
- Branding can be switched in later without redrawing screens.

### Negative

- The list matching Figma pieces to code parts is kept by hand, so it can fall out of date. *Mitigation:* any PR that adds or changes one of our components updates `parts-crosswalk.md` in the same PR.
- The USWDS kit is a beta (0.3), so its pieces may change in later releases. *Mitigation:* the kit is copied into our own Figma file and changes only when we choose.
- USWDS leadership changed in September 2026 (Nextgov, 2026-09-16: <https://www.nextgov.com/people/2026/09/gsas-web-design-system-head-replaced-treasury-ai-engineer/416035/>). *Mitigation:* the code stays pinned at USWDS 3.13 until the team reviews a newer version.

## Verification

- **Pieces:** every screen is built from Parts Library pieces only (rule 1 in `figma-working-guide.md`). Reviewers check this at spec review.
- **The list:** a PR that changes a component in `engineering/client/src/components/` without updating `parts-crosswalk.md` is sent back in review.
- **Drawing and code:** when a screen is marked AGREED, and in each PR that builds a screen, the code is compared with the drawing, word by word and part by part (`ui-workflow.md`, "When code is checked against the drawing"). Differences are logged as defects.

## Related

- `product/context/design/ui-workflow.md`: the steps from flow to screen to code. That file describes a process, so it sits outside this decision. Whether the process needs its own decision record is for the Lead Engineer to decide.
- `product/context/design/figma-working-guide.md` and `parts-crosswalk.md`.
- Kalish's flows, FLOW-01 to FLOW-07 (PR #75): what each screen must do.
- SCRUM-24 (Storybook), SCRUM-35 (AI-assisted UX plan), Confluence Q9 (branding).
- Future design records, not yet written: keep or replace the custom `Card`; whether the federal banner and identifier appear.
