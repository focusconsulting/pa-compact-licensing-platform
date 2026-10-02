---
artifact: guide
status: draft
authored-by: Service Designer (Moe)
last-revised: 2026-10-02
audience: PM (Nebi), Service Designer (Moe), and any Claude session working in the Figma files
see-also: [README.md, ui-workflow.md, parts-crosswalk.md]
---

# Working in the Figma files

How to make and change screens so everyone, whether a person or Claude, does it the same way. Nobody needs to be a Figma expert: Claude does the Figma work and follows this guide, and people review the result. Claude also keeps the session notes, so nobody has to remember which setting does what.

## The files (all in the Focus team, Pro plan)

| File | Key | What it is |
|---|---|---|
| PA Compact Parts Library | `k1W9PxXhtQ3fopcKUePpH9` | The official USWDS Design Kit Beta 0.3, adapted. **Every screen is built from its parts.** |
| PA Compact Journey Maps & Workflows | `rzT4ibs4oFCAVtXXVunK3F` | Journey maps. "Commission-Facing" and "Internal Only" sections |
| Wireframes (one per release) | created at the first spec | Screens, built from Parts Library instances |

## Rules

1. **Only use Parts Library parts.** Place instances; don't draw look-alike shapes. If a screen needs something the library lacks, stop. It becomes a design decision record (`/author-design-adr`) before anyone draws it.
2. **Don't edit the parts' look by hand** (no local colour or font overrides). Look comes only from the mode, so the switch keeps working.
3. **Don't change the `Default` mode** of the "USWDS Theme" collection. It's the kit's original. Our modes are separate (see below).
4. **Name every screen frame by its ID**: `<story-id>/SCR-<nn> <short name>`, for example `012-sql-verify/SCR-03 Decision`.
5. **Draw every state the spec lists** (empty, filled, error, waiting, done, denied) as its own frame, named with the ID plus the state.
6. **Tag behaviours in the frame's annotation**: *rule-required* (with the citation, for example Rule 3 §3.4(b)) or *Focus preference*. Mark terms from draft rules as *provisional*.
7. **Every check needs something to check against.** A tick box, confirm button or approve control must sit next to the information being checked (what the person told us, and what to compare it with). A tick box on its own is a rubber stamp.
8. **Open the reference before you cite it.** If a note says "follows CompactConnect screen X", the screenshot (`product/context/reference/compactconnect-screens/`) must have been looked at.
9. **Keep AI output reviewable.** Draft only the screens in the current spec, and get each one reviewed before drafting more.

## The example page: start here

The Parts Library page **"🧪 DRAFT SAMPLE (not representative): FLOW-02 workflow example"** shows every step, using one part of Kalish's FLOW-02 (a state checks a PA's application):

- **Two screens:** *Screen 1, applications waiting for your state*, and *Screen 2, check one application and decide*. Both are built only from Parts Library pieces.
- **One set of screens** in the USWDS default colours, each with a status tag (Draft, In review or Agreed) beside its title.
- **A yellow note beside each screen** (not part of the screen) in the format below.
- **Sample data only.** The rules marked "being re-checked" depend on the review of PR #75.

## Every page starts with a short lead-in, and the canvas explains itself

