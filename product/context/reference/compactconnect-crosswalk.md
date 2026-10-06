---
artifact: crosswalk
status: draft
authored-by: CTO (Kalish)
last-revised: 2026-09-30
reference: "../CompactConnect @ 83596ab4 (2026-09-28) — github.com/csg-org/CompactConnect"
inputs: [mvp-jira-tickets.md, mvp-ticket-breakdown.md v4.2, product/context/flows/ FLOW-01..07]
---

> **Needs review (2026-10-05, SCRUM-39).** Two places say bulk upload is "not in SOW": the paragraph that says "Ours drops bulk upload (not in SOW)", and the row "Bulk license upload, military status, home-state change, printable proof". That was true of SOW version 1.0. The current SOW in this repo (`product/context/PA Compact Data System SOW - Focus Consulting.md`), §2.1, now lists:
>
> - **State upload:** "Upload PA identifying information and licensure data", and "Upload compact uniform data set, as defined by compact policy, via API capability".
> - **Military status:** "Verify military affiliation", for the PA.
> - **Still not listed:** home-state change and printable proof.
>
> See `TENSION-04-state-upload-versus-multi-party-record` and `flows/README.md`. Remove this note when the file is updated.

# CompactConnect crosswalk — product analysis

CompactConnect (CC) is the data system CSG and InspiringApps built for the Audiology/SLP, Counseling, and OT compacts. It demoed to the full PA Commission on 25 April 2025 and the Counseling compact went live on it in October 2025. This document maps what we are building, journey by journey and screen by screen, onto what CC already does, so that product tickets can point at a CC screen and say "like this" or "like this, except", and so that every place we differ has a stated product reason.

**Default: follow CompactConnect.** Where a row below says nothing else, the CC screen is the wireframe reference and the CC behaviour is the requirement. Deviations name the compact rule, the SOW clause, or the decision (`D1`–`D15` in `mvp-ticket-breakdown.md` §2.1) that forces them.

Two sets of pictures back this document. **Our own captures** of every screen, taken 2026-09-30 from the CompactConnect app running locally on its demo data, are in `compactconnect-screens/` next to this file (index in its README; §10 names the file for each screen). **CompactConnect's own staff screenshots**, referenced as `image.png`, are in the corpus at `product/context/research-corpus/sources/compactconnect-staff-user-guide-images/`, alongside the ingested staff guide (`sources/compactconnect-staff-user-guide.md`) and backend design notes (`sources/compactconnect-backend-design.md`). Screen names in `code` are CC pages and components under `../CompactConnect/webroot/src/`.

## 1. What CompactConnect is, in product terms

Three personas and a public lookup, one web app:

- **Practitioner.** Registers by proving they match a license their home state already uploaded. Sees a dashboard of their home-state license and privileges. Buys privileges in other states in one checkout: pick states, accept attestations, pay by card, done. Privileges are issued the moment payment clears; no state touches the purchase. Gets email when a privilege is bought, deactivated, encumbered, or about to expire.
- **State staff.** Upload license data (CSV or system integration) with a flag saying whether each license is compact-eligible. Search practitioners, view details, deactivate a privilege, report discipline ("encumber") on a license or privilege, open or close an investigation, configure the state's fees and notification emails, manage the state's users.
- **Compact staff.** Everything state staff can do across all states, plus compact-level fees, the Authorize.net account, and turning states "live". Their operational view is search plus a weekly transaction-report email; there is no dashboard.
- **Public.** Search a practitioner by name and state and see their privileges and history.

## 2. Where the PA compact is a different product

Four differences come from the PA rules, not from taste. Everything else in this document sits under them.

