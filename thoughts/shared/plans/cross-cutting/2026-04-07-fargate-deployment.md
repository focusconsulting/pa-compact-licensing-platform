# Fargate Deployment Pipeline — Implementation Plan

## Overview

Deploy the PA Compact Licensing API (`api/`) to AWS Fargate across three environments (DEV, STAGING, PROD) with full Terraform IaC and GitHub Actions CI/CD. DEV auto-deploys on merge to `main`; STAGING and PROD deploy via manual `workflow_dispatch` from semver git tags.

## Related

- GitHub Issue: N/A
- Beads Task: TBD (will be created as part of this plan)
- ADRs: N/A
- **Area**: cross-cutting (api + iac)

## Current State Analysis

- FastAPI app with production-ready multi-stage Dockerfile (`api/Dockerfile:34-49`) — Gunicorn + UvicornWorker on port 8000
- `pydantic-settings` config (`api/licensing_api/config.py:6-16`) already supports `environment: LOCAL_DEV | DEV | STAGING | PROD` and all settings are env-var overridable
- Health endpoints: `/health/live` (liveness) and `/health/ready` (readiness — checks Postgres + Redis) at `api/licensing_api/routes/health.py`
- CI workflow (`.github/workflows/api.yml`) runs lint + test on push/PR to main
- `iac/` directory is empty (`.gitkeep` only)
- No deployment workflows, no AWS resources defined in code

### Key Discoveries:
- The app config already maps cleanly to ECS environment variables + Secrets Manager secrets
- Health check endpoints are ready for ALB target group health checks
- The Dockerfile prod stage runs as non-root (UID 999), which is Fargate-compatible
- No HTTPS/ACM needed — ALB DNS name is sufficient for now

## Desired End State

After implementation:
1. `terraform apply` in any environment directory provisions a complete, isolated stack (VPC, RDS, ElastiCache, ECS/Fargate, ALB, Secrets Manager)
2. Merging to `main` automatically builds a Docker image tagged `sha-<7-char-hash>`, pushes to ECR, and deploys to DEV
3. Pushing a semver git tag (`v*.*.*`) builds and pushes a Docker image tagged with that version
4. Clicking "Run workflow" on the release action deploys a chosen image tag to STAGING or PROD
5. Sensitive config (DB password, Redis URL) is injected from Secrets Manager at container start

### Verification:
- `terraform plan` shows no drift after fresh apply
- DEV deployment completes end-to-end on a merge to main
- ALB DNS returns `{"status": "ok"}` from `/health/live`
- `/health/ready` returns `{"db": true, "cache": true}`

## What We're NOT Doing

- HTTPS/ACM certificates or Route53 DNS
- GitHub Environments with protection rules (using `workflow_dispatch` instead)
- Blue/green or canary deployments (using ECS rolling update)
- Auto-scaling (fixed `desired_count`, can be added later)
- VPC peering or Transit Gateway
- CI/CD for Terraform itself (manual `terraform apply` for now)
- Bastion hosts or VPN access
- WAF or CloudFront
- Monitoring/alerting (CloudWatch logs only)

---

## Phase 1: Bootstrap — Terraform State Backend & ECR

### Overview
Create the S3 bucket for Terraform state (with native S3 locking) and a shared ECR repository. These are one-time resources managed with local state.

### Changes Required:

#### 1. Bootstrap Terraform Config
**File**: `iac/bootstrap/main.tf`

```hcl
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  # Intentionally uses local state — this IS the state backend
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "project_name" {
  default = "pa-compact-licensing"
}

# --- S3 State Bucket ---
resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.project_name}-tfstate"
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    noncurrent_version_expiration { noncurrent_days = 90 }
  }
}

# --- ECR Repository (shared across environments) ---
resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}-api"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 30 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = { type = "expire" }
    }]
  })
}

# --- Outputs ---
output "tfstate_bucket" {
  value = aws_s3_bucket.tfstate.id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_repository_arn" {
  value = aws_ecr_repository.api.arn
}
```

### Success Criteria:

#### Automated Verification:
- [ ] `cd iac/bootstrap && terraform init && terraform validate`
- [ ] `cd iac/bootstrap && terraform fmt -check`
- [ ] `cd iac/bootstrap && terraform plan` (review output)

