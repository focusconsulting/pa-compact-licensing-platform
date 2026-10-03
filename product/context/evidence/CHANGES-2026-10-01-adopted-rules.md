# Atoms superseded by the adopted Rules 3 and 4

**Date:** 2026-10-01. **Ticket:** SCRUM-39. **Written by:** Moe (moe-focus).

The Commission adopted Rule 3 (Compact Privilege) and Rule 4 (Compact Data System) on 2026-04-06. They took effect on 2026-05-31. Ten atoms in this folder quoted draft text that the adopted rules changed (eight on 2026-10-01, two on 2026-10-02). Each one now has a new atom that quotes the adopted text. The old atoms are kept and marked `status: superseded`.

This file records each change: what the draft said, what the adopted rule says, and which flows and signals cite the old atom. Those flows and signals carry a "needs review" note until they are updated. When a file is updated, remove its note and its entry in the "Cited by" column.

Draft sources:

- `product/context/research-corpus/raw/raw/claudesourced-pacompact-meetings/rules-committee/pa-compact-rule-2-and-3-drafts.pdf`: a draft redline of Rules 2 and 3. The file gives no date: its "History of Rule" line is blank (PDF page 1, line 3). Three Rules Committee minutes suggest it is a version from between 2025-01-29 and 2025-07-10:
  - On 2025-01-29 the committee asked to "lower the 25% or change it to active medical services in that state" (minutes PDF page 2, line 48). The redline shows that edit.
  - On 2025-02-24 the committee discussed "3.5.C", the redline's grace sentence (minutes PDF page 4, lines 116-123).
  - On 2025-07-10 the committee said the tests in 2.1(a) had been "taken out" (minutes PDF page 3, lines 73-74). The redline still has them.

  Line numbers restart for each rule. Draft text below is quoted as amended: inserted text kept, struck text left out, checked against the page images. The converted text of this redline lost its strike-through marks, so quote from the PDF.
- `product/context/research-corpus/raw/raw/claudesourced-pacompact-meetings/rules-committee/pa-draft-rules-2_3_5.pdf`: draft Rule 5, Data System, renumbered Rule 4 on 2025-11-10. Clean text, with no redline marks.

Adopted text: `product/context/research-corpus/raw/raw/commission-documents/rules/adopted/`.

Not covered here:

- `ATOM-GOV-R23-01` and `ATOM-GOV-R23-11` quote draft text that the adopted rules left out. They are marked superseded with no replacement. See "Atoms quoting draft text the adopted rules left out" below.
- Twelve draft-rule atoms quote text that reads the same in the adopted rules. Each keeps its draft source and gets one `adopted-text:` line naming the adopted section. See "Atoms with the same wording in the adopted rules" below.

## Summary

| Old atom | New atom | Adopted section | What it covers | Cited by |
|---|---|---|---|---|
| `ATOM-GOV-R23-05` | `ATOM-GOV-R3-01` | Rule 3.4(a) | What a PA submits to apply | `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/01-end-to-end-privilege-issuance.md`, `flows/02-sql-eligibility-verification.md` |
| `ATOM-GOV-R23-06` | `ATOM-GOV-R3-02` | Rule 3.4(b) | What the state of qualifying license does with an application | `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `evidence/signals/SIGNAL-the-system-does-the-heavy-lifting-for-states.md`, `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/02-sql-eligibility-verification.md` |
| `ATOM-GOV-R23-12` | `ATOM-GOV-R3-03` | Rule 3.5(c) | What the state of qualifying license does at renewal | `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/04-expiration-and-renewal.md` |
| `ATOM-GOV-R23-13` | `ATOM-GOV-R3-04` | Rule 3.7(a)-(b) | When an application is withdrawn | `flows/02-sql-eligibility-verification.md`, `flows/03-payment-and-remote-state-issuance.md`, `flows/06-state-machines.md` |
| `ATOM-GOV-R23-14` | `ATOM-GOV-R3-05` | Rule 3.9(a) | Appealing a denial | `flows/02-sql-eligibility-verification.md` |
| `ATOM-GOV-R23-15` | `ATOM-GOV-R3-06` | Rule 3.9(b) | When a state withdraws eligibility | `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/05-adverse-action-cascade.md`, `flows/06-state-machines.md` |
| `ATOM-GOV-R5-02` | `ATOM-GOV-R4-01` | Rule 4.3(c) | What the state of qualifying license must verify and submit | `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/01-end-to-end-privilege-issuance.md`, `flows/02-sql-eligibility-verification.md` |
| `ATOM-GOV-R5-05` | `ATOM-GOV-R4-02` | Rule 4.4(b) | Reporting adverse actions | `flows/05-adverse-action-cascade.md` |
| `ATOM-GOV-R23-09` | `ATOM-GOV-R3-07` | Rule 3.5(a) | When a privilege expires, and renewing it | `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `flows/04-expiration-and-renewal.md`, `flows/06-state-machines.md` |
| `ATOM-GOV-R5-03` | `ATOM-GOV-R4-03` | Rule 4.3(d) | What the remote state must verify and submit | `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/01-end-to-end-privilege-issuance.md`, `flows/03-payment-and-remote-state-issuance.md` |

