# Architecture (C4)

The system's context and containers, in the [C4 model](https://c4model.com/).
Update these diagrams in the pull request that changes what they show.

## Context

Who uses the PA Compact Data System, and which outside systems it depends on.

```mermaid
---
title: "PA Compact Data System: system context"
---
flowchart TD
  pa@{shape: person, label: "Physician Assistant"}
  state@{shape: person, label: "State<br/>staff"}
  commission@{shape: person, label: "Commission staff"}
  public@{shape: person, label: "Public and employers"}

  cds["PA Compact Data System"]

  cognito["Amazon Cognito"]
  ses["Amazon SES"]
  payments["Payment Provider"]
  nccpa["NCCPA"]
  boards["State licensing systems"]

  pa paToCds@-- "Apply for privileges<br/>Pay fees<br/>Manage profile" --> cds
  state stateToCds@-- "Verify eligibility<br/>Issue or deny privileges<br/>Report adverse actions<br/>Configure state" --> cds
  commission commissionToCds@-- "Read reports and audits<br/>Override privileges<br/>Configure the compact" --> cds
  public publicToCds@-- "Verify PA privileges" --> cds
  boards boardsToCds@-- "Send licensee data" --> cds
  cds -- "Authenticate PAs, State staff, and Commission staff" --> cognito
  cds cdsToSes@-- "Send notification emails" --> ses
  cds cdsToPayments@-- "Collect payments" --> payments
  cds cdsToNccpa@-- "Query PA national certifications" --> nccpa

  classDef person fill:#08427b,stroke:#073b6f,color:#fff
  classDef system fill:#1168bd,stroke:#0b4884,color:#fff
  classDef external fill:#999999,stroke:#8a8a8a,color:#fff
  class pa,state,commission,public person
  class cds system
  class cognito,ses,payments,nccpa,boards external
```

## Containers

What runs inside the system, all in AWS `us-east-1` (SOW §2: Commission data
stays in the United States).

```mermaid
---
title: "PA Compact Data System: containers"
config:
  flowchart:
    wrappingWidth: 200
---
flowchart LR
  user@{shape: person, label: "<b>Any user</b><br/>PA, state staff, Commission staff, or member of the public"}

  subgraph cds["PA Compact Data System"]
    cdn["<b>CDN</b><br/><i>[AWS CloudFront]</i>"]
    client["<b>Client</b><br/><i>[Next.js]</i><br/>Browser application"]
    api["<b>API</b><br/><i>[FastAPI / ECS Fargate]</i><br/>System services"]
    worker["<b>Worker</b><br/><i>[Python / ECS Fargate service]</i><br/>Delivers domain events, sends email"]
    jobs["<b>Scheduled jobs</b><br/><i>[Python / ECS Fargate task]</i><br/>One run per schedule"]
    db@{shape: cyl, label: "<b>Database</b><br/><i>[Aurora PostgreSQL 16]</i><br/>Records, history, domain events, audit log"}
    files@{shape: cyl, label: "<b>Document storage</b><br/><i>[Amazon S3]</i><br/>Uploaded proofs, orders, and verification documents"}
  end

  cognito["<b>Amazon Cognito</b><br/>User pool"]
  ses["<b>Amazon SES</b><br/>Email"]
  payments["<b>Payment Provider</b><br/>Collect payments"]
  nccpa["<b>NCCPA</b><br/>Certification"]
  observability["<b>CloudWatch</b><br/>Logs, metrics, alarms"]
  scheduler["<b>EventBridge Scheduler</b><br/>Starts jobs"]

  user -- "<b>Accesses</b><br/><i>[HTTPS]</i>" --> cdn
  user -- "<b>Authenticates</b><br/><i>[SRP / HTTPS]</i>" --> cognito
  cdn -- "<b>Serves</b><br/><i>[Amazon S3]</i>" --> client
  cdn -- "<b>Forwards /api</b><br/><i>[HTTPS]</i>" --> api
  api -- "<b>Verifies (JWKS)</b><br/><i>[HTTPS]</i>" --> cognito
  api -- "<b>Reads and writes</b><br/><i>[SQL / TLS]</i>" --> db
  api -- "<b>Reads and writes</b><br/><i>[HTTPS]</i>" --> files
  worker -- "<b>Reads and writes</b><br/><i>[SQL / TLS]</i>" --> db
  worker -- "<b>Sends email</b><br/><i>[SMTP / STARTTLS]</i>" --> ses
  worker -- "<b>Logs</b><br/><i>[awslogs]</i>" --> observability
  scheduler -- "<b>Runs</b><br/><i>[ECS RunTask]</i>" --> jobs
  jobs -- "<b>Reads and writes</b><br/><i>[SQL / TLS]</i>" --> db
  jobs -- "<b>Logs</b><br/><i>[awslogs]</i>" --> observability
  api -- "<b>Charges fees</b><br/><i>[HTTPS]</i>" --> payments
  api -- "<b>Queries certification</b><br/><i>[HTTPS]</i>" --> nccpa
  api -- "<b>Logs</b><br/><i>[OTLP / AWS Distro for OpenTelemetry]</i>" --> observability

  classDef person fill:#08427b,stroke:#073b6f,color:#fff
  classDef container fill:#438dd5,stroke:#3c7fc0,color:#fff
  classDef external fill:#999999,stroke:#8a8a8a,color:#fff
  class user person
  class cdn,client,api,worker,jobs,db,files container
  class cognito,ses,payments,nccpa,observability,scheduler external
```

## Locally

Every external service above has a local stand-in that the app reaches
through its production client; only URLs differ (constitution Principle IV).
See [Run the whole system locally](../../README.md#run-the-whole-system-locally)
and [`engineering/api/.env.example`](../api/.env.example).

| In AWS | Locally |
|---|---|
| Aurora PostgreSQL | Postgres in Docker Compose |
| Cognito | cognito-local ([`engineering/mocks/cognito`](../mocks/cognito/README.md)), signed in to with password auth instead of SRP ([ADR-0010](../adrs/0010-local-sign-in-uses-password-auth.md)) |
| SES | maildev |
| EventBridge Scheduler | None: run a job by hand with `just job <name>` |
| S3 | RustFS |
| Payment Provider, NCCPA | Mock servers, built with the tickets that write their clients |
