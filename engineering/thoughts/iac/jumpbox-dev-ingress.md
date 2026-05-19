# Jumpbox Ingress for DEV Debugging

The networking Terraform (`infrastructure/iac/components/app/terraform/networking.tf`)
includes conditional ingress rules on the ECS, RDS, and ElastiCache security groups
that allow all traffic from a designated jumpbox EC2 instance.

These rules are **off by default** and only activated when `jumpbox_sg_id` is supplied
at apply time:

```bash
terraform apply \
  -var-file=environments/dev/us-east-1/app.tfvars \
  -var="jumpbox_sg_id=sg-xxxxxxxxxxxxxxxxx"
```

When active, an SSM port-forward tunnel through the jumpbox gives a local machine
direct TCP access to:

| Resource      | Port |
|---------------|------|
| ECS task      | 8000 |
| RDS PostgreSQL| 5432 |
| ElastiCache   | 6379 |

## Why this is useful

With the tunnel running, a developer can set environment variable overrides pointing
at DEV resources and run the API (or any tooling) locally against the real DEV
database and cache — without deploying a new container image. This is particularly
helpful for:

- Reproducing a bug that only appears against real data
- Running ad-hoc queries or migrations against DEV RDS directly
- Testing Redis behaviour against the live ElastiCache cluster

## How to use

1. Get the jumpbox security group ID:
   ```bash
   aws ec2 describe-instances \
     --instance-ids <jumpbox-id> \
     --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
     --output text
   ```

2. Apply with the variable set (plan first with `gen-tf-plan.py`).

3. Start the SSM tunnel using the `aws-tunnel-to-service` shell function.

4. Create a local env override file (e.g. `api/.env.dev`) pointing at the
   tunnelled ports. This file is gitignored via the root `.env*` rule:
   ```bash
   # api/.env.dev
   DB_HOST=127.0.0.1
   DB_PORT=5433
   DB_NAME=licensing
   DB_USER=licensing
   DB_PASSWORD=<dev password from Secrets Manager>
   REDIS_URL=redis://127.0.0.1:6380
   ENVIRONMENT=DEV
   LOG_LEVEL=DEBUG
   ```

5. Run the API using the override file:
   ```bash
   cd api
   just dev env-file=.env.dev
   ```

## Important

- This variable should **never** be set in staging or production tfvars.
- The `jumpbox_sg_id` variable defaults to `null`, so omitting it from a prod apply
  leaves all three security groups unchanged.
