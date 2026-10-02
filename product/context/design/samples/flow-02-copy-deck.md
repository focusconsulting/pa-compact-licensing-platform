---
artifact: copy-deck
status: draft
authored-by: Service Designer (Moe)
last-revised: 2026-10-02
screens: [FLOW-02/SCR-01, FLOW-02/SCR-02]
checked-with: plain-copy (ui-copy rules), ux-critique, Moe's Figma comments of 2026-10-01
---

# Copy deck: FLOW-02 sample screens (state staff reviewing an application)

Every word on the two sample screens, checked with `plain-copy` before drawing. The rules applied:

- one name per thing;
- buttons say what they do;
- labels are nouns;
- no internal codes or open questions on screen (those go in the notes);
- nothing claims a feature that isn't designed.

## One name per thing

| Thing | Name used everywhere | Replaces |
|---|---|---|
| The list | Applications to review | "Applications to verify", "Applications waiting for your state" |
| How long it's been open | Day 23 of 60 | "Days left", "Days since received", "day 23 of 60" |
| Status: complete, not yet decided | Ready to review | "Submitted" |
| Status: staff asked for more | Waiting for the PA | "Information requested" |
| Status: PA answered | PA replied | "Resubmitted" |
| Outcome | Eligible / Not eligible | "Eligible / Denied" |
| The staff member's message | Note to the PA | "request", "request note" |

## Screen 1: Applications to review

| Element | Text |
|---|---|
| Breadcrumb | Home › Applications to review |
| Heading | Applications to review |
| Banner (info, slim) | An application is withdrawn if the PA doesn't send everything you asked for within 60 days of it arriving. |
| Columns | PA name · Received · Day (of 60) · Status |
| PA name | A link to the application (for example "Sample PA A") |

## Screen 2: one application

| Element | Text |
|---|---|
| Breadcrumb | Home › Applications to review › Sample PA A |
| Heading | Sample PA A |
| Tags | Ready to review · Received Sep 08, 2026 · Day 23 of 60 |
| Section | What the PA told us |
| Rows | Date of birth · Home address · Email · NCCPA certification (Current, #000000) |
| Section | 1. Is [your state] the PA's home state? |
| Rows | The PA's reason: I live in this state |
| Link | View proof of address (PDF, uploaded Sep 08, 2026) |
| Checkbox | This matches our records. Hint: Not sure? Send the PA a note below. |
| Section | 2. Does the license match your records? |
| Table columns | (field) · What the PA entered · Your records |
| Rows | License number · Status · Expiry date · Restrictions |
| Warning (when they differ) | The [field] doesn't match (for example, "The expiry date doesn't match"). Check which is right before you confirm. |
| Checkbox | The license matches and has no restrictions |
| *State: no record yet* (proposed, not decided) | Your records column reads "Not in this system yet". Button: **Enter the license from your records**. How the state's license data gets in is still open (Rule 4 §4.2(e), §4.3(c)(11)). |
| Section | 3. Has the background check been done? |
| Date field | Label: Date your state's background check was finished. Hint: Must be within 60 days of the received date. Don't enter or upload the results. |
| Section | 4. Is there an open investigation the PA didn't mention? |
| Rows | What the PA signed: "I'm not aware of any pending investigation of my license" (Sep 08, 2026) · Open investigations in your records: None found |
| Checkbox | I checked our investigation records and found no conflict |
| Section | Need more from the PA? (optional) |
| Text box | Label: Note to the PA. Hint: The PA gets an email asking them to sign in and read it. |
| Button | Send note to the PA |
| *State: waiting* | Warning banner at top: Waiting for the PA. You sent a note on Sep 20, 2026. You can decide when they reply. |
| Section | 5. Your decision |
| Choices | Eligible · Not eligible |
| *State: Not eligible chosen* | Text box. Label: Reason the PA isn't eligible. Hint: The PA will see this and how to appeal to your state. Don't include criminal history details. |
| Button | Record decision (grey until ready) |
| Line under the grey button | Confirm the license and enter the background check date first. |

## Read-aloud check

Read top to bottom aloud, 2026-10-01. Removed in this pass:

- "Results are never stored here" (a system rule told to the wrong person);
- "not this note" (unclear);
- "Do the PA's signed statements hold up?" (didn't say what to check);
- "(how this is checked with NCCPA is still open)" (an internal question shown on screen).