#### Manual Verification:
- [ ] Run `terraform apply` — creates S3 bucket and ECR repo
- [ ] Verify S3 bucket exists: `aws s3 ls | grep pa-compact-licensing-tfstate`
- [ ] Verify ECR repo exists: `aws ecr describe-repositories --repository-names pa-compact-licensing-api`

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual `terraform apply` and confirmation before proceeding.

---

## Phase 2: VPC Module

### Overview
Reusable VPC module with public subnets (ALB), private subnets (Fargate tasks, RDS, ElastiCache), IGW, and NAT gateway. Single NAT for DEV/STAGING, per-AZ NAT for PROD.

### Changes Required:

#### 1. VPC Module
**File**: `iac/modules/vpc/main.tf`

```hcl
# Creates: VPC, public + private subnets across 2 AZs,
# IGW, NAT gateway(s), route tables, S3 gateway endpoint

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs             = slice(data.aws_availability_zones.available.names, 0, var.az_count)
  nat_count       = var.single_nat ? 1 : var.az_count
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${var.name}-vpc" }
}

# --- Public Subnets (ALB) ---
resource "aws_subnet" "public" {
  count                   = var.az_count
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${var.name}-public-${local.azs[count.index]}" }
}

# --- Private Subnets (Fargate, RDS, ElastiCache) ---
resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 100)
  availability_zone = local.azs[count.index]

  tags = { Name = "${var.name}-private-${local.azs[count.index]}" }
}

# --- Internet Gateway ---
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.name}-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.name}-public-rt" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count          = var.az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# --- NAT Gateway(s) ---
resource "aws_eip" "nat" {
  count  = local.nat_count
  domain = "vpc"
  tags   = { Name = "${var.name}-nat-eip-${count.index}" }
}

resource "aws_nat_gateway" "main" {
  count         = local.nat_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${var.name}-nat-${count.index}" }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  count  = var.az_count
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.name}-private-rt-${count.index}" }
}

resource "aws_route" "private_nat" {
  count                  = var.az_count
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[var.single_nat ? 0 : count.index].id
}

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# --- S3 Gateway Endpoint (free, reduces NAT costs for ECR pulls) ---
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = { Name = "${var.name}-s3-endpoint" }
}
```

**File**: `iac/modules/vpc/variables.tf`

```hcl
variable "name" {
  description = "Name prefix for all VPC resources"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use"
  type        = number
  default     = 2
}

variable "single_nat" {
  description = "Use a single NAT gateway (cost savings for non-prod)"
  type        = bool
  default     = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}
```

**File**: `iac/modules/vpc/outputs.tf`

```hcl
output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "vpc_cidr_block" {
  value = aws_vpc.main.cidr_block
}
```

### Success Criteria:

#### Automated Verification:
- [ ] `cd iac/modules/vpc && terraform fmt -check`
- [ ] Module validates when referenced from an environment config (tested in Phase 5)

#### Manual Verification:
- [ ] VPC and subnets appear in AWS console after apply

---

## Phase 3: Data Layer Modules (RDS + ElastiCache + Secrets)

### Overview
Terraform modules for RDS PostgreSQL, ElastiCache Redis, and Secrets Manager. Each module is reusable across environments with different sizing via variables.

### Changes Required:

#### 1. RDS Module
**File**: `iac/modules/rds/main.tf`

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.name}-db-subnet"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.name}-db-subnet" }
}

resource "aws_security_group" "rds" {
  name   = "${var.name}-rds"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-rds" }
}

resource "aws_db_instance" "main" {
  identifier     = "${var.name}-postgres"
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_user
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = var.multi_az
  skip_final_snapshot = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.name}-final-snapshot"

  backup_retention_period = var.backup_retention_period

  tags = { Name = "${var.name}-postgres" }
}
```

**File**: `iac/modules/rds/variables.tf`

```hcl
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "allowed_security_group_ids" {
  type        = list(string)
  description = "Security groups allowed to connect (e.g. ECS tasks)"
}

