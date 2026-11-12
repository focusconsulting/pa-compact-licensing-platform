locals {
  # The account's bootstrap repo exports the jumpbox's security group when it creates
  # one (create_jumpbox); states applied before that output existed have none.
  jumpbox_sg_ids = compact([try(data.terraform_remote_state.network.outputs.jumpbox_security_group_id, null)])
}

# Each group allows only the ports in use, in both directions. Rules stay inline so the
# group's rule set is exactly what is written here: a rule removed from this file is
# removed from AWS. Egress to another group is by the VPC's CIDR, because two groups
# cannot name each other in inline rules; the receiving group's ingress rule names the
# sending group, which is what restricts the connection.
data "aws_vpc" "main" {
  id = data.terraform_remote_state.network.outputs.vpc_id
}

# Security Group for the internal Application Load Balancer
# CloudFront VPC Origin traffic arrives through the CloudFront-managed service SG
# (CloudFront-VPCOrigins-Service-SG). That SG must be referenced explicitly here —
# allowing the VPC CIDR is not sufficient because VPC Origin traffic is matched
# by SG membership, not source IP.
resource "aws_security_group" "alb_sg" {
  description = "${var.environment_name}-${local.application_name}-alb-sg"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id

  egress {
    description = "API port on the tasks"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  tags = {
    Name = "${var.environment_name}-${local.application_name}-alb-sg"
  }
}

# Allow traffic from CloudFront to the ALB by referencing the security group CloudFront VPC Origins creates.
resource "aws_vpc_security_group_ingress_rule" "alb_from_cloudfront" {
  security_group_id            = aws_security_group.alb_sg.id
  referenced_security_group_id = data.aws_security_group.cloudfront_vpc_origin.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "HTTPS from CloudFront VPC Origin"

  depends_on = [aws_cloudfront_vpc_origin.alb_origin]
}

# Security Group for ECS Fargate tasks
# The API, the Worker, and the scheduled jobs. Only accepts traffic on port 8000 from the ALB
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

  dynamic "ingress" {
    for_each = local.jumpbox_sg_ids
    content {
      description     = "All ports from jumpbox (SSM tunnel)"
      from_port       = 0
      to_port         = 0
      protocol        = "-1"
      security_groups = [ingress.value]
    }
  }

  egress {
    description = "PostgreSQL on the database"
    from_port   = local.db_port
    to_port     = local.db_port
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # AWS APIs (ECR, Secrets Manager, SSM, CloudWatch, X-Ray, S3) and Cognito's JWKS have
  # no fixed addresses, and the tasks reach them through the NAT, so the destination is
  # open and the port is not.
  egress {
    description = "HTTPS to AWS APIs and Cognito"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "SMTP with STARTTLS to SES"
    from_port   = 587
    to_port     = 587
    protocol    = "tcp"
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

  dynamic "ingress" {
    for_each = local.jumpbox_sg_ids
    content {
      description     = "PostgreSQL from jumpbox (SSM tunnel)"
      from_port       = local.db_port
      to_port         = local.db_port
      protocol        = "tcp"
      security_groups = [ingress.value]
    }
  }

  # The database opens no connections of its own. An empty list, not an omitted block:
  # omitting it would leave whatever egress rules the group already has.
  egress = []

  tags = {
    Name = "${var.environment_name}-${local.application_name}-rds-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}
