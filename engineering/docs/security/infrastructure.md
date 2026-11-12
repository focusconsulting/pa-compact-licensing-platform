# Infrastructure security

What protects the running system, and how to operate it. The code is the
`app` component under
[`engineering/infrastructure/iac/`](../../infrastructure/iac/README.md);
the plan that built it is SCRUM-84.

## Encryption at rest

Each environment has one customer-managed KMS key, `alias/<env>-licensing-data`
([`kms.tf`](../../infrastructure/iac/components/app/opentofu/kms.tf)), with
yearly rotation. It encrypts:

| What | Where |
|---|---|
| The Aurora cluster, its automated backups and snapshots, and Performance Insights | `rds.tf` |
| The secrets: database credentials, Cognito configuration, SES SMTP credentials | `secrets.tf`, `ses.tf` |
| The API, Worker, jobs, Postgres, and web firewall log groups | `ecs.tf`, `worker.tf`, `rds.tf`, `waf.tf` |
| The alerts topic | `alerting.tf` |
| The ADOT collector's configuration parameter | `ecs.tf` |
| The job schedules | `scheduler.tf` |

Uploaded documents have a key of their own (`alias/<env>-licensing-documents`,
[`documents.md`](../documents.md)), so access to documents is granted
separately from everything else.

Who may use the key is granted by IAM policies on the roles in the module:
the task execution role decrypts the secrets and the parameter, and the
scheduler role decrypts its schedules. The key's own policy admits only the
account, CloudWatch Logs for this environment's log groups, and CloudWatch
alarms publishing to the alerts topic.

One exception: the CloudFront web firewall's log group is always in
`us-east-1`, and a log group can use only a key from its own region. In an
environment outside `us-east-1` it is encrypted with the service's own key.

Scheduling the key for deletion makes the database and its backups
unreadable when the waiting period ends. Don't, except as the last step of
retiring an environment.

## The database

- **Backups.** Automated backups are kept for `backup_retention_period` days
  (7 to 35; staging keeps 7, prod 35).
- **Logs.** Postgres logs go to CloudWatch for 365 days: connections,
  disconnections, lock waits, DDL, and any statement slower than one second.
  Statements are logged without their bound values
  (`log_parameter_max_length = 0`), because those values may be personal
  information. Don't raise it.
- **Monitoring.** Performance Insights and one-minute enhanced monitoring
  are on.

## `deletion_protection`

One variable guards what would block a teardown or lose data in one. It
defaults to `true`.

| With it on | With it off |
|---|---|
| The Aurora cluster cannot be deleted | It can |
| Deleting the cluster first takes a final snapshot, `<cluster>-final` | No final snapshot |
| The load balancer cannot be deleted | It can |

Staging turns it off, because staging is spun up and torn down by design and
holds nothing that must survive. Any environment that holds real data leaves
it on.

### Retiring an environment that has it on

1. Open a pull request that sets `deletion_protection = false` in the
   environment's `app.tfvars`, and have it reviewed: this is the step that
   makes the data deletable.
2. `just apply app <env>`.
3. Take a manual snapshot if the data must be kept; with protection off,
   destroying the cluster takes none.
4. `tofu destroy` the `app` component, then `ecr`.