variable "engine_version" {
  type    = string
  default = "16"
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "max_allocated_storage" {
  type    = number
  default = 50
}

variable "db_name" {
  type    = string
  default = "licensing"
}

variable "db_user" {
  type    = string
  default = "licensing"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "multi_az" {
  type    = bool
  default = false
}

variable "skip_final_snapshot" {
  type    = bool
  default = true
}

variable "backup_retention_period" {
  type    = number
  default = 7
}
```

**File**: `iac/modules/rds/outputs.tf`

```hcl
output "endpoint" {
  value = aws_db_instance.main.endpoint
}

output "address" {
  value = aws_db_instance.main.address
}

output "port" {
  value = aws_db_instance.main.port
}

output "security_group_id" {
  value = aws_security_group.rds.id
}
```

#### 2. ElastiCache Module
**File**: `iac/modules/elasticache/main.tf`

```hcl
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.name}-redis-subnet"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "redis" {
  name   = "${var.name}-redis"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-redis" }
}

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.name}-redis"
  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  tags = { Name = "${var.name}-redis" }
}
```

**File**: `iac/modules/elasticache/variables.tf`

```hcl
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "allowed_security_group_ids" {
  type        = list(string)
  description = "Security groups allowed to connect (e.g. ECS tasks)"
}

variable "engine_version" {
  type    = string
  default = "7.1"
}

variable "node_type" {
  type    = string
  default = "cache.t4g.micro"
}
```

**File**: `iac/modules/elasticache/outputs.tf`

```hcl
output "endpoint" {
  value = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "port" {
  value = aws_elasticache_cluster.main.cache_nodes[0].port
}

output "security_group_id" {
  value = aws_security_group.redis.id
}
```

#### 3. Secrets Module
**File**: `iac/modules/secrets/main.tf`

```hcl
# Creates a Secrets Manager secret with individual key-value pairs
# that map to the app's pydantic-settings env vars.
# The actual secret values are set manually in the AWS console or via CLI
# after initial creation.

resource "aws_secretsmanager_secret" "app" {
  name = "${var.name}/app-config"
  tags = { Name = "${var.name}-app-config" }
}

# Seed with structure — actual values should be updated manually or via CI
resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DB_PASSWORD = var.db_password
    REDIS_URL   = var.redis_url
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
```

**File**: `iac/modules/secrets/variables.tf`

```hcl
variable "name" { type = string }

variable "db_password" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type      = string
  sensitive = true
}
```

**File**: `iac/modules/secrets/outputs.tf`

```hcl
output "secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}
```

### Success Criteria:

#### Automated Verification:
- [ ] `terraform fmt -check -recursive iac/modules/`
- [ ] Modules validate when referenced from environment config (tested in Phase 5)

#### Manual Verification:
- [ ] Resources created correctly on `terraform apply` (tested in Phase 5)

---

## Phase 4: ECS/Fargate Module (Compute Layer)

### Overview
Reusable module that creates: ECS cluster, task definition, Fargate service, ALB (listener on port 80 only — no HTTPS), target group, IAM roles (execution + task), CloudWatch log group, and security groups.

### Changes Required:

#### 1. ECS Module
**File**: `iac/modules/ecs/main.tf`

```hcl
# --- CloudWatch Logs ---
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.name}"
  retention_in_days = var.log_retention_days

  tags = { Name = "${var.name}-logs" }
}

# --- IAM: Execution Role (ECR pull, secrets fetch, log writing) ---
resource "aws_iam_role" "execution" {
  name = "${var.name}-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "secrets-access"
  role = aws_iam_role.execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.secret_arn]
    }]
  })
}

# --- IAM: Task Role (app-level AWS access) ---
resource "aws_iam_role" "task" {
  name = "${var.name}-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# --- Security Groups ---
resource "aws_security_group" "alb" {
  name   = "${var.name}-alb"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-alb" }
}

resource "aws_security_group" "tasks" {
  name   = "${var.name}-tasks"
  vpc_id = var.vpc_id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name}-tasks" }
}

# --- ALB ---
resource "aws_lb" "main" {
  name               = var.name
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]

  tags = { Name = "${var.name}-alb" }
}

resource "aws_lb_target_group" "app" {
  name        = var.name
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/health/ready"
    protocol            = "HTTP"
    port                = "traffic-port"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
  }

  deregistration_delay = 30

  tags = { Name = "${var.name}-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# --- ECS Cluster ---
resource "aws_ecs_cluster" "main" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${var.name}-cluster" }
}

