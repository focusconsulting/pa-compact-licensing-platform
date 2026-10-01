---
artifact: flow
flow-id: FLOW-03
title: Payment and remote-state issuance (Phase 2)
status: draft
authored-by: CTO (Kalish)
last-revised: 2026-09-30
sources:
  - product/context/research-corpus/sources/pa-compact-model-legislation.md
  - product/context/research-corpus/sources/pa-compact-rule-2-and-3-drafts.md
  - product/context/research-corpus/sources/pa-draft-rules-2_3_5.md
  - product/context/research-corpus/sources/pa-compact-rfp-questions-responses.md
rules-cited: [ML §4.A.8, ML §4.A.11, R3r §3.4(c), R3r §3.4(d), R3r §3.5(a), R3r §3.6(b), R3r §3.7(a), R5 §5.3(d)]
tickets: [P-01, P-02, P-03, S-01, C-02]
decisions: [D2, D6, D9, D15]
open-questions: [Q-02, Q-02b, Q-02c, Q-05, Q-07]
see-also: [FLOW-01, FLOW-04, FLOW-06, compactconnect-crosswalk §3.6, §4.5]
atoms: [ATOM-GOV-ML-07, ATOM-GOV-R23-03, ATOM-GOV-R23-07, ATOM-GOV-R23-08, ATOM-GOV-R23-13, ATOM-GOV-R5-03, ATOM-GOV-RFP-05, ATOM-GOV-RFPQA-03]
signals: [SIGNAL-the-system-does-the-heavy-lifting-for-states, SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance]
---

> **Needs review (2026-10-01, SCRUM-39).** This file cites one atom that quoted draft rule text. That text changed when Rules 3 and 4 were adopted on 2026-04-06. `ATOM-GOV-R23-13` is replaced by `ATOM-GOV-R3-04`. The draft and adopted text are side by side in `product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`. Remove this note when the file is updated.

# FLOW-03 — Payment and remote-state issuance

