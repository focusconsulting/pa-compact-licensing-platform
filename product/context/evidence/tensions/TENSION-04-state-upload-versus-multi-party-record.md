---
tension-id: TENSION-04-state-upload-versus-multi-party-record
date-surfaced: 2026-10-05
surfaced-by: CTO (Kalish), on replacing the SOW with the redline response v2
status: open
---

# TENSION-04: Do states upload their licensing data, or is the uniform data set filled in by several parties as the PA applies?

The uniform data set is the record the Commission's data system keeps for each PA (physician assistant) who applies for or holds a compact privilege, the right to practice in another member state (the rules say "Participating State") without a second license. The flows in `product/context/flows/` were designed so that this record is filled in as the PA applies: the PA enters their own details, staff in the PA's state of qualifying license confirm them on a screen, and each other state adds its privilege details when it issues. The current SOW (statement of work), the redline response v2, now also lists states uploading PA and licensure data, by file and by API. No record says how the two fit together.

## Positions

What each record says, source by source.

- **The statute puts the duty on the state.** PA Compact Model Legislation, §8.B (`ATOM-GOV-ML-14`): "a Participating State shall submit a uniform data set to the Data System on all PAs to whom this Compact is applicable (utilizing a unique identifier) as required by the Rules of the Commission, including: 1. Identifying information; 2. Licensure data; ...".
- **Adopted Rule 4, Compact Data System (adopted 2026-04-06), 4.3(a) and (b)**, converted source lines 299-300: "The Compact Commission, through its Data System, shall maintain a uniform data set for each PA who applies for or holds Compact Privileges." and "each Participating State shall verify and submit the required information to create a uniform data set for each PA who applies for or holds Compact Privileges."
- **Rule 4, 4.3(c)** (`ATOM-GOV-R4-01`, PDF lines 115-134): the state of qualifying license "shall verify and submit" fourteen items "for each PA applying for or holding a Qualifying License", from full legal name to license number, status and dates, adverse actions, and denials of licensure.
- **Rule 4 names no mechanism.** "Verify and submit" is not defined. Nothing in 4.3 says whether a state submits by confirming fields in the data system, by sending a file, or by an API.
- **Rule 4, 4.3(e)**, converted source lines 387-391: the uniform data set "shall also include" the PA's own applications, attestations and certifications, and the documents a state submits to verify or decline eligibility. So under the rule the record has more than one contributor.
- **The two texts cover different sets of PAs.** The statute says "all PAs to whom this Compact is applicable". Rule 4.3(a) and (b) say "each PA who applies for or holds Compact Privileges". The first could be read as every licensed PA in a member state; the second is only PAs who come to the compact.
- **What the Rules Committee said, 2025-08-25** (`ATOM-GOV-M0825-04`, minutes PDF pages 6-7, lines 223-243). J. Alley: "If a PA comes to the system to update their address, that would be populated to all the member states. If the state of qualifying license had concerns, they could follow up with the PA." N. Kalfas, the Commission's counsel: "You can make it incumbent upon the practitioner to provide the information but also allow the state to put in what they have". In the same meeting (`ATOM-GOV-M0825-03`, PDF page 5, lines 145-165) Kalfas said: "With other commissions the states are heavily informing the function of the data system".
- **The RFP questions and responses** (`pa-compact-rfp-questions-responses.md`). Response 22.1, line 72: "There is no expectation for external state system development. There will likely be a need for API capability for internal commission use and ensuring ease of interface between the commission data system and external state systems." Response 43.1, line 138: "API functionality is an anticipated need but will be defined further through the agile development process."
- **The earlier SOW (version 1.0, 2026-03-09) had no state upload.** Its state portal list was: portal authentication, verify qualifying licenses, issue compact privileges, access practitioner records, update license or privilege status, upload disciplinary information. Its §2.2 listed "Real‑time or API integrations with state licensing systems" as out of scope.
- **The SOW redline response v2** (`product/context/PA Compact Data System SOW - Focus Consulting.md`) adds three things:
  - §2.1, state portal list, line 73: "Upload PA identifying information and licensure data". The words "identifying information" and "licensure data" are the statute's (§8.B.1 and 2).
  - §2.1, state portal list, line 88: "Upload compact uniform data set, as defined by compact policy, via API capability."
  - §3, Phase 2, line 153: "State licensee data ingestion (multi-format: API and upload). Architecture and ingestion design will be validated using mock data developed collaboratively by the Commission and Focus. To support this, the Commission will identify two or more representative member states and work with Focus to understand their anticipated data structures. ... No dependency on production data from member states is required to begin this work."
- **The same SOW limits it.** §2.1, line 48, calls its list "the anticipated universe of features", "not a fixed requirements list". §2.3, line 129: "Actual state coordination, state system integration, and live pilot operations are out of scope for this period of performance." §2.2 still lists "Real‑time or API integrations with state licensing systems" among capabilities that "may be added". "Verify qualifying licenses" is no longer in the state portal list; "Issue compact privileges" still is.
- **No Commission minutes on disk discuss a state upload or a state API.** Rules, Executive and Full Commission records through 2026-09-28 were searched. The only API discussion is the Executive Committee minutes of 2026-05-13, line 459, on "API integration between NCCPA and the compact data system".
- **The reference implementation works the other way round.** In CompactConnect, the data system other compacts use, states upload license records in bulk, a PA can only create an account that matches an uploaded license, and eligibility is a flag in the upload (`product/context/reference/compactconnect-crosswalk.md` §2).

