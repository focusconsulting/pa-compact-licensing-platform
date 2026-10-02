---
tension-id: TENSION-03-license-active-past-printed-expiry
date-surfaced: 2026-10-02
surfaced-by: Researcher (Moe), PR #75 review group 2
status: open
---

# TENSION-03: Which expiry date does a state send when its licenses can stay active after expiry?

A compact privilege is the right of a PA (physician assistant) to practice in another member state (the rules say "Participating State") without a second license. It is based on one of the PA's licenses, their qualifying license. It ends on the expiry date that license had when the PA applied for the privilege, or earlier if the license is revoked, given up, or the privilege is ended for discipline. In at least one state, Maine, a license can stay active after its expiry date (Rules Committee minutes, 2025-01-29 and 2025-02-24, below). The adopted rule is clear that the privilege still ends on the original date. What is not known is which date such a state would send to the data system as the expiry date.

## Positions

What each record says, source by source.

- **Adopted Rule 3, Compact Privilege (adopted 2026-04-06), 3.5(a)**, PDF page 5, lines 169-176: "A compact privilege shall be valid until the expiration or revocation of the qualifying license used to apply for the privilege unless the privilege is terminated pursuant to an adverse action or the qualifying license is voluntarily terminated by the PA. The expiration date of the qualifying license shall be the expiration date that was in effect on the date the PA applied for the compact privilege. Any renewal of the qualifying license does not automatically renew the compact privilege."
- **An earlier draft covered this case, and it was taken out.** The 2025 draft of Rule 3 (`pa-compact-rule-2-and-3-drafts.pdf`, PDF page 9, lines 181-185) said: "Should the qualifying license remain in an active status past the expiration date, any compact privilege issued under that qualifying license will remain active until the status of qualifying license is updated by the State of Qualifying License." `ATOM-GOV-R23-11` (an atom: one quoted passage from one source, in `evidence/atoms/`) quotes it. This file calls it the "grace" behaviour: privileges stay active until the state updates the license. The adopted rule does not include it.
- **What the Rules Committee said about it**, minutes, 2025-02-24, PDF page 4, lines 116-123. Here "3.5.C" means the 2025 draft's 3.5(c), the grace sentence quoted above. The adopted rule's 3.5(c) is different text, about renewal. T. Terranova is Tim Terranova, Maine's delegate to the Commission (attendance lists in the Commission minutes).
  - "3.5.C Was intended to respond to the Maine example in order to use active status versus expiration date."
  - "There is a concern that this could create a scenario for unlicensed practice as most states use a date of expiration instead of letting practice continue after that date."
  - "T. Terranova confirms that the Maine board can and will need to address this as it seems unique to them."
- **The same case was raised a month earlier.** Rules Committee minutes, 2025-01-29, PDF page 3, line 81: "Example Maine – active vs active expired, need to define both". The minutes do not define the two terms.
- **No record on disk says whether Maine has addressed it.** The Maine medical board sent public comments on draft Rule 3; the Rules Committee went through them on 2026-02-09 (comments numbered 1 to 12, minutes PDF pages 2-5). None is about this case. Rules, Executive and Full Commission minutes on disk through 2026-09-28 were also searched. Other states have not been checked. The 2025-02-24 minutes say "most states use a date of expiration".

## Why it matters

Under 3.5(a), a privilege ends on the expiry date the license had when the PA applied. It ends on that date even if the license has been renewed or is still active. That is what the rule says, and it also says how the PA is told:

- The Commission emails the PA "Not less than 60 days prior to the expiration of a compact privilege" (3.5(b), PDF page 5, lines 178-184).
- "The PA is responsible for renewing any compact privilege(s) prior to their expiration" (3.5(b)).
- Renewing the license does not renew the privilege (3.5(a)). The PA applies again once the state confirms continued eligibility (3.5(c) and (d), PDF page 5, lines 186-201).

So the system needs no "license still active" exception. The grace sentence would have added one. The committee raised an unlicensed-practice concern about it on 2025-02-24, and the adopted rule left it out.

What is still open is the data, not the rule. The system can only end the privilege on the right date if the state sends the right expiry date. For a state like Maine, where the minutes say a license can be "active expired", it is not known which date the state would send.

This affects `flows/04-expiration-and-renewal.md` (line 56 describes the removed grace behaviour) and the tickets that flow feeds: A-04, L-04 and P-01. These IDs come from the MVP ticket breakdown the flows refer to (`product/backlog/mvp-ticket-breakdown.md`), which is not yet in the repo.

## Proposed resolution path

- **Rule-required:** end the privilege on the expiry date that was in effect when the PA applied (3.5(a)). So the grace behaviour in flow 04, line 56, has to come out. The edit is made when flow 04 is reviewed, because the review process changes no flow before it has been walked with the researcher. Until then flow 04 has a "needs review" note.
- **Question for the Commission and the pilot states**, to add to the Commission question list on Confluence (Sprint 0 Questions, Q01 to Q25: <https://focusdigital.atlassian.net/wiki/spaces/PC/pages/62881793>): "Rule 3.5(a) ends a privilege on the license expiry date in effect when the PA applied. Where a state's license can stay active after its expiry date, as the Rules Committee minutes describe for Maine, which date should the state send to the data system as the expiry date? The Rules Committee said in February 2025 that Maine would need to address this. Has it?"
- Record the answer here under `## Resolution`.