## `ATOM-GOV-R23-05` to `ATOM-GOV-R3-01`: What a PA submits to apply (Rule 3.4(a))

- **Draft**, Rule 3.4(a)(2), PDF page 7, lines 111-115: "During the application process designate a state of qualifying license. The PA must meet one of the state of qualifying license eligibility requirements in Rule 2 at the time of application. A member state shall apply Rule 2 requirements contemporaneously when evaluating a licensee's compact privilege eligibility under Compact Section 4 and this Rule."
  **Adopted**, Rule 3.4(a)(2), lines 118-121: "At the time of application designate a Participating State as the state of qualifying license for purposes of eligibility for a compact privilege through the Compact if the PA possesses a full and unrestricted license to conduct medical services in that Participating State."
- **Draft**, Rule 3.4(a)(3), PDF page 7, lines 116-118: "Submit to a criminal background check at the time of application through the process designated by the state of qualifying license which will include the submission of fingerprints or other biometric based information."
  **Adopted**, Rule 3.4(a)(4), lines 127-129: "Submit to a criminal background check within 60 days of the application through the process designated by the state of qualifying license which will include the submission of fingerprints or other biometric based information."
- **Draft**, Rule 3.4(a)(4), PDF page 7, lines 119-120: "Submit any other information regarding clarifying any discrepancies requested by the state of qualifying license."
  **Adopted**, Rule 3.4(a)(6), lines 132-134: "Submit any other information requested by the state of qualifying license regarding any unusual circumstances related to the application under review in accordance with compact requirements."
- **Draft**, Rule 2.1(b), PDF page 3, lines 80-83: "Regardless of the designation qualification under subsection (a), the PA shall provide the Commission the primary residence address and consent to service of process by mail at the primary residence address under Section 5(A)(2) of the Compact. A change of primary residence address shall be reported to the Commission within thirty (30) days."
  **Adopted**, Rule 3.4(a)(3), lines 122-126: "Regardless of the participating state selected as the state of qualifying license, the PA shall provide the Commission the primary residence address and consent to service of process by mail at the primary residence address under Section 5(A)(2) of the Compact. A change of primary residence address shall be reported to the Commission within thirty (30) days of the change."
- **Draft** Rule 3.4(a) (PDF pages 7-8, lines 107-122) has no item on pending investigations.
  **Adopted**, Rule 3.4(a)(5), lines 130-131: "Sign an attestation that the applicant is unaware of any pending investigation of the current qualifying license at the time of the application."
- Draft 3.4(a)(1) and (5) read the same as adopted 3.4(a)(1) and (7).

Cited by: `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/01-end-to-end-privilege-issuance.md`, `flows/02-sql-eligibility-verification.md`.

## `ATOM-GOV-R23-06` to `ATOM-GOV-R3-02`: What the state of qualifying license does with an application (Rule 3.4(b))