## Why it matters

The two models differ on who starts the record and what the state's staff do.

| | Filled in as the PA applies (current flows) | State upload first (CompactConnect's model) |
|---|---|---|
| Who creates the PA's record | the PA, by signing up | the state, in a file or feed |
| How the license gets on file | state staff enter or link it while reviewing the application | it arrives before the PA applies |
| How eligibility is decided | state staff review and decide in the system | a flag in the upload |
| Whose data it is | the PA's, verified by the state | the state's |

Six things are undecided:

1. **What the upload is for.** It could pre-load licenses so staff do not type them, replace the review screen for states that prefer a feed, or become the main source of identity data. The SOW does not say.
2. **Which PAs a state uploads.** Every PA it licenses (the statute's wording), or only PAs who have applied (Rule 4's wording). The first is a bulk feed of people who may never use the compact; the second can only follow an application.
3. **Which value wins when the upload and the PA disagree**, for example on an address or a name. The 2025-08-25 discussion settled this for address before any upload was planned.
4. **Whether an uploaded field counts as verified on arrival**, or still needs staff to confirm it on the review screen. Rule 3.4(b) has the state of qualifying license evaluate eligibility through the data system either way.
5. **What the state of qualifying license does once its data is uploaded.** Today's flows give its staff a queue and a review screen: they confirm the PA's details, enter or link the license, record that the background check is done, and decide eligible or denied. With an upload, staff could still do all of that, could review only where the upload and the PA's entries differ, or could do nothing per PA because the upload is taken as the state's answer. The SOW removed "Verify qualifying licenses" from the state portal list and added the uploads, which can be read as moving that work from a person to a feed. It does not say so.
6. **What the system does with uploaded data after it arrives.** Whether a later upload that shows a license expired, lapsed or disciplined ends the PA's privileges automatically, as a status change entered by staff does in `flows/05-adverse-action-cascade.md`, or only prompts staff to act. Whether the uploaded expiry date is the one a privilege is pinned to (see `TENSION-03-license-active-past-printed-expiry`). How often a state is expected to send data, and what a missing record in a later upload means. And, if a state uploads every PA it licenses, what the Commission holds and who can see it for PAs who never apply: Rule 4.3(c) includes the social security number and date of birth.

This affects `flows/01-end-to-end-privilege-issuance.md` (Phase 0 sign-up and the "Where this differs from CompactConnect" table), `flows/02-sql-eligibility-verification.md` (the "license already on file" branch, the field ownership table and the Q-04 question), `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance` (its last implication assumes no state data feed at pilot), and tickets L-01, L-03, L-05 and U-01 in `product/backlog/mvp-ticket-breakdown.md`. That file also lists "bulk CSV license upload" as dropped because it was not in the SOW, and its Q-04 asks only whether states pre-load by manual entry.

## Proposed resolution path

- **Rule-required, whichever way this goes:** the state of qualifying license evaluates eligibility and gives notice through the data system (Rule 3.4(b)), and the record keeps the PA's applications and attestations and the state's verification documents (Rule 4.3(e)). An upload cannot remove the state's eligibility decision or the PA's own entries. Whether that decision has to be made by a person on a screen, PA by PA, is point 5 above and part of the counsel question below.
- **Focus preference until the Commission answers:** treat upload as one more way for a state to write its own fields (license number, status, issue and expiration dates), landing as the "license already on file" record that staff compare with what the PA entered. Keep sign-up open to any PA, keep the staff review as the eligibility decision, and do not match accounts to uploaded records. Reason: this is the only reading consistent with every source above. Rule 4.3(a) and (b) scope the record to PAs who apply or hold privileges, the 2025-08-25 discussion has the PA enter and the state add "what they have", and §2.3 puts real state system integration outside this period of performance.
- **Focus preference:** design the ingestion format against the mock data the SOW describes (§3, Phase 2), and do not build account matching or an upload-driven eligibility flag until the questions below are answered.
- **Questions for the Commission's Product Manager**, to add to the Commission question list on Confluence (Sprint 0 Questions, Q01 to Q25: <https://focusdigital.atlassian.net/wiki/spaces/PC/pages/62881793>):
  - "The SOW lists states uploading PA identifying information and licensure data, and uploading the uniform data set by API. What should the upload do: pre-load license records before PAs apply, replace on-screen entry for states that prefer a feed, or something else?"
  - "Which PAs would a state upload: every PA it licenses, or only those who have applied for or hold a compact privilege (Rule 4.3(b))?"
  - "When an uploaded value and a value the PA entered disagree, which does the system keep, and who is told?"
  - "Once a state uploads its data, what do its staff still do for each PA who applies? Do they review and decide every application in the system, review only where the upload and the PA's entries differ, or is the upload the state's answer?"
  - "After the first upload, how is the data used? If a later upload shows a license expired, lapsed or disciplined, should the system end the PA's privileges on its own, or tell staff and wait? How often would a state send data?"
  - "If a state uploads PAs who have not applied to the compact, should the system hold their records, including social security number and date of birth, and who may see them?"
- **Question for the Commission's rules counsel**, same list: "Does a state meet 'verify and submit' in Rule 4.3(b) and (c) when its staff confirm the fields on a screen in the data system, with no file or feed? And does a field that arrives in a state upload count as verified without that confirmation?" This is the counsel question already folded into Q-04.
- Record the answers here under `## Resolution`. If the answers change the flows, the edits are made in flows 01 and 02 and the signal above.