| | CompactConnect | PA Compact Data System | Why |
|---|---|---|---|
| **Who decides eligibility** | The home state says so when it uploads the license (`compactEligibility` flag). The system never asks a state to decide anything about a person. | The PA applies to the Commission, designates a State of Qualifying License (SQL), and the SQL reviews the application in the system: verifies the license, runs the background check, confirms the SQL basis, records the verdict. | Rule 3 §3.4(b) gives the SQL four duties "through the data system". The Commission asked that the system, not the state, do the heavy lifting (Nov 10 2025). |
| **Who issues the privilege** | Payment is issuance. The Commission's own minutes of the CC demo: "No action required by the privilege state to issue the privilege." | The PA pays up front, then each remote state issues (or denies) from a queue. | Rule 3 §3.4(d): the remote state issues on receipt of fees, information, and the SQL's verification. |
| **How the PA gets an account** | Self-registration only succeeds if name, date of birth, SSN last four, and license type match an uploaded license. | Anyone can create an account; identity is established later by the SQL's review. | Follows from the first row: there is nothing to match against until the SQL has verified. |
| **Whose data it is** | The state's. The practitioner sees their state-uploaded name, address, and license read-only and attests it is correct. | The PA's. The PA enters the uniform data set (names, sex, DOB, NPI, address, NCCPA certification, education) and the SQL verifies it. | Rule 4/5 §5.3 puts the uniform data set on the PA's application; every address and email change is kept as history. |

What is **the same** and needs no discussion with the Commission: card payment through Authorize.net's lightbox with fees itemised per state; attestations as versioned legal texts the PA accepts by checkbox; a privilege that expires when the qualifying license expires; discipline reported by a state cascading to privileges; email as the only channel; two-factor login for everyone; the same four staff permissions (read private, read SSN, write, admin) granted per state.

## 3. The practitioner journey

### 3.1 Getting in

| Step | CompactConnect | Ours | Posture |
|---|---|---|---|
| Landing | One page, three doors: "Verify a compact privilege", "Register as Practitioner", "Login as Practitioner", "Login as Compact or State Staff" (`PublicDashboard`; `staff_login.png`). | Same three doors. | Follow |
| Register | Two screens: license type, home state (states not yet live are greyed "(not live)"), first and last name, SSN last four, date of birth, email; then a confirmation summary; then "if your information is valid you will receive an email". Deliberately never says whether a match was found. (`RegisterLicensee`) | Email, password, then a two-factor (authenticator app) enrolment step. No matching. Keep CC's two-screen confirm and the neutral copy that never confirms whether an email is already registered. | Adapt |
| Login | Cognito's hosted login page, with a "locked out of your account?" recovery link on the landing page. | Our own login and two-factor screens so they sit inside the design system. | Adapt |
| Lost authenticator | Self-service: re-prove identity (same fields as registration) plus password, receive an email link, the account is rebuilt and the authenticator re-enrolled (`MfaResetStartLicensee`, `MfaResetConfirmLicensee`). | **Not in the backlog.** Default: at pilot an administrator resets it after an out-of-band check. | Gap, see §8 |
| Session | Logged out after ten minutes idle with a thirty-second warning. | Same. | Follow (add to U-01) |

### 3.2 Profile and account

| | CompactConnect | Ours | Posture |
|---|---|---|---|
| Account page | Name (read-only for practitioners), email (editable: a code is emailed to the new address and must be entered within 15 minutes; the old address is told), change password, military status, change home state (`Account`, `UserAccount`). | Profile form for the uniform data set with the same code-verified email change; a read-only summary; consent to service of process and the 30-day address-change duty stated in the copy. No home-state change, no military status. | Adapt |
| Personal information | Shown read-only at purchase: name, home state, license number and expiry, address, state-provided email, account email, phone; the practitioner attests it is correct (`PrivilegePurchaseInformationConfirmation`). | The same summary layout is our "confirm profile" step, but the fields are the PA's own with an Edit link. | Adapt |

### 3.3 Dashboard

CC's `LicenseeDashboard` is the reference for ours and needs almost no change in layout:

