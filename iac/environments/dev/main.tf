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

data "aws_ecr_repository" "api" {
  name = "pa-compact-licensing-api"
}

# --- Task Security Group (created here to avoid circular module deps) ---

resource "aws_security_group" "ecs_tasks" {
  name   = "${var.project_name}-${var.environment}-tasks"
  vpc_id = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-${var.environment}-tasks" }
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

# --- Secrets ---

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
  allowed_security_group_ids = [aws_security_group.ecs_tasks.id]
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
  allowed_security_group_ids = [aws_security_group.ecs_tasks.id]
  node_type                  = var.elasticache_node_type
}

# --- ECS / Fargate ---

module "ecs" {
  source                 = "../../modules/ecs"
  name                   = "${var.project_name}-${var.environment}"
  aws_region             = var.aws_region
  environment            = "DEV"
  vpc_id                 = module.vpc.vpc_id
  public_subnet_ids      = module.vpc.public_subnet_ids
  private_subnet_ids     = module.vpc.private_subnet_ids
  ecr_repository_url     = data.aws_ecr_repository.api.repository_url
  image_tag              = var.image_tag
  task_cpu               = var.task_cpu
  task_memory            = var.task_memory
  desired_count          = var.desired_count
  db_host                = module.rds.address
  db_port                = module.rds.port
  secret_arn             = module.secrets.secret_arn
  task_security_group_id = aws_security_group.ecs_tasks.id
}
