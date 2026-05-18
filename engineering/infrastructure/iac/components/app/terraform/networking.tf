data "aws_secretsmanager_secret_version" "jumpbox" {
  secret_id = "${var.environment_name}-jumpbox-sgid-tfvar"
}

locals {
  jumpbox_sg_id = jsondecode(data.aws_secretsmanager_secret_version.jumpbox.secret_string)["jumpbox_sg_id"]
}

# Security Group for the internal Application Load Balancer
# CloudFront VPC Origin traffic arrives through the CloudFront-managed service SG
# (CloudFront-VPCOrigins-Service-SG). That SG must be referenced explicitly here —
# allowing the VPC CIDR is not sufficient because VPC Origin traffic is matched
# by SG membership, not source IP.
resource "aws_security_group" "alb_sg" {
  description = "${var.environment_name}-${local.application_name}-alb-sg"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id

  ingress {
    description     = "HTTP from CloudFront VPC Origin"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [data.aws_security_group.cloudfront_vpc_origin.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment_name}-${local.application_name}-alb-sg"
  }
}

# Security Group for ECS Fargate tasks
# Only accepts traffic on port 8000 from the ALB
resource "aws_security_group" "ecs_sg" {
  description = "${var.environment_name}-${local.application_name}-ecs-sg"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id

  ingress {
    description     = "API port from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  ingress {
    description     = "All ports from jumpbox (SSM tunnel)"
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [local.jumpbox_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment_name}-${local.application_name}-ecs-sg"
  }
}

# Security Group for Aurora RDS
# Only accepts PostgreSQL traffic from ECS tasks
resource "aws_security_group" "rds_sg" {
  description = "${var.environment_name}-${local.application_name}-rds-sg"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = local.db_port
    to_port         = local.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  ingress {
    description     = "PostgreSQL from jumpbox (SSM tunnel)"
    from_port       = local.db_port
    to_port         = local.db_port
    protocol        = "tcp"
    security_groups = [local.jumpbox_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment_name}-${local.application_name}-rds-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for ElastiCache Redis
# Only accepts Redis traffic from ECS tasks
resource "aws_security_group" "redis_sg" {
  description = "${var.environment_name}-${local.application_name}-redis-sg"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id

  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  ingress {
    description     = "Redis from jumpbox (SSM tunnel)"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [local.jumpbox_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment_name}-${local.application_name}-redis-sg"
  }
}