- **Draft**, Rule 3.4(b), PDF page 8, lines 124-133: "When the state of qualifying license receives the application through the Compact Commission that state shall: (1) Evaluate the PA's eligibility for participating in the compact privilege process; (2) Perform a criminal background check pursuant to Public Law 92-544 as required by the terms and provisions of the Compact within 60 days; (3) Determine whether the PA meets one of the state of qualifying license eligibility requirements in Rule 2 at the time of application; and (4) Issue notice, through the data system, to the Compact Commission verifying or denying the PA's eligibility to participate in the Compact and confirming that the state will serve as the state of qualifying license."
  **Adopted**: see `ATOM-GOV-R3-02`

Cited by: `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `evidence/signals/SIGNAL-the-system-does-the-heavy-lifting-for-states.md`, `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/02-sql-eligibility-verification.md`.

## `ATOM-GOV-R23-12` to `ATOM-GOV-R3-03`: What the state of qualifying license does at renewal (Rule 3.5(c))

- **Draft**, Rule 3.5(d), PDF page 9, lines 187-196: "When the state of qualifying license processes a complete renewal for the PA, the state of qualifying license shall: (1) Determine that the PA has not been found guilty by a court of a felony or misdemeanor offense through an adjudication or by an entry of a plea of guilt or no contest to the charge; (2) Determine whether the PA meets one of the state of qualifying license eligibility requirements in Rule 2 at the time of renewal; and (3) Issue notice, through the data system, to the Compact Commission verifying or denying the PA's eligibility to continue participation in the Compact."
  **Adopted**: see `ATOM-GOV-R3-03`

Cited by: `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/04-expiration-and-renewal.md`.

## `ATOM-GOV-R23-13` to `ATOM-GOV-R3-04`: When an application is withdrawn (Rule 3.7(a)-(b))

- **Draft**, Rule 3.6(a)(1), PDF page 10, lines 210-212: "If the PA does not submit all requested materials, including any required fees, within 60 days after the application is opened, then the application shall be deemed to have been withdrawn."
  **Adopted**, Rule 3.7(a)(1), lines 235-237: "If the PA does not submit all requested materials, including any required fees, within 60 days after the application is opened, then the application shall be deemed incomplete and to have been withdrawn."
- The rest of draft 3.6 (PDF page 10, lines 207-223), including the remote-state clock in (b), matches adopted 3.7 apart from the section number and the same "deemed incomplete and" wording in 3.7(b)(1).

Cited by: `flows/02-sql-eligibility-verification.md`, `flows/03-payment-and-remote-state-issuance.md`, `flows/06-state-machines.md`.

## `ATOM-GOV-R23-14` to `ATOM-GOV-R3-05`: Appealing a denial (Rule 3.9(a))

- **Draft**, Rule 3.8(a), PDF pages 10-11, lines 241-245: "If the member state selected as the state of qualifying license issues a notice to the Compact Commission denying the applicant's eligibility for the compact, the PA may appeal such determination. The appeal shall be filed with the member state that issued the denial and shall be subject to the laws of that state."
  **Adopted**: see `ATOM-GOV-R3-05`
- In the redline, "of eligibility within 30 days of the PA's receipt of the notice" is struck through (PDF page 10, line 243). The earlier version of this atom quoted those words as live text, because the converted file lost the strike-through.

Cited by: `flows/02-sql-eligibility-verification.md`.

## `ATOM-GOV-R23-15` to `ATOM-GOV-R3-06`: When a state withdraws eligibility (Rule 3.9(b))

- **Draft**, Rule 3.8(b), PDF page 11, lines 247-255: "If the member state selected as the state of qualifying license issues a notice to the Compact Commission approving the PA's eligibility for the compact and thereafter withdraws the approval due to the PA not meeting the Compact's eligibility requirements, any compact privilege issued under that qualifying license shall automatically be cancelled with no action required by any member state. The Compact Commission shall provide e-mail notice of the withdrawal to the PA along with notice that all issued compact privileges have been cancelled. The PA may appeal the withdrawal of eligibility. The appeal shall be filed with the member state that issued the denial and shall be subject to the laws of that state."
  **Adopted**: see `ATOM-GOV-R3-06`
- In the redline, "within 30 days of the PA's receipt of the withdrawal notice" is struck through (PDF page 11, lines 253-254).

Cited by: `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/05-adverse-action-cascade.md`, `flows/06-state-machines.md`.

## `ATOM-GOV-R5-02` to `ATOM-GOV-R4-01`: What the state of qualifying license must verify and submit (Rule 4.3(c))

- **Draft**, §5.3(c), lines 114-134: "As a State of Qualifying License, a Participating State shall verify and submit the following information for each PA applying for or holding a Qualifying License: (1) Full legal name; (2) Other name(s) used, previously or currently; (3) Sex; (4) Date of birth; (5) National Provider Identifier Number; (6) Social security number; (7) Primary residence address of record; (8) Telephone number of record; (9) E-mail address delegated by applicant to receive correspondence from the Compact Commission and Participating States; (10) PA educational program completed, including year of completion; (11) NCCPA Certification number, current certification status and certification expiration date; (12) License number, status, issue date and expiration date in the designated State of Qualifying License; (13) Adverse actions against a License or Compact Privilege; (14) The existence of Significant Investigative Information; and (15) Any denial of licensure, and the reason(s) for such denial (excluding the reporting of any criminal history record information where prohibited by law)."
  **Adopted**: see `ATOM-GOV-R4-01`

Cited by: `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/01-end-to-end-privilege-issuance.md`, `flows/02-sql-eligibility-verification.md`.

## `ATOM-GOV-R5-05` to `ATOM-GOV-R4-02`: Reporting adverse actions (Rule 4.4(b))

- **Draft**, §5.4(b), lines 159-166: "Adverse action reports shall: (1) Include the participating PA's name, NPI number, a summary of the action taken or a copy of a public complaint detailing the charges against the PA, and a copy of the order or other documentation imposing the adverse action. (2) Be submitted to the Compact Commission as soon as reasonably possible, but no later than ten days after the adverse action is ordered or otherwise taken by the State. If the adverse action is summary or emergency action, the report shall be submitted within one business day."
  **Adopted**: see `ATOM-GOV-R4-02`
- Draft §5.4(b)(3), lines 167-170, reads the same as adopted 4.4(b)(3).

Cited by: `flows/05-adverse-action-cascade.md`.

## `ATOM-GOV-R23-09` to `ATOM-GOV-R3-07`: When a privilege expires, and renewing it (Rule 3.5(a))

Added 2026-10-02 (SCRUM-39).

- **Draft**, Rule 3.5(a), PDF page 9, lines 167-171, as amended (checked against the page image: "extend the expiration date of" is struck, "renew" and the last sentence are inserted): "The expiration date of the qualifying license shall be the expiration date that was in effect on the date the PA applied for the compact privilege. Any renewal of the qualifying license does not automatically renew the compact privilege. The PA must follow the procedure set forth in this Rule in order to maintain any existing compact privilege(s)."
  **Adopted**: see `ATOM-GOV-R3-07`. Two additions: the first sentence adds "or the qualifying license is voluntarily terminated by the PA", and the last sentence adds "in accordance with Section 4.A of the model legislation".

Cited by: `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `flows/04-expiration-and-renewal.md`, `flows/06-state-machines.md`.

