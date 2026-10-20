# Architecture (C4)

The system's context and containers, in the [C4 model](https://c4model.com/).
Elements marked _planned_ are designed but not built yet; each names the
ticket that builds it. Update these diagrams in the pull request that changes
what they show.

## Context

Who uses the PA Compact Data System, and which outside systems it depends on.

```mermaid
C4Context
  title PA Compact Data System: system context

  Person(pa, "Physician assistant", "Applies for compact privileges, pays fees, and manages their profile")
  Person(state, "State staff and administrators", "Verify eligibility as the qualifying-license state, issue or deny privileges as a remote state, report adverse actions, configure their state")
  Person(commission, "Commission staff", "Configure the compact, override privileges, read reports and the audit log")
  Person(public, "Public and employers", "Look up whether a PA holds a privilege to practise")

  System(cds, "PA Compact Data System", "Privilege applications, eligibility, issuance, adverse actions, and the record of every change")

  System_Ext(cognito, "Amazon Cognito", "Sign-in for PAs, state staff, and Commission staff")
  System_Ext(ses, "Amazon SES", "Sends notification email (planned: 4gi.5)")
  System_Ext(authnet, "Authorize.net", "Takes card payments for privilege fees (planned)")
  System_Ext(nccpa, "NCCPA", "Reports each PA's national certification (planned, awaiting the NCCPA contract)")
  System_Ext(boards, "State licensing systems", "Send licensee data by file upload or API (planned: L-02)")

  Rel(pa, cds, "Applies and pays", "HTTPS")
  Rel(state, cds, "Verifies, decides, reports", "HTTPS")
  Rel(commission, cds, "Configures and oversees", "HTTPS")
  Rel(public, cds, "Looks up privileges", "HTTPS")
  Rel(cds, cognito, "Signs users in, verifies their tokens")
  Rel(cds, ses, "Sends email", "SMTP")
  Rel(cds, authnet, "Charges fees, receives payment webhooks", "HTTPS")
  Rel(cds, nccpa, "Looks up certification", "HTTPS")
  Rel(boards, cds, "Sends licensee data", "HTTPS")
```

## Containers

What runs inside the system, all in AWS `us-east-1` (SOW §2: Commission data
stays in the United States).

```mermaid
C4Container
  title PA Compact Data System: containers

  Person(user, "Any user", "PA, state staff, Commission staff, or the public")

  System_Boundary(cds, "PA Compact Data System") {
    Container(cdn, "CloudFront", "AWS CloudFront", "Serves the client and routes /api to the API")
    Container(client, "Client", "Next.js static export, React, USWDS", "Every screen; runs in the browser and signs in with Cognito (SRP)")
    Container(api, "API", "FastAPI on ECS Fargate, behind an internal ALB", "Validates and records every change with its history and domain event; enforces permissions")
    Container(worker, "Worker", "Same image as the API, its own ECS service", "Handles domain events and runs scheduled jobs: notifications, cascades, clocks (planned: 4gi.5)")
    ContainerDb(db, "Database", "Aurora PostgreSQL 16", "Records, history, domain events, audit log")
    ContainerDb(files, "Document storage", "Amazon S3", "Uploaded proofs, orders, and verification documents (planned: 4gi.6)")
  }

  System_Ext(cognito, "Amazon Cognito", "User pool")
  System_Ext(ses, "Amazon SES", "Email")
  System_Ext(authnet, "Authorize.net", "Payments")
  System_Ext(nccpa, "NCCPA", "Certification")
  System_Ext(observability, "CloudWatch and X-Ray", "Logs, metrics, traces, alarms to Slack")

  Rel(user, cdn, "Uses", "HTTPS")
  Rel(cdn, client, "Serves", "S3 origin")
  Rel(cdn, api, "Forwards /api", "HTTPS")
  Rel(user, cognito, "Signs in", "SRP over HTTPS")
  Rel(api, cognito, "Fetches signing keys (JWKS)", "HTTPS")
  Rel(api, db, "Reads and writes", "SQL over TLS")
  Rel(api, files, "Issues short-lived upload and download links", "HTTPS")
  Rel(worker, db, "Claims and handles events", "SQL over TLS")
  Rel(worker, ses, "Sends email", "SMTP")
  Rel(api, authnet, "Charges fees", "HTTPS")
  Rel(api, nccpa, "Looks up certification", "HTTPS")
  Rel(api, observability, "Logs and traces", "OTLP via the ADOT sidecar")
```

## Locally

Every external service above has a local stand-in that the app reaches
through its production client; only URLs differ (constitution Principle IV).
See [Run the whole system locally](../../README.md#run-the-whole-system-locally)
and [`engineering/api/.env.example`](../api/.env.example).

| In AWS | Locally |
|---|---|
| Aurora PostgreSQL | Postgres in Docker Compose |
| Cognito | The Cognito mock ([`engineering/mocks/cognito`](../mocks/cognito/README.md)) |
| SES | maildev |
| S3 | RustFS |
| Authorize.net, NCCPA | Mock servers, built with the tickets that write their clients |