Based on the NYS Fidelity Modes file, which uses small tagged callouts next to what they explain, plus `plain-copy` (built for scanning) and `ux-critique` (weight matches importance; don't repeat).

- **Top-left: a red DRAFT banner** (only while the page is a draft), at most about 1,000 px wide so lines stay readable.
- **Under it, the START HERE panel:**
  - a two-line intro;
  - **a diagram** of the 6 steps (Source, Build, Break, Decide, Review and walk through, Build in code), with the loop from Decide back to Build and a YOU ARE HERE marker. It's a diagram, not the USWDS Step indicator, because the process loops;
  - a colour key shown as swatches;
  - one line linking to this guide.
- **On the canvas: numbered callouts** ("STEP 2 · BUILD THE DRAFT"), one per step. Each is at most two lines and joined by a dashed line to the section it describes. The current step's tag is orange.
- **Explanations live in this guide, not on the canvas.**
- **Figma only refers to things the team can open:** Figma itself, the repo (including open PRs), Jira and Confluence. Never a local file path. When a doc isn't shared yet, say so ("Moe has it; not shared yet"). Once it's uploaded, replace that line with the link.
- **The page reads in step order, top to bottom, in one column:**
  1. the banner and START HERE;
  2. the SBB board (Source, Build, Break, Decide, left to right);
  3. the Screens section.

  Each callout is joined to a real screen or column. None is left aimed at an empty section edge.

Example: the FLOW-02 draft sample page (panel `3059:28790`). The first version of the panel (a 1,500 px wall of text) was replaced on 2026-10-01 after Moe's critique.

## Every screen goes through Source → Build → Break

No screen gets drawn first. Each one goes through the team's Source, Build, Break method, and the Service Designer decides at each checkpoint. The note beside the screen shows that each step happened:

- [ ] **Source** (before drawing; shown to the Designer first)
  - [ ] The adopted rule sections, read in the rule PDF itself, not a summary or a flow's paraphrase
  - [ ] What the flow (FLOW-0x) says this person sees and does on this screen
  - [ ] The reference screen (CompactConnect capture or other), opened and looked at
  - [ ] Any experience-layer evidence (what real users have said)
  - [ ] What we don't know yet
- [ ] **Build**: in the USWDS default colours, tagged Draft, Parts Library pieces only, every control next to the information it acts on, plain-language note
- [ ] **Break** (start clean; the Designer gives the verdict)
  - [ ] For each control: what does this person know or compare here, and where is it on the screen?
  - [ ] Each "required by the rules" item checked against the rule text
  - [ ] Compared with the reference screen: what we kept, what we changed and why
  - [ ] One alternative layout named, and why we didn't pick it

## Notes beside screens: write them so anyone can act on them

Every screen gets a yellow note frame named `NOTE (not part of the screen): <screen title>`. Use these headings, in plain words, with no rule codes in the body:

1. **What this screen is for:** one or two sentences a new teammate understands.
2. **Who uses it:** the person, in everyday terms (for example "staff at the PA's home licensing state", not "SQL").
3. **What it must do (required by the rules):** bullets. Say what and why in words.
4. **How it behaves (team decisions):** bullets, with the reason.
5. **What we chose (can change):** Focus preferences, so the Commission knows they're open.
6. **Still to decide / still to draw:** each item with who decides or what's missing.
7. **What changed and why** (only when something was corrected): a pink box with the date, what it said before, what the source says, and what was changed. Keep corrections visible; don't silently edit.
8. **Sources:** one small line at the bottom with the rule sections, flow and decision IDs.

The same goes for words on the screen itself: no internal codes. A checkbox says "Your state is the right home state for this PA", not "SQL basis confirmed".

## One set of screens, with status tags

Changed twice on 2026-10-02 at Moe's request:

1. **Three versions became two.** Low scribbled out the text, and Mid vs High wasn't a clear difference.
2. **Two became one.** Once the draft look was readable, the only difference from the final look was grey instead of blue. People comment on colour anyway.

So now:

- **One set of screens** in the USWDS default colours, in a section headed "SCREENS: shown in the USWDS default colours. PA Compact branding isn't decided yet (Q9), so colours will change."
- **A status tag beside each screen's title:** DRAFT, IN REVIEW or AGREED. The tag says how settled a screen is, not its styling.
- **Marking a screen AGREED** starts the code check in `ui-workflow.md` ("When code is checked against the drawing"). Changing an agreed screen sets it back to IN REVIEW.
- **Nothing is redrawn later.** When the Commission decides branding (Q9), a branded mode is added to the Parts Library and the section switches to it.

**The settings behind it.** The "USWDS Theme" collection has these modes:

| Mode | Use |
|---|---|
| `Final (USWDS 3.13, matches the code)` | The screens; matches `engineering/client/src/styles/_uswds-theme.scss` and `uswds-3.13-theme-colors.json` |
| `Draft (grey, readable)` | Not used on the sample page now. Kept in case a grey version is wanted again |
| `Layout sketch (optional)` | Grey with square corners; with the `Scribble (Low)` font, text is unreadable. Layout experiments only |
| `Default`, `Project theme dark` | The kit originals; leave alone |

A screen takes the look of the section it is in. The Screens section sets `Font role / Heading` to `Serif` (USWDS 3.13 default `$theme-font-role-heading: "serif"`, Merriweather); body text uses the normal Public Sans. Every section has a large header (as above) and a visible title above each screen.

## For Claude: tooling and recipe

- **Tool:** `figma-console-mcp`, pinned to `1.40.8`, with the Figma Desktop Bridge plugin running in each file you work in. Each person uses their own Figma personal access token in their own MCP config. **Never write a token into a file.**
- **Shared Mac:** don't use `@latest`, and stop old servers. Stale servers hold the bridge ports (9223 to 9232) and block other users.
- **Before any change:** call `figma_list_open_files`, then `figma_navigate` with `lock: true` on the target file. Take a screenshot of the page before and after, and check that nothing overlaps.
- **Start of session:** search the components again (`figma_search_components`). Node IDs go stale between sessions.
- **Setting a section's look** (plugin API, inside `figma_execute`):

```js
const cols = await figma.variables.getLocalVariableCollectionsAsync();
const C = n => cols.find(c => c.name === n);
const mode = (c, re) => c.modes.find(m => re.test(m.name)).modeId;
function setLook(section, look) { // 'Final' (default colours) now; a branded mode later
  const theme = C('USWDS Theme');
  for (const c of cols.filter(c => c.name.startsWith('Font role /') || c.name === 'Font type / Proto')) section.clearExplicitVariableModeForCollection(c);
  section.setExplicitVariableModeForCollection(theme, mode(theme, new RegExp('^' + look)));
  const hd = C('Font role / Heading'); section.setExplicitVariableModeForCollection(hd, mode(hd, /^Serif$/));
}
```

- **After any change to a part or the crosswalk:** update the part's description block headed "PA COMPACT CROSSWALK" and `parts-crosswalk.md` in the same PR.
- **Record** the file key, page and node IDs of what you built in the session note.

## What people do (no Figma skills needed)

- **Review:** open the link Claude gives you, look at each screen, and leave comments in Figma or in the review notes against the screen ID.
- **Decide:** whether a screen is ready for the client, and whether a behaviour is rule-required or a preference.
- **Only these need a person in Figma:** opening a Community file ("Open in Figma"), running the Bridge plugin in a file, and renaming or moving files. The plugin can't do them.