## `ATOM-GOV-R5-03` to `ATOM-GOV-R4-03`: What the remote state must verify and submit (Rule 4.3(d))

Added 2026-10-02 (SCRUM-39).

- **Draft**, Rule 5.3(d), `pa-draft-rules-2_3_5.pdf`, lines 135-141: "As a Remote State, a Participating State shall verify and submit the following information for each PA applying for or holding a Compact Privilege in the Remote State: (1) Compact Privilege issue date, status, expiration date and privilege number or other unique privilege identifier issued by the remote state; (2) Adverse actions against a Compact Privilege; and (3) The existence of Significant Investigative Information."
  **Adopted**: see `ATOM-GOV-R4-03`. One addition: "where applicable", after "shall verify and submit".

Cited by: `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/01-end-to-end-privilege-issuance.md`, `flows/03-payment-and-remote-state-issuance.md`.

## Atoms quoting draft text the adopted rules left out

Added 2026-10-02 (SCRUM-39). These two atoms quote draft text that the adopted rules left out, with nothing in its place. Each is marked `status: superseded` with `superseded-by: none`. The questions they leave open are tracked as tensions in `evidence/tensions/`.

| Old atom | What it covers | Adopted text that applies | Open question | Cited by |
|---|---|---|---|---|
| `ATOM-GOV-R23-01` | Tests for picking a state of qualifying license | Rule 3.4(a)(2) | `TENSION-02` | `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/02-sql-eligibility-verification.md` |
| `ATOM-GOV-R23-11` | Privileges staying active after the license's expiry date | Rule 3.5(a) | `TENSION-03` | `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `flows/04-expiration-and-renewal.md`, `flows/06-state-machines.md` |

