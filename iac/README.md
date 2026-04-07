# Infrastructure

Terraform configuration for deploying the PA Compact Licensing API to AWS Fargate.

## Architecture

Each environment (DEV, STAGING, PROD) gets an isolated stack:
- **VPC** with public/private subnets across 2 AZs
- **ALB** in public subnets (HTTP on port 80)
- **ECS Fargate** service in private subnets
- **RDS PostgreSQL** in private subnets
- **ElastiCache Redis** in private subnets
- **Secrets Manager** for sensitive configuration

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.10
3. **GitHub Actions IAM Role**: Create an OIDC provider and IAM role (`github-actions-deploy`) with permissions for ECR, ECS, and Secrets Manager. See [AWS docs on OIDC with GitHub](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html).
4. **GitHub Secrets**: Set `AWS_ACCOUNT_ID` in the repository secrets.

## Initial Setup (one-time)

### 1. Bootstrap State Backend & ECR

```bash
cd iac/bootstrap
terraform init
terraform apply
```

### 2. Provision an Environment

```bash
cd iac/environments/dev
terraform init
terraform apply -var="db_password=YOUR_SECURE_PASSWORD"
```

Repeat for `staging` and `prod`.

## Deployments

### DEV (automatic)

Merging code to `main` that changes files in `api/` automatically:
1. Builds a Docker image tagged `sha-<commit-hash>`
2. Pushes to ECR
3. Deploys to the DEV ECS service

### STAGING / PROD (manual)

1. **Create a release tag:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   This triggers the "Build Release Image" workflow, which builds and pushes an image tagged `v1.0.0` to ECR.

2. **Deploy the release:**
   - Go to **Actions** > **Deploy Release to Environment**
   - Click **Run workflow**
   - Enter the image tag (e.g., `v1.0.0`) and select the target environment
   - Click **Run workflow** to start the deployment

### Manual DEV Deploy (re-deploy a specific commit)

You can also manually deploy to DEV by running:
```bash
# Find the image tag from ECR
aws ecr describe-images --repository-name pa-compact-licensing-api \
  --query 'imageDetails[*].imageTags' --output table

# Then use the "Deploy Release to Environment" workflow
```

## Environment Sizing

| Resource | DEV | STAGING | PROD |
|---|---|---|---|
| Fargate CPU | 256 (0.25 vCPU) | 256 | 512 (0.5 vCPU) |
| Fargate Memory | 512 MB | 512 MB | 1024 MB |
| Task Count | 1 | 1 | 2 |
| RDS Instance | db.t4g.micro | db.t4g.micro | db.t4g.small |
| RDS Multi-AZ | No | No | Yes |
| Redis Node | cache.t4g.micro | cache.t4g.micro | cache.t4g.small |
| NAT Gateways | 1 (single) | 1 (single) | 2 (per AZ) |
| VPC CIDR | 10.0.0.0/16 | 10.1.0.0/16 | 10.2.0.0/16 |

## Secrets Management

Sensitive values are stored in AWS Secrets Manager and injected as environment variables at container start. After initial `terraform apply`, update secrets via:

```bash
aws secretsmanager put-secret-value \
  --secret-id pa-compact-licensing-dev/app-config \
  --secret-string '{"DB_PASSWORD":"real-password","REDIS_URL":"redis://endpoint:6379"}'
```