Phase 2 of FLOW-01 in detail. The PA applies to one or more remote states, pays state fee(s) plus the Commission fee, and each remote state issues or denies. The 72-hour issuance target is operational (RFP Q&A #46.1), not a system SLA; it is measured from the paid request reaching the remote state.

The PA-side steps are CompactConnect's purchase wizard step for step (crosswalk §3.6; captures `pa-privilege-step2-*.png` through `pa-privilege-step4-payment-summary.png`). Only the ending changes: CompactConnect says "purchased" and the privilege exists the moment payment clears; we say "sent to {states} for issuance" and the remote state issues from a queue (R3r §3.4(d)). The state-side queue and case view have no CompactConnect equivalent (crosswalk §4.5).

```mermaid
sequenceDiagram
    autonumber
    participant PA
    participant Web
    participant API
    participant DB
    participant Pay as Authorize.net
    participant Worker
    participant Email
    participant RS as Remote State staff

    PA->>Web: choose states [KS, OK] from the live-state grid (SQL and states with an active privilege greyed out)
    PA->>Web: per-state panel: fee, expiration (= QL expiry), each proof the state configured in S-01 as a checkbox-with-text or an upload (D9), practice-requirements link
    PA->>Web: privilege attestations, then acknowledge "if issued, expires on {QL expiry}" and "fees are non-refundable"
    Web->>API: POST /me/privilege-requests {states, attestations, proofs}
    API->>API: guard: participation=eligible, no 2-year bar, states live, not SQL, no active privilege there
    API->>DB: privilege_request(KS, pending_payment), privilege_request(OK, pending_payment)
    API->>API: fees = Σ state privilege fee + commission fee × N (+ card fee if Q-02 enables it)
    API-->>Web: order summary (server-computed): one line per state, "Administrative fee (× N)", total

    Web->>API: POST /me/payments/checkout {request_ids}
    API->>DB: transaction(status=initiated, idempotency_key)
    API->>Pay: getHostedPaymentPageRequest(amount, line items tagged by state, refId=transaction_id)
    Pay-->>API: token
    API-->>Web: token
    Web->>Pay: Accept UI lightbox — card and billing address entered on Authorize.net, never touch us

    alt Approved
        Pay->>API: webhook net.authorize.payment.authcapture.created (HMAC verified)
        API->>DB: transaction(status=paid, provider_ref), requests→submitted, event privilege.requested ×2
        Worker->>Email: PA receipt (itemised), KS ops, OK ops
    else Declined / abandoned
        Pay->>API: webhook declined (or nothing)
        API->>DB: transaction(status=declined|abandoned) — requests stay pending_payment
        note over API: inline error, PA can retry — drafts expire with the 60-day rule (L-06)
    end

    RS->>Web: queue for KS: request age vs 72h target (operational, not SLA)
    RS->>Web: case view: SQL verdict + date, license, attestations, uploaded proofs, payment status, PA contact details
    note over RS: no in-app request-info at pilot (D15) — a state with a question emails the PA from the contact details
    alt Issue
        RS->>API: POST /states/ks/privilege-requests/{id}/issue
        API->>API: guard: participation still eligible, transaction paid
        API->>DB: privilege(number=PA-KS-000123, issued_at, expiration=QL expiry snapshot on request), request→issued, event privilege.issued
        note over API,DB: the privilege row is KS's R5 §5.3(d) "verify and submit" (issue date, status, expiration, number)
        Worker->>Email: PA "issued", SQL FYI, Commission FYI
    else Deny
        RS->>API: POST .../deny {reason}
        API->>DB: request→denied, event privilege.denied
        Worker->>Email: PA "denied by KS" with reason
        note over API,Worker: fees are non-refundable [R3r §3.4(c)(4)] — no refund flow in MVP
    end

    PA->>Web: GET /me/transactions — what was paid, when, for which states (new — CompactConnect has no practitioner transaction list)
```

## Per-state proofs (S-01, Q-07)

CompactConnect's per-state panel has one configurable proof: "jurisprudence exam required?" with a link, accepted as a checkbox that opens the full text. Ours generalises it to the four things R3r §3.4(c)(3)–(6) let a remote state require: jurisprudence, supervision/collaborative agreement, prescriptive authority, other compliance. Each is configured per state as `none | attestation | proof_upload`; an attestation renders as CompactConnect's checkbox-with-modal (`pa-privilege-step2-attestation-modal.png`), an upload as the F-12 file field. "More info" is the state's practice-requirements URL. Which proofs each pilot state requires is Q-07.

## Payment integration shape (Q-02b)

Authorize.net is not hosted-only. The Accept suite offers three shapes; the trade is PCI scope against control of the payment form's accessibility:

| Shape | Where the card form lives | PCI scope | WCAG control |
|---|---|---|---|
| Accept Hosted | Authorize.net page (redirect or iframe) | SAQ A | none |
| Accept.js + built-in form (Accept UI lightbox) | Authorize.net lightbox on our page | SAQ A | none |
| Accept.js + our own form | our USWDS form; only an opaque nonce reaches the API | SAQ A-EP | full |

**MVP: Accept UI lightbox** (D6, CompactConnect parity), accessibility limitation documented as a known exception in H-01. The `PaymentProvider` protocol allows a later move to our own form (deferred, §5.1: pulled back if H-01 cannot document the lightbox as an acceptable exception).

## Deferred (§5.1): ACH and settlement

Card only at pilot. eCheck.Net is reachable through the same Accept.js path (`bankData`), but there is no settlement or returned-item webhook: an eCheck sits in `capturedPendingSettlement` for several business days, then `settledSuccessfully` or `returnedItem`, discoverable only by polling `getTransactionDetails`. That is incompatible with the 72-hour target unless remote states issue at risk. If the Commission requires bank payment (Q-02c), the request gains a `submitted_payment_pending` status, issuance is gated on settlement, and a `reconcile_transactions` job polls settlement state and emits `payment.settled` / `payment.returned`. The settlement job also returns on its own if the Commission asks for settlement status in C-02.

## Local development

`PAYMENT_PROVIDER=fake` renders a stub card page that approves or declines by the amount's cents (`.00` approve, `.99` decline) and posts the same webhook payload shape. (`.50` pending-settlement arrives with ACH.)

## Evidence

Atoms are in `product/context/evidence/atoms/`; signals and tensions beside them. Rule section references above resolve to these IDs.

- `ATOM-GOV-R23-07` — remote-state application; non-refundable state fee plus Commission administrative fee
- `ATOM-GOV-R23-08` — issuance on receipt of fees, information, and SQL verification; privilege data goes to the data system
- `ATOM-GOV-R23-03` — the Commission collects and remits fees (why line items are tagged by state)
- `ATOM-GOV-ML-07` — the 2-year bar guard on the request
- `ATOM-GOV-R23-13` — 60-day abandonment of an unpaid request
- `ATOM-GOV-R5-03` — what the remote state "verifies and submits" on issuance (issue date, status, expiration, privilege number); the privilege row is that submission
- `ATOM-GOV-RFP-05` — the 72-hour story (operational target, not an SLA)
- `ATOM-GOV-RFPQA-03` — the Commission selects the payment processor
- `SIGNAL-the-system-does-the-heavy-lifting-for-states`
- `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance` — the remote state's lane of the record
