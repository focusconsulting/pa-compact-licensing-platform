---
tension-id: TENSION-02-changing-state-of-qualifying-license
date-surfaced: 2026-10-02
surfaced-by: Researcher (Moe), PR #75 review group 2
status: open
---

# TENSION-02: What does a PA need to switch to a different state of qualifying license?

A PA (physician assistant) joins the compact through one state where they hold a license, called their state of qualifying license. Through the compact they can then get a privilege, the right to practice in another member state (the rules say "Participating State") without a second license. The adopted rules describe one way to switch to a different state of qualifying license, and that description refers to a section that does not exist.

## Positions

What each record says, source by source.

- **Adopted Rule 3, Compact Privilege (adopted 2026-04-06), 3.6(a)**, PDF page 6, lines 209-218. If a PA gives up their qualifying license before it expires, all their privileges end that day, "unless the PA selects a new state of qualifying license prior to terminating the current qualifying license by following this process". Step (3) of that process: "Meet the requirements of paragraph 2.1 with the new state of qualifying license,".
- **No adopted rule has a paragraph 2.1.** All three adopted rules were searched: the rule on rulemaking, Rule 3 (Compact Privilege) and Rule 4 (Compact Data System).
- **Where "paragraph 2.1" came from.** In the 2025 draft of Rule 2 (`pa-compact-rule-2-and-3-drafts.pdf`, PDF page 2, line 63), paragraph 2.1 was "State of qualifying license designation". It listed tests the PA's state had to meet: primary residence, where they practice, their employer's location, or their tax state. In March 2025 the Commission's legal counsel said the Commission had no authority to add them (Executive Committee minutes, 2025-03-12, PDF page 4, lines 122-124). By July 2025 the Rules Committee had taken them out (minutes, 2025-07-10, PDF page 3, lines 73-74), and planned to move Rule 2's content into Rule 3 (same minutes, PDF page 4, line 130).
- **Rule 2 is now a definitions rule.** Draft Rule 2, Definitions, has its own "2.1 Definitions" (PDF page 1, line 17). It went out for public comment on 2026-08-12 (Executive Committee minutes, line 97). It is not adopted. If it is adopted as written, "paragraph 2.1" in 3.6(a)(3) would refer to a list of definitions, which sets no requirements.
- **What the adopted rule asks of the first state a PA picks.** Rule 3, 3.4(a)(2), PDF page 4, lines 118-121: the PA designates a state "if the PA possesses a full and unrestricted license to conduct medical services in that Participating State."
- **Switching without giving up a license is not mentioned.** 3.6(a) only applies when the PA gives up their current qualifying license. No adopted text allows or forbids switching any other way. The Rules Committee minutes of 2025-02-24 (PDF page 3, line 99), from before the rule was adopted, record: "Voluntary termination being the only way to get a new state of qualifying licensure."

## Why it matters

Two things are undecided:

1. Which requirements the new state has to meet when a PA switches. The text refers to a paragraph that no longer exists.
2. Whether a PA who holds licenses in two compact states can move their qualifying license from one to the other without giving one up.

The system has to know both to build the switching steps and to decide which states a PA can pick. No flow in `product/context/flows/` covers switching yet. `flows/05-adverse-action-cascade.md` line 86 has one related row: when a qualifying license is given up, all the PA's privileges become inactive. That row matches 3.6(a) and does not change.

## Proposed resolution path

- **Focus preference until the Commission answers:** treat 3.6(a)(3) as asking for what 3.4(a)(2) asks: a full and unrestricted license in the new state. Reason: that is the only requirement for choosing a state in any adopted rule. The tests paragraph 2.1 used to hold were out of the draft by July 2025, and in March 2025 counsel had said the Commission had no authority to add them.
- **Focus preference until the Commission answers:** do not build switching while keeping both licenses. Reason: no adopted text describes it. Until then the only switching route the system offers is the 3.6(a) one.
- **Question for the Commission's rules counsel**, to add to the Commission question list on Confluence (Sprint 0 Questions, Q01 to Q25: <https://focusdigital.atlassian.net/wiki/spaces/PC/pages/62881793>): "Rule 3.6(a)(3) asks a PA to 'meet the requirements of paragraph 2.1' with the new state. No adopted rule has a paragraph 2.1. Does it mean the 3.4(a)(2) requirement, a full and unrestricted license in that state? And can a PA change their state of qualifying license without giving up their current one?"
- Record the answer here under `## Resolution`. If the Commission amends Rule 3, add an atom (one quoted passage from one source, in `evidence/atoms/`) quoting the new text.