- "Welcome, {name}".
- A primary action "+ Obtain Privileges". When it is unavailable, a "Why is this unavailable?" link opens a plain-language list of the reasons (no eligible license, discipline on file, a wait period after discipline was lifted, a pending document review). Ours uses the same device for "Apply for participation" / "Apply for privileges" with our reasons (application in review, information requested, not yet eligible, two-year bar).
- A "Home state" block, then one card per home-state license (`HomeStateBlock`, `LicenseCard`). Ours: an "SQL" block and the qualifying-license card, with "Verified by {state} on {date}" where CC shows "Compact Eligible".
- A collapsible "Privileges" section, a clock icon that explains "privileges expire when your license does", and one card per privilege: state, Active/Inactive pill, active from, expires (red when past), privilege number, discipline status, "View details" (`PrivilegeCard`; the card layout is visible in `practitioner_details_page.png`).

What we add that CC does not have: an **application timeline** (submitted → under review → information requested, with the SQL's note → eligible or denied, with reason and appeal note). We draw it with CC's history timeline component rather than inventing a new one.

### 3.4 Privilege detail and history

Follow CC exactly (`PrivilegeDetail`, `PrivilegeDetailBlock`, `PrivilegeHistory`; `privilege_summary.png`): a summary card (issued, status as "Active (Expires: date)" / "Inactive (Expired: date)" / "Inactive (Deactivated)", privilege number, discipline status) and a vertical timeline of events with a "Today" marker. Under 90 days from expiry the timeline shows a caution icon and "Expiring in N days". Event names come from one vocabulary: issued, renewed, expired, deactivated, disciplinary action, disciplinary action lifted. CC's "Privilege purchased" becomes "Privilege issued".

### 3.5 Applying for participation (new, Phase 1)

CC has no equivalent, but its **purchase wizard is the pattern** for every wizard we build: a step indicator, Next / Back / Cancel on every step, Cancel returns to the dashboard, refreshing or deep-linking drops you back at the first incomplete step (`PrivilegePurchase`). One product difference: CC keeps the wizard state in the browser only; ours saves a draft on every Continue so a PA can stop and come back.

| Our step | CC reference | Posture |
|---|---|---|
| Intro: what to expect, what you will need | — | New |
| Confirm profile | `PrivilegePurchaseInformationConfirmation` layout | Adapt |
| Designate SQL and basis (primary residence, ≥25% of practice, employer, tax residence, service member) | State picker from `UpdateHomeJurisdiction` (each state labelled with why it does or does not qualify) | New |
| Qualifying license details | If the state pre-loaded it, "pick your license" is CC's `PrivilegePurchaseLicense` select | New |
| Documents (proof of SQL basis, NCCPA card; which are required is Q-07) | Single-file upload with "may take a minute to process" from `MilitaryStatusUpdate` | Adapt |
| Attestations | `PrivilegePurchaseAttestation`: each attestation fetched as versioned legal text, "not under investigation / under investigation" as a radio pair, the rest as required checkboxes | Follow |
| Background-check acknowledgement | — | New |
| Review and sworn statement (checkbox + typed name + timestamp) | The two acknowledgement checkboxes on `PrivilegePurchaseFinalize` | Adapt |
| Submitted | `PrivilegePurchaseSuccessful` | Follow |
| Information requested → resubmit (the SQL's note at the top, documents step to answer it) | — | New (D15) |

**Attestation texts.** CC's ten attestations are the drafting base for Q-06. Six carry over nearly verbatim (true information, current address with consent to service of process and the duty to report changes, no current discipline, no discipline in the past two years, the under-investigation pair, the scope-of-practice text with its two-year-bar warning). Two are reworded (home-state residency becomes the five SQL bases; "under investigation" narrows to the SQL only per the Feb 9 2026 minutes). Two are dropped (military). Four are new from the model legislation (ARC-PA graduate, current NCCPA, no disqualifying conviction, no DEA action).

### 3.6 Applying for privileges and paying (Phase 2)

This is CC's core flow and we follow it step for step. Only the ending changes: CC says "purchased", we say "sent to {states} for issuance".

| Step | CompactConnect (`PrivilegePurchase*`, `SelectedStatePurchaseInformation`) | Ours | Posture |
|---|---|---|---|
| Who may start | An eligible home-state license, no active discipline, nothing lifted in the last two years, no document under review. | Participation `eligible`, no two-year bar. | Adapt |
| Select states | Checkbox grid of member states sorted by name; the home state and any state where an active privilege already exists are greyed out; states not yet live do not appear; up to 20 per checkout. | Same. | Follow |
| Per-state panel | Appears as each state is ticked: expiration date (= license expiry), state fee, administrative fee, subtotal, an "I attest I have completed the jurisprudence exam" checkbox with a "More info" link where the state requires it, and a scope-of-practice checkbox. Ticking either opens the full text with Back / "I understand"; closing without confirming unticks. | Same panel. Each proof the state configured (jurisprudence, supervision agreement, prescriptive authority, other) appears as either CC's checkbox-with-modal or a file upload. "More info" is the state's practice-requirements page. | Follow |
| Attestations | As in §3.5. | Same. | Follow |
| Payment summary | One line per state ("{State} Compact Privilege State Fee"), "Administrative Fee ($X × N)", an optional card-fee line, Total; two required acknowledgements: "If purchased, these privileges will expire on {date}." and "All compact privilege purchases are final. Refunds will not be issued." The Pay button only activates once both are ticked. | Same, minus the military rate. Wording: "if issued". | Follow |
| Card entry | Authorize.net's lightbox opens over the page (card and billing address entered there, never on our site). | Same lightbox (D6). Its accessibility limits are documented as a known exception. | Follow |
| Result | Charged and issued in the same moment; receipt email with the itemised lines. | Charged; requests go to each state's queue; receipt email; then a second email when each state issues. | Adapt |
| Decline | Inline error, retry. | Same. | Follow |
| Transactions | None for the practitioner. | A simple list of what they paid, when, for which states. | New |

### 3.7 Notifications the PA receives

CC sends: purchase receipt, privilege deactivated (with the state's note), discipline reported or lifted on a license or privilege, expiry reminders at 30, 7, and 0 days, email-change code, account-recovery confirmation, military audit result. CC publishes an "issued" event but sends no issued email.

Ours: welcome, application received, information requested (a link, never the note body), eligible / denied (with appeal text), payment receipt, privilege issued / denied per state, deactivated, adverse action reported or lifted, expiry at 60 / 30 / 7 days (60 is the rule minimum), expired, email-change code. SII is never mentioned to the PA.

## 4. The state staff journey

### 4.1 Navigation and access

CC's staff app is a left sidebar: Upload data (write permission only), Manage users (admins), Search licensing data, Settings (admins), and at the bottom Account and Logout (`manage_users_tab.png`, `settings_tab.png`). Ours keeps the shape and swaps the items: Applications to review (as SQL), Privilege requests (as remote state), Practitioners, Settings, Account, Logout. Items appear only when the user's permissions allow them, as in CC.

Staff accounts are created by invitation (CC: an admin fills email, name, compact or state, and permissions; `invite_user_form.png`). Ours does the same by command line at pilot; the self-service user page (`user_management_page.png`) is deferred.

### 4.2 Settings

Follow CC's two-level settings closely; they are the most mature part of the product.

| | CompactConnect (`settings_tab.png`, `CompactSettingsConfig`, `StateSettingsList`, `StateSettingsConfig`) | Ours | Posture |
|---|---|---|---|
| Compact settings (compact admin) | Compact fee, optional card transaction fee, three email lists (operations, discipline notifications, summary reports), "Is licensee registration enabled?" which is one-way with a confirm dialog. Registration cannot be enabled until the Authorize.net account is entered. | Commission fee (default $0 until Rule 6), the same three lists, report recipients. Card fee deferred. Same one-way rules. | Follow |
| State list (compact admin) | A table of states with Status and an "Enable" button that makes a state live for privilege purchase, one-way with a confirm. State admins see "Edit" for their own state. | Same; "live" means a PA can pick the state as SQL or remote state. | Follow |
| State settings (state admin) | Fee per license type with an optional military rate, "Jurisprudence exam required?" with a link, the three email lists, "State is live" one-way toggle. A state admin of one state lands straight on this form. | One fee. Jurisprudence becomes a four-row proofs matrix (jurisprudence, supervision agreement, prescriptive authority, other), each "none / attestation / upload", plus a practice-requirements URL and a contact. | Adapt |
| Payment account (compact admin) | A screen to enter the Authorize.net login and key, validated against Authorize.net; three screenshots walk the admin through the card-code fraud filter settings (`authorize_net_*.png`). | Entered by Focus at pilot; the fraud-filter screenshots become our onboarding note for the Commission's Authorize.net administrator. | Deferred |

### 4.3 License data

CC states upload licenses in bulk by CSV or integration (`license_upload.png`) and never touch an individual record in the app. Ours drops bulk upload (not in SOW) and adds a **license entry form** for the SQL: number, status, issued, expires, renewal date, unrestricted. The card that shows the result is CC's `LicenseCard` (state, Active/Inactive pill, expires, license number, discipline status, and a free-text status line the state can write).

### 4.4 SQL eligibility review (new, no CC precedent)

The state-side half of Phase 1. CC has nothing like it; the nearest thing a CC state does is tick "compact eligible" on an upload. Design it first and test it in usability round 2.

- **Queue:** applications where my state is the SQL, with submitted date, age, days until the 60-day withdrawal, status. Borrow CC's list chrome: a "Viewing: {filters} ×" chip and an "Edit search" button (`license_list_view.png`).
- **Case view:** borrow CC's practitioner-detail layout (`practitioner_details_page.png`: alert banner, breadcrumb, name, state tags, collapsible sections) and add the four-item checklist (SQL basis, license verified, background check completed, attestations), the SQL's request-information control, and one decision control.
- **Actions:** verify license (links or creates the record), record the background-check completion date only (results never enter the system), request information (a note; the PA gets a link), decide eligible or deny with a reason. The decision is the rule's "notice to the Commission".
- **Withdraw eligibility:** confirm dialog patterned on CC's deactivate dialog; every privilege is cancelled at once and the PA and remote states are told.

### 4.5 Remote-state issuance (new, no CC precedent)

The state-side half of Phase 2. Same queue and case layout as §4.4: requests for my state, age against the 72-hour target (a dashboard target, not an SLA), and a case view showing the SQL's verdict and date, the license, attestations and any uploaded proofs, payment status, and the PA's contact details. Two actions: issue (assigns the privilege number) or deny with a reason. There is no in-app way to ask the PA a question at pilot; the state uses the contact details.

### 4.6 Practitioner records

| | CompactConnect | Ours | Posture |
|---|---|---|---|
| Search | Providers or Privileges (the latter exports CSV); first name, last name, home state, privilege state, purchase date range, military status, investigation status, discipline date range, NPI (`license_search_tab.png`). | Name, NPI, license number, privilege number, SQL state, privilege state, status. | Adapt |
| Results | First name, last name (sortable), home state, privileges as a list of states (`license_list_view.png`). | Same columns. | Follow |
| Who sees whom | Any staff user sees every practitioner in the compact; "read private" unlocks DOB, address, SSN last four. | A state user sees only PAs who use their state as SQL or hold a request or privilege there; the Commission sees everyone. | Deviate: Rule 4/5 §5.6(a). Tell pilot states, CC-experienced staff will expect the wider view. |
| Detail | Alert banner if under investigation; breadcrumb; name; home-state and license-state tags; collapsible "Personal information" (address, emails, DOB, SSN last four with "Reveal full SSN" for those permitted), "License details" (license cards), "Privileges" (privilege cards) (`practitioner_details_page.png`). | Same, plus sections for address and email history, applications with their notes, adverse actions, SII, and documents. SSN reveal asks for a reason and is logged. | Follow + extend |

### 4.7 Status changes and discipline

| | CompactConnect (`privilege_action_menu.png`) | Ours | Posture |
|---|---|---|---|
| Deactivate a privilege | Compact admin only. Card menu → Deactivate → required note → confirm. The PA and the state are emailed. | Issuing state or Commission. Same dialog. | Follow |
| License status change | Arrives with the next upload; the system classifies it as renewal, deactivation, or other and cascades a deactivation to every privilege on that license. | A form on the license card: expired, lapsed, inactive, reinstated, terminated, with an effective date. Same cascade. A reinstated license does **not** reactivate privileges (CC does on renewal). | New form, same effect |
| Report discipline ("encumber") | State admin only. Card menu → Encumber → action type (fine, reprimand, probation, suspension, revocation, …), NPDB category (multi-select), start date. On a license it marks every privilege of that license; on a privilege, only that one. | Same dialog with the same two pick-lists, plus a summary, order date, emergency flag, public flag, optional attachment, and an SII checkbox with a contact. On a qualifying license it **deactivates** every privilege rather than marking them. | Follow + extend; effect deviates per ML §4.B / §6.G |
| Lift | Card menu → Remove encumbrance → pick the action(s) and give an end date. A privilege stays encumbered while any action is unlifted. | Same. Lifting does not reactivate; the PA may reapply two years after the end date. | Follow; reactivation deviates |
| Investigations / SII | Card menu → Add investigation (confirm) / End investigation (with or without an encumbrance). Shown to staff as a red banner and a "Investigation" discipline status; never on the public site. | A flag, contact, and short description on the adverse-action form; closable; visible to state and Commission users only. | Adapt |
| Who is told | The practitioner, the acting state, and every other state where the practitioner holds a license or privilege, via each state's discipline email list. | The same set. This is the Q-20 default; CC is the precedent to cite. | Follow |
| Confidential records | None; all discipline is public (without type and category). | A "public / not public" flag; non-public records never reach the public site and carry a "confidential — do not redisclose" banner for staff. | New, Rule 4/5 §5.5(c) |

## 5. The Commission journey

CC gives compact staff the state tools across all states, settings, and a weekly transaction report by email. It has no dashboard.

- **Dashboard (new):** five tiles (applications by status, requests by status, issued in the last 30 days, median time to issue against 72 hours, aging queues), each drilling into search.
- **Reports:** CC emails each compact a weekly and monthly financial summary and transaction detail CSV, and each state its own rows only. Ours is an on-demand reports page with date and state filters producing the same CSVs (privileges issued/expired/deactivated, applications and time to decision, transactions by state, adverse actions); state users get their own rows only, as in CC. The scheduled email is deferred.
- **Overrides:** CC's compact admin can deactivate any privilege and approve military documents. Ours: deactivate with note only.

## 6. The public journey

| | CompactConnect (`PublicLicensingList`, `PublicLicensingDetail`, `PublicPrivilegeDetail`) | Ours | Posture |
|---|---|---|---|
| Search | Choose a compact, then first name, last name, state; a last name is required if a first name is given. Only practitioners who hold a privilege appear. | Both names together, or an exact privilege number. Same "only privilege holders" rule. | Adapt |
| Practitioner page | Name, home state, one card per privilege (state, status, active from, expires, privilege number, discipline status, View details). No address, DOB, or contact details. | Same, with the fields Q-12 allows. | Follow |
| Privilege page | Summary and the history timeline, with discipline events dated but not categorised. | Same. | Follow |
| What is public | Name, home state, license status, compact eligibility, **NPI**, privilege states, privilege dates and status, **discipline dates**. | Default: name, SQL state, privilege number, status, dates. No NPI, no eligibility, no discipline. | Deviate pending Q-12 |

## 7. Product decisions we inherit outright

1. Two-factor authentication for everyone, practitioners included.
2. One checkout for many states; fees itemised per state plus one administrative fee; card only; "all purchases are final".
3. Attestations as versioned legal texts accepted by checkbox, re-accepted if the text changes.
4. A privilege expires when the qualifying license expires, and renewing the license does not extend it.
5. Status is derived, never edited by hand: a privilege is active only if it is not expired, not deactivated, and not under an unlifted disciplinary action.
6. Discipline on the home license affects every privilege; discipline on one privilege affects only that one; a lifted action still bars new privileges for two years.
7. One-way settings (a state goes live once; registration is enabled once) with a confirm dialog.
8. Three notification lists per state and per compact: operations, discipline, reports.
9. States see only their own rows in reports.
10. The public sees only privilege holders, and never personal contact details.
11. Registration and account pages never confirm whether a record or email exists.

## 8. Product decisions we make differently

| Decision | CompactConnect | Ours | Reason |
|---|---|---|---|
| Eligibility | Uploaded flag | SQL reviews in-system | Rule 3 §3.4(b) |
| Issuance | On payment | By the remote state from a queue | Rule 3 §3.4(d) |
| Registration | Match an uploaded license | Self-signup; SQL verifies later | Follows from the two above |
| Practitioner data | State-owned, read-only to the PA | PA-entered, SQL-verified, history kept | Rule 4/5 §5.3 |
| Effect of home-license discipline | Privileges marked encumbered, restored on lift | Privileges deactivated, no reinstatement, two-year bar | ML §4.B, §6.G, §4.A.8 |
| Who can search whom | All staff, all practitioners | State staff scoped to their PAs | Rule 4/5 §5.6(a) |
| Public data | Includes NPI, eligibility, discipline dates | Name, states, privilege number, status, dates | Rule 4/5 §5.5(b); Q-12 |
| Confidential discipline | None | Public flag + confidential banner | Rule 4/5 §5.5(c) |
| SII | Investigation record with a discipline status visible on cards | Flag + contact, never shown to the PA | ML §8.C |
| Expiry reminders | 30 / 7 / 0 days | 60 / 30 / 7 days | Rule 3 §3.5(b) minimum |
| Staff user management | Self-service page | Command line at pilot | Scope (§5.1 of the breakdown) |
| Bulk license upload, military status, home-state change, printable proof | Present | Not built | Not in SOW; military basis survives only as an SQL basis |

## 9. Questions for the Commission where CC's choice is the alternative

1. **Public fields (Q-12).** CC shows NPI, compact eligibility, and dates of disciplinary actions. Our default hides all three. Offer both.
2. **Who is told about discipline (Q-20).** CC tells the practitioner, the acting state, and every state where the practitioner holds a license or privilege. That is our default; the statute could be read as "all participating states".
3. **Lost authenticator.** CC lets a practitioner recover on their own by re-proving identity. Our default is an administrator reset at pilot; CC's flow is the fallback if volume needs it.
4. **Card fee pass-through (Q-02).** CC lets the compact add a per-privilege card fee that the practitioner sees as a line item. Ours is deferred until the Commission says yes.
5. **Payment account in the app.** CC's compact admin enters and rotates the Authorize.net keys on a settings screen. We do it for the Commission at pilot.

## 10. Screen map

One row per screen. "Capture" is our screenshot in `compactconnect-screens/`; "CC reference" is the component or CC staff-guide image. The product ticket attaches the capture to the wireframe.

| Portal | Screen | Capture | CC reference | Posture |
|---|---|---|---|---|
| Public | Landing | `public-landing.png` | `PublicDashboard`, `staff_login.png` | Follow |
| Public | Verify: search | `public-verify-search.png` | `PublicLicensingList` | Adapt |
| Public | Verify: results | `public-verify-results.png` | `LicenseeListLegacy` | Follow |
| Public | Verify: practitioner page | `public-practitioner-detail.png` | `PublicLicensingDetail` | Follow |
| Public | Verify: privilege history | `public-privilege-detail.png` | `PublicPrivilegeDetail`, `privilege_summary.png` | Follow |
| PA | Register | `public-register.png` | `RegisterLicensee` (two-screen confirm) | Adapt |
| PA | Two-factor enrolment, login, reset password | — (Cognito hosted pages) | `reset_password.png` | Adapt |
| PA | Lost-authenticator recovery | `public-account-recovery.png` | `MfaResetStartLicensee` | Gap, §8 |
| PA | Profile form and summary | `pa-account.png`, `pa-privilege-step1-confirm-info.png` | `UserAccount`, `PrivilegePurchaseInformationConfirmation` | Adapt |
| PA | Dashboard with SQL block, license card, privilege cards | `pa-dashboard.png`, `pa-dashboard-expiry-explanation.png` | `LicenseeDashboard` | Follow |
| PA | Application timeline | `pa-privilege-detail.png` (timeline component) | `PrivilegeHistory` | New |
| PA | Privilege detail and history | `pa-privilege-detail.png` | `PrivilegeDetail`, `privilege_summary.png` | Follow |
| PA | Participation wizard (nine steps) and resubmit variant | `pa-privilege-step1-confirm-info.png`, `pa-privilege-step3-attestations.png`, `pa-privilege-step4-payment-summary.png` (for the confirm, attestation, and review steps) | `PrivilegePurchase*` | Mostly New |
| PA | Privilege application: select states | `pa-privilege-step2-select-states.png` | `PrivilegePurchaseSelect` | Follow |
| PA | Privilege application: per-state panel and attestation text | `pa-privilege-step2-state-panel.png`, `pa-privilege-step2-attestation-modal.png` | `SelectedStatePurchaseInformation` | Follow |
| PA | Privilege application: attestations | `pa-privilege-step3-attestations.png` | `PrivilegePurchaseAttestation` | Follow |
| PA | Privilege application: fee summary and acknowledgements | `pa-privilege-step4-payment-summary.png` | `PrivilegePurchaseFinalize` | Follow |
| PA | Privilege application: pay, done | — (Authorize.net lightbox needs live scripts) | `PrivilegePurchaseAcceptUI`, `PrivilegePurchaseSuccessful` | Follow |
| PA | Transactions | — | — | New |
| State | Compact settings and state list | `staff-compact-settings.png` | `CompactSettingsConfig`, `StateSettingsList`, `settings_tab.png` | Follow |
| State | State settings | `staff-state-settings.png` | `StateSettingsConfig` | Adapt |
| State | License entry form and card | `staff-practitioner-detail.png` (license cards) | `LicenseCard` | New form, Follow card |
| State | SQL queue and case view | `staff-search-results.png`, `staff-practitioner-detail.png` (layout only) | `LicenseeList`, `LicensingDetail` | New |
| State | Remote-state queue and case view | as above | as above | New |
| State | Practitioner search | `staff-search.png` | `LicenseeSearch`, `license_search_tab.png` | Adapt |
| State | Search results | `staff-search-results.png` | `LicenseeList`, `license_list_view.png` | Follow |
| State | Practitioner detail, SSN reveal | `staff-practitioner-detail.png` | `LicensingDetail`, `practitioner_details_page.png` | Follow + extend |
| State | Privilege history (staff view) | `staff-privilege-detail-history.png` | `PrivilegeDetail` | Follow |
| State | Card action menu | `staff-privilege-action-menu.png` | `privilege_action_menu.png` | Follow |
| State | Deactivate privilege | `staff-deactivate-privilege-modal.png` | `PrivilegeCard` | Follow |
| State | Report discipline | `staff-encumber-privilege-modal.png` | `LicenseCard` / `PrivilegeCard` encumber dialog | Follow + extend |
| State | Lift | `staff-lift-encumbrance-modal.png` | unencumber dialog | Follow |
| State | SII | `staff-add-investigation-modal.png` | add-investigation dialog | Adapt |
| State | License status update form | — | — | New |
| Commission | Dashboard tiles | — | — | New |
| Commission | Reports page | — | CC weekly/monthly CSVs (columns) | Adapt |
| Deferred | Staff user management | `staff-users.png`, `deferred-invite-staff-user-modal.png` | `user_management_page.png`, `invite_user_form.png` | Deferred |
| Deferred | Payment account | `staff-compact-settings.png` (Authorize.net section) | `authorize_net_*.png` | Deferred |
| Dropped | Bulk upload | `dropped-bulk-license-upload.png` | `license_upload.png` | Dropped |
| Dropped | Military status | `dropped-military-status.png` | `MilitaryStatus` | Dropped |
| Dropped | Home-state change | `pa-account.png` (middle section) | `UpdateHomeJurisdiction` | Dropped |
| Dropped | Printable proof | `dropped-printable-verification.png` | `LicenseeProof` | Dropped |