# --- ECS Task Definition ---
resource "aws_ecs_task_definition" "app" {
  family                   = var.name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = var.container_name
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    essential = true

    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "LOG_LEVEL",   value = var.log_level },
      { name = "DB_HOST",     value = var.db_host },
      { name = "DB_PORT",     value = tostring(var.db_port) },
      { name = "DB_NAME",     value = var.db_name },
      { name = "DB_USER",     value = var.db_user },
    ]

    secrets = [
      { name = "DB_PASSWORD", valueFrom = "${var.secret_arn}:DB_PASSWORD::" },
      { name = "REDIS_URL",   valueFrom = "${var.secret_arn}:REDIS_URL::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    linuxParameters = {
      initProcessEnabled = true
    }
  }])
}

# --- ECS Service ---
resource "aws_ecs_service" "app" {
  name            = var.name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = var.container_name
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  health_check_grace_period_seconds = 90

  enable_execute_command = true

  # CI/CD manages the task definition and desired_count
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.http]
}
```

**File**: `iac/modules/ecs/variables.tf`

```hcl
variable "name" { type = string }
variable "aws_region" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }

variable "ecr_repository_url" { type = string }
variable "image_tag" {
  type    = string
  default = "latest"
}

variable "container_name" {
  type    = string
  default = "api"
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "task_cpu" {
  type    = string
  default = "256"
}

variable "task_memory" {
  type    = string
  default = "512"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "log_level" {
  type    = string
  default = "INFO"
}

variable "log_retention_days" {
  type    = number
  default = 30
}

# Database connection (non-secret parts)
variable "db_host" { type = string }
variable "db_port" {
  type    = number
  default = 5432
}
variable "db_name" {
  type    = string
  default = "licensing"
}
variable "db_user" {
  type    = string
  default = "licensing"
}

# Secrets Manager ARN for sensitive values
variable "secret_arn" { type = string }
```

**File**: `iac/modules/ecs/outputs.tf`

```hcl
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "service_name" {
  value = aws_ecs_service.app.name
}

output "task_definition_family" {
  value = aws_ecs_task_definition.app.family
}

output "task_security_group_id" {
  value = aws_security_group.tasks.id
}
```

### Success Criteria:

#### Automated Verification:
- [ ] `terraform fmt -check -recursive iac/modules/`
- [ ] Module validates when referenced from environment config (tested in Phase 5)

#### Manual Verification:
- [ ] ALB DNS returns responses after deploy (tested in Phase 5)

---

## Phase 5: DEV Environment

### Overview
Wire up all modules into a complete DEV environment with appropriate sizing (small instances, single NAT, single Fargate task).

### Changes Required:

#### 1. Environment Config
**File**: `iac/environments/dev/main.tf`

```hcl
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }

  backend "s3" {
    bucket       = "pa-compact-licensing-tfstate"
    key          = "environments/dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "pa-compact-licensing"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# --- Data: ECR repo from bootstrap ---
data "aws_ecr_repository" "api" {
  name = "pa-compact-licensing-api"
}

# --- VPC ---
module "vpc" {
  source     = "../../modules/vpc"
  name       = "${var.project_name}-${var.environment}"
  vpc_cidr   = var.vpc_cidr
  az_count   = 2
  single_nat = true
  aws_region = var.aws_region
}

# --- Secrets (must be created before ECS to get ARN) ---
module "secrets" {
  source      = "../../modules/secrets"
  name        = "${var.project_name}-${var.environment}"
  db_password = var.db_password
  redis_url   = "redis://${module.elasticache.endpoint}:${module.elasticache.port}"
}

# --- RDS ---
module "rds" {
  source                     = "../../modules/rds"
  name                       = "${var.project_name}-${var.environment}"
  vpc_id                     = module.vpc.vpc_id
  subnet_ids                 = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.ecs.task_security_group_id]
  instance_class             = var.rds_instance_class
  db_name                    = "licensing"
  db_user                    = "licensing"
  db_password                = var.db_password
  multi_az                   = false
  skip_final_snapshot        = true
}

# --- ElastiCache ---
module "elasticache" {
  source                     = "../../modules/elasticache"
  name                       = "${var.project_name}-${var.environment}"
  vpc_id                     = module.vpc.vpc_id
  subnet_ids                 = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.ecs.task_security_group_id]
  node_type                  = var.elasticache_node_type
}

