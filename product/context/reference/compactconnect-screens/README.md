# CompactConnect screen captures

Captured 2026-09-30 from the CompactConnect web app (`github.com/csg-org/CompactConnect` @ 83596ab4) run locally in its mock-API mode, so the data shown is CompactConnect's own demo data (OT compact, practitioners "Layne Cornell" and "Janet Doe"), not real records. Viewport 1440 px wide, full page unless the name says "modal" or "menu" (those are viewport crops). These accompany `../compactconnect-crosswalk.md`; §10 there maps each of our planned screens to one of these files.

Prefixes: `public-` unauthenticated, `pa-` practitioner, `staff-` state or compact staff, `deferred-` a screen we build later, `dropped-` a screen we do not build.

| File | What it shows |
|---|---|
| `public-landing.png` | Landing page: practitioner login, "create an account", staff login per compact, "verify a compact privilege" |
| `public-register.png` | Practitioner registration: license type, home state, name, SSN last 4, DOB, email |
| `public-account-recovery.png` | "Reset your account" for a practitioner locked out of two-factor |
| `public-verify-search.png` | Public verification search: profession, state, first and last name |
| `public-verify-results.png` | Public results: name, home state, privilege states, "Viewing: OT, Doe" filter chip |
| `public-practitioner-detail.png` | Public practitioner page: name, home state, privilege cards |
| `public-privilege-detail.png` | Public privilege page: summary and history timeline |
| `pa-dashboard.png` | Practitioner dashboard: welcome, "+ Obtain Privileges", home-state block, license cards, privilege cards |
| `pa-dashboard-expiry-explanation.png` | The clock-icon tooltip explaining that privileges expire with the license |
| `pa-privilege-detail.png` | Practitioner's own privilege page: summary, history with renewals, "Today" marker, expiration |
| `pa-account.png` | Account page: name (read-only), email change, change home state, change password, military status |
| `pa-privilege-step1-confirm-info.png` | Purchase step 1: confirm personal and license information, two attestation checkboxes |
| `pa-privilege-step2-select-states.png` | Purchase step 2: state checkbox grid; home state and states already held are greyed out |
| `pa-privilege-step2-state-panel.png` | Step 2 with Alabama selected: expiration, state fee, administrative fee, subtotal, jurisprudence and scope checkboxes |
| `pa-privilege-step2-attestation-modal.png` | The scope-of-practice attestation text opened from the state panel, with Back / "I understand" |
| `pa-privilege-step3-attestations.png` | Purchase step 3: investigation radio pair, discipline and true-information checkboxes |
| `pa-privilege-step4-payment-summary.png` | Purchase step 4: itemised fees, total, the two acknowledgements, Payment button |
| `staff-search.png` | Staff search form: providers or privileges, names, home and privilege state, dates, military, investigation, encumbered, NPI |
| `staff-search-results.png` | Staff results list with the "Viewing" chip and "Edit search" |
| `staff-practitioner-detail.png` | Staff practitioner record: investigation banner, personal information with SSN reveal, military audit, license cards, privilege cards |
| `staff-privilege-detail-history.png` | Staff view of a deactivated privilege's history |
| `staff-privilege-action-menu.png` | The kebab menu on an active privilege card: Deactivate, Encumber, Add investigation |
| `staff-deactivate-privilege-modal.png` | Deactivate dialog with required notes |
| `staff-encumber-privilege-modal.png` | Encumber dialog: disciplinary action, NPDB category multi-select, start date |
| `staff-lift-encumbrance-modal.png` | Remove-encumbrance dialog listing the actions on record |
| `staff-add-investigation-modal.png` | Confirm Significant Investigative Information dialog |
| `staff-users.png` | Staff user list: permissions, affiliation, states, account status |
| `staff-compact-settings.png` | Compact settings: fees, three notification lists, registration toggle, Authorize.net credentials, state live list |
| `staff-state-settings.png` | State settings: per-type fees with military rate, jurisprudence, notification lists, live toggle |
| `deferred-invite-staff-user-modal.png` | Invite new user form (we do this by command line at pilot) |
| `dropped-bulk-license-upload.png` | CSV license upload (not built; states enter licenses in a form instead) |
| `dropped-military-status.png` | Military status page (not built) |
| `dropped-printable-verification.png` | Printable verification document with QR code (not built) |
| `styleguide.png` | CompactConnect's living style guide route |

Not captured: Cognito hosted login pages (external), the Authorize.net card lightbox (needs live Authorize.net scripts), and the purchase success page (its route guard sends a fresh session back to the dashboard).