### `ATOM-GOV-R23-01`: Tests for picking a state of qualifying license

- **Draft**, Rule 2 §2.1(a), PDF pages 2-3, lines 64-78, as amended: "The PA shall designate a Participating State as the state of qualifying license for purposes of registration for a compact privilege through the Compact if the PA possesses a full and unrestricted license to conduct medical services in that state, and the state is: (1) The state of primary residence for the PA, or (2) The state where active medical services occur, or (3) The location of the PA's current employer, or (4) If no state qualifies under subparagraph (1), subparagraph (2), or subparagraph (3), the state designated as state of residence for purposes of federal income tax. (5) A service member, or the service member's spouse, may retain their state of primary residence designation during the period the service member is on active duty."
- In the redline, "at least twenty-five percent of the" is struck through in (2), and "active" is inserted (PDF page 2, lines 69-70). The atom quotes the struck words as live text, because the converted file lost the strike-through.
- **Adopted**, Rule 3, Compact Privilege (adopted 2026-04-06), 3.4(a)(2), PDF page 4, lines 118-121: "At the time of application designate a Participating State as the state of qualifying license for purposes of eligibility for a compact privilege through the Compact if the PA possesses a full and unrestricted license to conduct medical services in that Participating State."
- **Statute**, Section 5.A, PDF page 6, lines 161-164: "Upon a Licensee's application for a Compact Privilege, the Licensee shall identify to the Commission the Participating State from which the Licensee is applying, in accordance with applicable Rules adopted by the Commission, and subject to the following requirements:"
- **Commission records on the tests:**
  - Rules Committee, 2025-02-24, PDF page 3, lines 94-95: "Since there are concerns about rulemaking authority on 2.2.A 1-5, this section is tabled. Chair will seek legal counsel to confirm authority."
  - Executive Committee, 2025-03-12, PDF page 4, lines 122-124, N. Kalfas: "With the addition of memo and the rules committee member's statement, it would not be appropriate for committee to move forward with a rule that further defines qualifying license. No I do not think the commission has authority."
  - Executive Committee, 2025-03-12, PDF page 5, lines 135-137, motion passed: "Jamie Alley motions to send the draft back to Rules Committee to be discussed with the new Rules chair, memo from compact drafting attorneys and memorialized legal opinion from N. Kalfas."
  - Rules Committee, 2025-07-10, PDF page 3, lines 73-74, L. Monick: "Now that we have taken out requirements for designating a state of qualifying license in 2.1a".
  - Rules Committee, 2025-11-10, PDF page 2, lines 33-34: "Chair Loucka clarifies that rule 1 is the rule on rulemaking, and rule 2 will be reserved for the rule on definitions, so the compact privilege process will remain rule 3."
- Adopted Rule 3.6(a)(3), PDF page 6, lines 217-218, still says "Meet the requirements of paragraph 2.1 with the new state of qualifying license,". No adopted rule has a paragraph 2.1. See `TENSION-02`.

Cited by: `evidence/signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md`, `flows/02-sql-eligibility-verification.md`.