# --- ECS / Fargate ---
module "ecs" {
  source              = "../../modules/ecs"
  name                = "${var.project_name}-${var.environment}"
  aws_region          = var.aws_region
  environment         = "DEV"
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  private_subnet_ids  = module.vpc.private_subnet_ids
  ecr_repository_url  = data.aws_ecr_repository.api.repository_url
  image_tag           = var.image_tag
  task_cpu            = var.task_cpu
  task_memory         = var.task_memory
  desired_count       = var.desired_count
  db_host             = module.rds.address
  db_port             = module.rds.port
  secret_arn          = module.secrets.secret_arn
}
```

**File**: `iac/environments/dev/variables.tf`

```hcl
variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "pa-compact-licensing"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "task_cpu" {
  type    = string
  default = "256"
}

variable "task_memory" {
  type    = string
  default = "512"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "elasticache_node_type" {
  type    = string
  default = "cache.t4g.micro"
}
```

**File**: `iac/environments/dev/outputs.tf`

```hcl
output "alb_dns_name" {
  value = module.ecs.alb_dns_name
}

output "ecs_cluster_name" {
  value = module.ecs.cluster_name
}

output "ecs_service_name" {
  value = module.ecs.service_name
}

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "redis_endpoint" {
  value = module.elasticache.endpoint
}
```

**File**: `iac/environments/dev/terraform.tfvars`

```hcl
# DEV environment sizing
aws_region            = "us-east-1"
environment           = "dev"
vpc_cidr              = "10.0.0.0/16"
task_cpu              = "256"
task_memory           = "512"
desired_count         = 1
rds_instance_class    = "db.t4g.micro"
elasticache_node_type = "cache.t4g.micro"
```

**Note**: `db_password` is intentionally omitted from tfvars. Pass it at apply time:
```bash
terraform apply -var="db_password=YOUR_SECRET"
```

### Circular Dependency Note

The ECS module and RDS/ElastiCache modules have a circular reference: RDS needs the ECS task security group to allow ingress, but ECS needs the RDS address for env vars. To resolve this, the ECS module creates the task security group early (before the service), and its ID is passed to the data layer modules. This works because Terraform resolves the dependency graph automatically — the security group resource has no dependency on RDS/ElastiCache outputs.

### Success Criteria:

#### Automated Verification:
- [ ] `cd iac/environments/dev && terraform init`
- [ ] `cd iac/environments/dev && terraform validate`
- [ ] `cd iac/environments/dev && terraform fmt -check`
- [ ] `cd iac/environments/dev && terraform plan -var="db_password=test"` (review output)

#### Manual Verification:
- [ ] Run `terraform apply -var="db_password=YOUR_SECRET"`
- [ ] ALB DNS returns `{"status": "ok"}` from `/health/live`
- [ ] `/health/ready` returns `{"db": true, "cache": true}`
- [ ] CloudWatch log group `/ecs/pa-compact-licensing-dev` has log streams

**Implementation Note**: After completing this phase, pause for manual `terraform apply` and health check verification before proceeding.

---

## Phase 6: GitHub Actions — DEV Auto-Deploy

### Overview
On merge to `main` (with changes in `api/`), build the Docker image tagged `sha-<7-char-hash>`, push to ECR, and deploy to the DEV ECS service via rolling update.

### Prerequisites
The following GitHub repository secrets must be configured:
- `AWS_ACCOUNT_ID` — AWS account ID
- `AWS_REGION` — e.g., `us-east-1`
- An IAM OIDC provider for GitHub Actions (recommended) OR `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`

### Changes Required:

#### 1. DEV Deploy Workflow
**File**: `.github/workflows/deploy-dev.yml`

```yaml
name: Deploy API to DEV

on:
  push:
    branches: [main]
    paths: [api/**]

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: pa-compact-licensing-api
  ECS_CLUSTER: pa-compact-licensing-dev
  ECS_SERVICE: pa-compact-licensing-dev
  CONTAINER_NAME: api

jobs:
  deploy:
    name: Build & Deploy to DEV
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image
        id: build
        working-directory: api
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: sha-${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --target app .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> "$GITHUB_OUTPUT"

      - name: Download current task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition ${{ env.ECS_SERVICE }} \
            --query taskDefinition \
            > task-definition.json

      - name: Render updated task definition
        id: render
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ steps.build.outputs.image }}

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### Success Criteria:

#### Automated Verification:
- [ ] Workflow YAML is valid (GitHub validates on push)
- [ ] `actionlint .github/workflows/deploy-dev.yml` (if installed locally)

#### Manual Verification:
- [ ] Push a change to `api/` on `main` → workflow triggers
- [ ] ECR shows new image tagged `sha-<hash>`
- [ ] ECS service updates to new task definition revision
- [ ] ALB returns healthy responses

**Implementation Note**: Before this workflow can run, the IAM OIDC provider and `github-actions-deploy` role must be created in AWS. This is a one-time manual step documented in the README (Phase 9).

---

## Phase 7: GitHub Actions — Release Build & Deploy

### Overview
Two-part workflow:
1. **On git tag push** (`v*.*.*`): Build Docker image tagged with the semver version, push to ECR
2. **Manual `workflow_dispatch`**: Choose an image tag and target environment (STAGING/PROD), deploy to ECS

### Changes Required:

#### 1. Release Build Workflow (tag-triggered)
**File**: `.github/workflows/release-build.yml`

```yaml
name: Build Release Image

on:
  push:
    tags: ["v*.*.*"]

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: pa-compact-licensing-api

jobs:
  build:
    name: Build & Push Release Image
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Extract version from tag
        id: version
        run: echo "tag=${GITHUB_REF_NAME}" >> "$GITHUB_OUTPUT"

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image
        working-directory: api
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          VERSION: ${{ steps.version.outputs.tag }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$VERSION --target app .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$VERSION
          echo "::notice::Image pushed: $ECR_REGISTRY/$ECR_REPOSITORY:$VERSION"
```

#### 2. Deploy to Environment Workflow (manual dispatch)
**File**: `.github/workflows/deploy-release.yml`

```yaml
name: Deploy Release to Environment

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: "Image tag to deploy (e.g., v1.2.3)"
        required: true
        type: string
      environment:
        description: "Target environment"
        required: true
        type: choice
        options:
          - staging
          - prod

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: pa-compact-licensing-api
  CONTAINER_NAME: api

jobs:
  deploy:
    name: Deploy ${{ inputs.image_tag }} to ${{ inputs.environment }}
    runs-on: ubuntu-latest

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Verify image exists in ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          aws ecr describe-images \
            --repository-name ${{ env.ECR_REPOSITORY }} \
            --image-ids imageTag=${{ inputs.image_tag }} \
            || (echo "::error::Image tag '${{ inputs.image_tag }}' not found in ECR" && exit 1)

      - name: Set environment-specific variables
        id: env-vars
        run: |
          if [ "${{ inputs.environment }}" = "staging" ]; then
            echo "cluster=pa-compact-licensing-staging" >> "$GITHUB_OUTPUT"
            echo "service=pa-compact-licensing-staging" >> "$GITHUB_OUTPUT"
          elif [ "${{ inputs.environment }}" = "prod" ]; then
            echo "cluster=pa-compact-licensing-prod" >> "$GITHUB_OUTPUT"
            echo "service=pa-compact-licensing-prod" >> "$GITHUB_OUTPUT"
          fi

      - name: Download current task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition ${{ steps.env-vars.outputs.service }} \
            --query taskDefinition \
            > task-definition.json

      - name: Render updated task definition
        id: render
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ inputs.image_tag }}

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render.outputs.task-definition }}
          service: ${{ steps.env-vars.outputs.service }}
          cluster: ${{ steps.env-vars.outputs.cluster }}
          wait-for-service-stability: true
```

### Success Criteria:

#### Automated Verification:
- [ ] Both workflow YAML files are valid

#### Manual Verification:
- [ ] Create tag `v0.1.0` → release-build workflow triggers → image appears in ECR tagged `v0.1.0`
- [ ] Go to Actions → "Deploy Release to Environment" → "Run workflow" → select `v0.1.0` and `staging` → deploys successfully
- [ ] ECS service in STAGING updates to the new image

---

## Phase 8: STAGING & PROD Environments

### Overview
Create Terraform configurations for STAGING and PROD environments, identical structure to DEV but with appropriate sizing.

### Changes Required:

#### 1. STAGING Environment
Copy `iac/environments/dev/` to `iac/environments/staging/` with these differences:

**File**: `iac/environments/staging/terraform.tfvars`

```hcl
aws_region            = "us-east-1"
environment           = "staging"
vpc_cidr              = "10.1.0.0/16"
task_cpu              = "256"
task_memory           = "512"
desired_count         = 1
rds_instance_class    = "db.t4g.micro"
elasticache_node_type = "cache.t4g.micro"
```

**File**: `iac/environments/staging/main.tf` — Same as DEV but with:
- Backend key: `environments/staging/terraform.tfstate`
- Default environment variable: `"staging"`

#### 2. PROD Environment
Copy with these differences:

**File**: `iac/environments/prod/terraform.tfvars`

```hcl
aws_region            = "us-east-1"
environment           = "prod"
vpc_cidr              = "10.2.0.0/16"
task_cpu              = "512"
task_memory           = "1024"
desired_count         = 2
rds_instance_class    = "db.t4g.small"
elasticache_node_type = "cache.t4g.small"
```

**File**: `iac/environments/prod/main.tf` — Same as DEV but with:
- Backend key: `environments/prod/terraform.tfstate`
- `single_nat = false` in VPC module (one NAT per AZ for HA)
- `multi_az = true` for RDS
- `skip_final_snapshot = false` for RDS
- `backup_retention_period = 30` for RDS

### Success Criteria:

#### Automated Verification:
- [ ] `cd iac/environments/staging && terraform init && terraform validate`
- [ ] `cd iac/environments/prod && terraform init && terraform validate`
- [ ] `terraform fmt -check -recursive iac/environments/`

#### Manual Verification:
- [ ] `terraform plan` for each environment shows expected resources
- [ ] Apply when ready — each environment is fully independent

---

## Phase 9: README

### Overview
Add deployment documentation to the repo root README.

### Changes Required:

**File**: `iac/README.md`

```markdown
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
   - Go to **Actions** → **Deploy Release to Environment**
   - Click **Run workflow**
   - Enter the image tag (e.g., `v1.0.0`) and select the target environment
   - Click **Run workflow** to start the deployment

### Manual DEV Deploy (re-deploy a specific commit)

You can also manually deploy to DEV by running:
```bash
# Find the image tag from ECR
aws ecr describe-images --repository-name pa-compact-licensing-api \
  --query 'imageDetails[*].imageTags' --output table

# Then use the "Deploy Release to Environment" workflow with environment=dev
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
```

### Success Criteria:

#### Automated Verification:
- [ ] README renders correctly in GitHub (check after push)

#### Manual Verification:
- [ ] A new team member can follow the README to understand the deployment process

---

## Testing Strategy

### Infrastructure Testing:
- `terraform validate` for syntax correctness
- `terraform plan` to preview changes before apply
- `terraform fmt -check -recursive` for formatting consistency

### Deployment Testing:
- Verify DEV auto-deploy end-to-end with a test commit
- Verify release build with a test tag `v0.1.0`
- Verify manual deploy workflow dispatch to STAGING

### Application Health:
- ALB health checks against `/health/ready` (checks Postgres + Redis)
- CloudWatch logs for application errors
- `aws ecs execute-command` for live debugging if needed

## Performance Considerations

- **Single NAT gateway** in DEV/STAGING saves ~$65/month per environment vs per-AZ NATs
- **S3 Gateway Endpoint** (free) reduces NAT data transfer costs for ECR image pulls
- **ECR lifecycle policy** keeps only 30 images to control storage costs
- **Deregistration delay** of 30s on ALB target group allows in-flight requests to complete during deployments
- **Circuit breaker** with rollback enabled prevents broken deployments from persisting

## References

- Existing Dockerfile: `api/Dockerfile`
- App configuration: `api/licensing_api/config.py`
- Health endpoints: `api/licensing_api/routes/health.py`
- CI workflow: `.github/workflows/api.yml`
