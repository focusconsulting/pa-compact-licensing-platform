> **Needs review (2026-10-05, SCRUM-39).** Two entries cite rule text that changed when Rules 3 and 4 were adopted on 2026-04-06. **SQL** cites "Rule 2 §2.1"; draft Rule 2 was not adopted. The PA designates the state of qualifying license under adopted Rule 3.4(a)(2), and Rule 3.1(q) defines it. **CBC** says the check is "run by the SQL". Adopted Rule 3.4(a)(4) has the PA "Submit to a criminal background check within 60 days of the application through the process designated by the state of qualifying license", and Rule 3.4(b)(2) has the state review it. The CBC entry also cites "Rule 4/5 §5.2(g)"; the adopted citation is Rule 4.2(g). Remove this note when the file is updated.

# PA Compact Data System — Acronyms and Terms

Companion to `product/backlog/mvp-ticket-breakdown.md`, `product/context/flows/`, and `compactconnect-crosswalk.md` beside this file. Rule citations use the keys in the second table.

## Compact and domain acronyms

| Acronym | Expansion | What it means here |
|---|---|---|
| **PA** | Physician Assistant (or Physician Associate — the model legislation treats the titles as synonymous, ML §2.P) | The practitioner; role `licensee` in the system |
| **PAC / the Commission** | Physician Assistant Compact Commission | The client; administers the compact and owns the data system |
| **QL** | Qualifying License | An unrestricted PA license issued by a participating state; the license a compact privilege hangs off (ML §2.R) |
| **SQL** | State of Qualifying License | The participating state the PA designates as the one whose license they rely on; verifies eligibility (Rule 2 §2.1, Rule 3 §3.4(b)). Not to be confused with the query language |
| **RS** | Remote State | A participating state where the PA is not licensed and is seeking or holds a compact privilege (ML §2.S); issues the privilege |
| **CP** | Compact Privilege | Authorization from a remote state to practise there under the compact (ML §2.B). Never "practice privilege" or "compact license" in the UI |
| **CBC** | Criminal Background Check | Fingerprint-based check run by the SQL within 60 days of application (Rule 3 §3.4(b)(2)). The system stores only the completion date, never results (Rule 4/5 §5.2(g)) |
| **CHRI** | Criminal History Record Information | The results of a CBC; must never be stored or reported through the data system (ML §8.B.4, R5 §5.2(g)) |
| **SII** | Significant Investigative Information | Investigative information a board has reason to believe is not groundless and would be more than a minor infraction (ML §2.U). Visible only to participating-state and commission users, never to the PA or public (ML §8.C) |
| **AA** | Adverse Action | Any disciplinary action against a license, application, or privilege: denial, censure, revocation, suspension, probation, monitoring, restriction (ML §2.A) |
| **UDS** | Uniform Data Set | The per-PA record every participating state must submit (ML §8.B, R5 §5.3): identity, licensure, adverse actions, SII existence, denials |
| **NPDB** | National Practitioner Data Bank | Federal repository of practitioner discipline; its action-category taxonomy is used as the "basis for action" pick-list on adverse actions |
| **NCCPA** | National Commission on Certification of Physician Assistants | Certifying body; current NCCPA certification is an eligibility requirement (ML §4.A.2) |
| **PANCE** | Physician Assistant National Certifying Examination | The NCCPA exam participating states must use for licensure (ML §3.A.7) |
| **ARC-PA** | Accreditation Review Commission on Education for the Physician Assistant | Accredits PA programs; graduation from an ARC-PA program is an eligibility requirement (ML §4.A.1) |
| **DEA** | Drug Enforcement Administration | A DEA controlled-substance registration action disqualifies a PA (ML §4.A.4); DEA registration in the remote state is the PA's responsibility (ML §4.D) |
| **PL 92-544** | Public Law 92-544 | The federal authority under which state boards obtain FBI criminal history for licensing; cited by the CBC rule |
| **NPI** | National Provider Identifier | 10-digit federal provider ID; part of the uniform data set |
| **SSN** | Social Security Number | The rule's "unique identifier" (Rule 3 §3.3(a)(5)); stored encrypted in a separate table, shown as last-4, full reveal audited |
| **CSG** | Council of State Governments | Runs the National Center for Interstate Compacts; produced the model legislation and webinar in the corpus |
| **RFP / RFI** | Request for Proposals / Request for Information | The Commission's Oct 2025 RFP and Jan 2025 RFI; the RFP's five "priority user stories" anchor MVP scope |
| **SOW** | Statement of Work | Focus's contract document; the scope boundary for the MVP backlog |
| **QASP** | Quality Assurance Surveillance Plan | The RFP/SOW table of deliverable standards: 90% coverage, 0 lint, WCAG 2.1 AA with pa11y, OWASP ASVS, single-command deploy |
| **PoP** | Period of Performance | 16 weeks / 8 sprints under the SOW |
| **MVP** | Minimum Viable Product | "A system that enables the Commission to issue compact privileges" (RFP Q&A #15.1) |
| **UAT** | User Acceptance Testing | Commission/state sign-off testing in Phase 3 |

## Rule citation keys used in the backlog

| Key | Document |
|---|---|
| **ML** | PA Compact Model Legislation (`human-sourced-docs/pa-compact-model-legislation.pdf`), cited by section, e.g. ML §4.B |
| **R2 / R2r** | Draft Rule 2, State of Qualifying License; `r` = the later redline (`pa-compact-rule-2-and-3-drafts.pdf`) |
| **R3 / R3r** | Draft Rule 3, Compact Privilege; `r` = redline approved by the rules committee Feb 9 2026 |
| **R5** | Draft Rule 5, Data System — renumbered to Rule 4 on Nov 10 2025; same text (`pa-draft-rules-2_3_5.pdf`) |
| **Nov10 / Feb9 / Nov3** | Rules committee minutes of Nov 10 2025 and Feb 9 2026; full commission minutes of Nov 3 2025 |

## Engineering and delivery acronyms

| Acronym | Expansion | Where it shows up |
|---|---|---|
| **ADR** | Architecture Decision Record | `engineering/docs/architecture_decision_records/`; decisions D1–D15 each get one |
| **AC** | Acceptance Criteria | The testable "done" list on every ticket |
| **API** | Application Programming Interface | The FastAPI service under `/api/v1/*` |
| **REST** | Representational State Transfer | The API style; resources per persona namespace |
| **OpenAPI / OAS** | OpenAPI Specification | Committed `openapi.json`; the TS client is generated from it |
| **MSW** | Mock Service Worker | Browser-side API mocks generated from the OpenAPI examples so UI tickets run without the API |
| **RBAC** | Role-Based Access Control | Roles + per-state permissions (F-04) |
| **AuthN / AuthZ** | Authentication / Authorization | Cognito + JWT (who you are) vs. the F-04 permission dependency (what you may do) |
| **JWT** | JSON Web Token | The bearer token Cognito issues; validated by `auth.py` |
| **JWKS** | JSON Web Key Set | Cognito's public keys used to verify JWTs |
| **SRP** | Secure Remote Password | The Cognito login protocol the client already uses |
| **MFA / TOTP** | Multi-Factor Authentication / Time-based One-Time Password | Required for every user (decision D4) |
| **PKCE** | Proof Key for Code Exchange | The OAuth flow the Cognito plan originally described; the client uses SRP instead |
| **SES** | Amazon Simple Email Service | Production email backend (F-11) |
| **S3** | Amazon Simple Storage Service | Document storage (F-12); RustFS locally |
| **KMS / CMK** | Key Management Service / Customer-Managed Key | Encryption keys for RDS, S3, Secrets, SSN column |
| **RDS / Aurora** | Relational Database Service | Managed Postgres |
| **ECS / Fargate** | Elastic Container Service / serverless container runtime | Runs the API and Worker |
| **ALB** | Application Load Balancer | Fronts the ECS service |
| **WAF** | Web Application Firewall | Rate limiting and managed rules on CloudFront (F-10) |
| **ADOT / OTel** | AWS Distro for OpenTelemetry / OpenTelemetry | Tracing and metrics sidecar already in the task definition |
| **IaC** | Infrastructure as Code | Terraform under `engineering/infrastructure/iac` |
| **CI / CD** | Continuous Integration / Continuous Delivery | GitHub Actions: lint, test, scan, deploy |
| **OIDC** | OpenID Connect | How GitHub Actions assumes the AWS deploy role without long-lived keys |
| **ECR** | Elastic Container Registry | Where the API image lives |
| **EventBridge** | AWS event bus / scheduler | Cron trigger for Worker jobs (F-13) |
| **GHAS** | GitHub Advanced Security | Paid tier needed for CodeQL/secret scanning on a *private* repo; free on public repos (Q-01) |
| **SAST / DAST** | Static / Dynamic Application Security Testing | CodeQL, Semgrep, Bandit (static); OWASP ZAP (dynamic) |
| **ZAP** | OWASP Zed Attack Proxy | The DAST scanner the QASP names |
| **ASVS** | OWASP Application Security Verification Standard (3.0) | The security standard the QASP names |
| **OWASP** | Open Worldwide Application Security Project | Publisher of ASVS and ZAP |
| **SBOM** | Software Bill of Materials | CycloneDX file generated per build; dependency-licence inventory comes from it |
| **CycloneDX / SPDX** | SBOM formats | Either satisfies RFP Q&A #27 |
| **PCI DSS** | Payment Card Industry Data Security Standard | Why card data never touches our servers |
| **SAQ A / SAQ A-EP** | PCI Self-Assessment Questionnaire A / A-EP | A: fully hosted payment form (Accept Hosted or Accept UI). A-EP: our own form with client-side tokenisation. Decision Q-02b |
| **ACH** | Automated Clearing House | US bank-to-bank transfer; Authorize.net calls it eCheck.Net. Not at pilot unless Q-02c says so |
| **MoR** | Merchant of Record | The entity whose merchant account takes the payment — the Commission, per SOW §7.4 |
| **HMAC** | Hash-based Message Authentication Code | How Authorize.net signs webhooks (SHA-512) |
| **WCAG 2.1 AA** | Web Content Accessibility Guidelines, level AA | The accessibility bar; 0 automated and 0 manual errors |
| **pa11y / axe** | Accessibility scanners | pa11y is the QASP's named tool; axe runs in component tests |
| **USWDS** | U.S. Web Design System | The design system; used via `@trussworks/react-uswds` with token overrides |
| **i18n** | Internationalisation | react-i18next; English only at pilot |
| **e2e** | End-to-end tests | Playwright against the local stack |
| **CSP / HSTS** | Content Security Policy / HTTP Strict Transport Security | Response headers set on CloudFront (F-10) |
| **RTO / RPO** | Recovery Time / Recovery Point Objective | Pilot targets to confirm with the Commission (Q-13) |
| **PO** | Product Owner | The Commission's designated decision-maker for backlog prioritisation |
| **PM** | Project Manager / Product Lead | Focus key personnel |
| **UX** | User Experience (designer/researcher) | Produces wireframes and runs usability rounds |

## Ticket prefixes

| Prefix | Epic |
|---|---|
| **F-** | Foundation and contracts |
| **U-** | Identity and users |
| **S-** | Compact and state configuration |
| **L-** | Qualifying licenses and eligibility (Phase 1) |
| **P-** | Privilege application, payment, issuance (Phase 2) |
| **A-** | Status changes, disciplinary information, renewal |
| **D-** | Practitioner records |
| **C-** | Commission portal |
| **V-** | Public verification |
| **H-** | Pilot readiness |
| **X-** | Product/design deliverables |
| **Q-** | Sprint 0 client questions |
| **D1–D15** | Architecture decisions (§2.1 of the ticket doc) |