### `ATOM-GOV-R23-11`: Privileges staying active after the license's expiry date

- **Draft**, Rule 3 §3.5(c), PDF page 9, lines 181-185, all inserted text: "The PA shall ensure that the qualifying license is properly renewed pursuant to the laws and regulations of the state of qualifying license. Should the qualifying license remain in an active status past the expiration date, any compact privilege issued under that qualifying license will remain active until the status of qualifying license is updated by the State of Qualifying License."
- **Adopted**: Rule 3 has no such text. Adopted 3.5(c) is the state's renewal duties, which the draft had as 3.5(d). The text that applies is Rule 3, Compact Privilege (adopted 2026-04-06), 3.5(a), PDF page 5, lines 169-176: "A compact privilege shall be valid until the expiration or revocation of the qualifying license used to apply for the privilege unless the privilege is terminated pursuant to an adverse action or the qualifying license is voluntarily terminated by the PA. The expiration date of the qualifying license shall be the expiration date that was in effect on the date the PA applied for the compact privilege. Any renewal of the qualifying license does not automatically renew the compact privilege. The PA must follow the procedure set forth in this Rule, in accordance with Section 4.A of the model legislation, in order to maintain any existing compact privilege(s)."
- **Commission record**, Rules Committee, 2025-02-24, PDF page 4, lines 116-123: "3.5.C Was intended to respond to the Maine example in order to use active status versus expiration date." "There is a concern that this could create a scenario for unlicensed practice as most states use a date of expiration instead of letting practice continue after that date." "S. Loucka – edit recommendation: We might walk back this section to represent the majority." "T. Terranova confirms that the Maine board can and will need to address this as it seems unique to them."
- See `TENSION-03`.

Cited by: `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `flows/04-expiration-and-renewal.md`, `flows/06-state-machines.md`.

## Atoms with the same wording in the adopted rules

Added 2026-10-02 (SCRUM-39). These atoms quote draft text that reads the same in the adopted rules. Each was checked word for word against the adopted rule PDF. Each keeps its draft source and gets one `adopted-text:` line in its front matter.

| Atom | Adopted section | Note |
|---|---|---|
| `ATOM-GOV-R23-02` | Rule 3.6(a) | Same meaning. The adopted text says "state of qualifying license" where this quote says "SQL". |
| `ATOM-GOV-R23-03` | Rule 3.2(a)(1)-(3) | Same wording |
| `ATOM-GOV-R23-04` | Rule 3.3(a)(5) | Same wording |
| `ATOM-GOV-R23-07` | Rule 3.4(c)(1)-(4) | Same wording |
| `ATOM-GOV-R23-08` | Rule 3.4(d) | Same meaning. The adopted text drops the "and" before "receipt of the information". |
| `ATOM-GOV-R23-10` | Rule 3.5(b) | Same wording |
| `ATOM-GOV-R5-01` | Rule 4.2(g) | Same wording |
| `ATOM-GOV-R5-04` | Rule 4.3(e)(1)-(5) | Same wording |
| `ATOM-GOV-R5-06` | Rule 4.5(b) | Same wording |
| `ATOM-GOV-R5-08` | Rule 4.6(a) | Same wording |
| `ATOM-GOV-R5-09` | Rule 4.6(b) | Same wording |
| `ATOM-GOV-R5-10` | Rule 4.2(f) | Same wording |

## Other atoms checked

Added 2026-10-02 (SCRUM-39). The 15 model legislation atoms and the 6 RFP and RFP questions atoms were checked word for word against their PDFs. All match. They are not rules, so the adoption of Rules 3 and 4 does not change them.

`ATOM-GOV-RFP-07` quotes the RFP correctly, but the number has changed since. The RFP (October 2025) says: "As of October 2025, the PA Compact has 19 member states." The Commission's August 2026 newsletter (page 2) says: "As of August 28, 2026, there are 29 Compact Member States." No file cites `ATOM-GOV-RFP-07`.

## Minutes atoms that quoted only part of an exchange

Added 2026-10-02 (SCRUM-39). These three atoms quote Rules Committee minutes word for word, but leave out the turns around them, which change what the quote means. Each now has a new atom quoting the full exchange from the same minutes. The old atom is kept and marked `status: superseded`.

| Old atom | New atom | Minutes | What the new atom adds | Cited by |
|---|---|---|---|---|
| `ATOM-GOV-M0825-01` | `ATOM-GOV-M0825-03` | 2025-08-25, PDF page 5, lines 145-165 | L. Monick's question, then counsel N. Kalfas: "I do not see how the commission will generate some of this information." J. Alley replies that the system must hold it "even if it is provided by a participating state." | `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/02-sql-eligibility-verification.md` |
| `ATOM-GOV-M0825-02` | `ATOM-GOV-M0825-04` | 2025-08-25, PDF pages 6-7, lines 223-243 | Counsel N. Kalfas: "allow the state to put in what they have, and the system could notify states what the most current information is according to state records." | `evidence/signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md`, `flows/02-sql-eligibility-verification.md`, `flows/07-domain-event-catalogue.md` |
| `ATOM-GOV-M1110-02` | `ATOM-GOV-M1110-04` | 2025-11-10, PDF page 4, lines 101-114 | J. Alley: "there is a need to know the PAs in your state who are practicing with your state as their SQL". Chair Loucka: "it has become apparent that it is necessary." | `evidence/signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md`, `evidence/signals/SIGNAL-the-system-does-the-heavy-lifting-for-states.md`, `flows/04-expiration-and-renewal.md` |

What the adopted rules say on each:

- Denials: Rule 4.3(c)(14), the state of qualifying license verifies and submits "Any denial of licensure, and the reason(s) for such denial". Rule 4.2(b)(5), the system maintains "License and privilege denials and any periods of Compact participation ineligibility resulting therefrom".
- Address: Rule 4.3(c)(6), the state verifies and submits the "Primary residence address of record". Rule 3.4(a)(3), the PA reports a change of address "within thirty (30) days". Rule 4.3(e)(1), the system keeps "All primary residence address changes provided by the participating PA".
- Renewal: Rule 3.5(c)(2), the state of qualifying license shall "Issue notice, through the data system, to the Compact Commission verifying or denying the PA's eligibility to continue participation in the Compact."

Three other minutes atoms were checked and kept as they are: `ATOM-GOV-M0209-02` (word for word), `ATOM-GOV-M0209-03` and `ATOM-GOV-M0209-05`. The last two use "…" to skip lines in the 2026-02-09 minutes (PDF page 4, lines 110-115, and page 5, lines 131-134). The skipped lines are the committee calling each change not substantive and agreeing to it. Both changes are in the adopted Rule 3 (3.4(e) and 3.6(a)).

## Signals and tension re-checked

Added 2026-10-02 (SCRUM-39). After the atom changes above, each signal and `TENSION-01` was read against the adopted Rules 3 and 4. Their text is unchanged. Claims to re-check are listed in each file's "needs review" note, with the adopted text beside them.

| File | Claims to re-check |
|---|---|
| `signals/SIGNAL-disciplinary-data-is-confidential-by-default.md` | 1: which records a state can see (Rules 3.4(e), 4.6(c)) |
| `signals/SIGNAL-privilege-life-is-tied-to-the-qualifying-license.md` | 2: "the same privilege number"; who tracks renewals (Rule 3.5(c)(2)) |
| `signals/SIGNAL-the-sql-is-the-sole-eligibility-authority.md` | 2: who runs the background check (Rule 3.4(b)(2)); the designation basis (not adopted) |
| `signals/SIGNAL-the-system-does-the-heavy-lifting-for-states.md` | 1: who tracks which PAs use which state (Rule 3.5(c)(2)) |
| `signals/SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance.md` | 3: denials (Rule 4.3(c)(14)); address (Rule 4.3(c)(6)); what counts as "submit" (open, Confluence Q4) |
| `tensions/TENSION-01-adverse-action-notification-breadth.md` | 1: Rule 4.6(c) is not listed |
