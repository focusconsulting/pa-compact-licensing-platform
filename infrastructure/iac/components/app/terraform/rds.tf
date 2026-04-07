
resource "aws_db_subnet_group" "db_subnet" {
  name       = "${var.environment_name}-${local.application_name}-db-subnet-group"
  subnet_ids = aws_subnet.web_subnets[*].id
}

resource "aws_rds_cluster_parameter_group" "cluster" {
  name   = local.cluster_identifier
  family = "aurora-postgresql16"

  dynamic "parameter" {
    for_each = local.cluster_parameters
    content {
      name         = parameter.key
      value        = parameter.value["value"]
      apply_method = lookup(parameter.value, "apply_method", "immediate")
    }
  }
}


resource "aws_rds_cluster" "rds_aurora_cluster" {
  cluster_identifier                  = local.cluster_identifier
  engine                              = "aurora-postgresql"
  engine_version                      = "16.2"
  db_subnet_group_name                = aws_db_subnet_group.rds_subnet_group.name
  database_name                       = local.db_name
  master_username                     = jsondecode(aws_secretsmanager_secret_version.db_credentials_version.secret_string)["username"]
  master_password                     = jsondecode(aws_secretsmanager_secret_version.db_credentials_version.secret_string)["password"]
  iam_database_authentication_enabled = false
  port                                = local.db_port
  db_cluster_parameter_group_name     = aws_rds_cluster_parameter_group.cluster.id
  storage_encrypted                   = true
  deletion_protection                 = false
  vpc_security_group_ids              = [aws_security_group.rds_security_group.id]
  skip_final_snapshot                 = true

  tags = {
    "layer"       = "data"
    "application" = local.application_name
    "Name"        = "${local.cluster_identifier}"
  }
}

# Have to define engine and engine_version in the cluster instance resource too
# Else the instance will default to a mismatched version
# https://github.com/terraform-providers/terraform-provider-aws/issues/4779
resource "aws_rds_cluster_instance" "cluster_instances" {
  count                        = var.instance_count
  identifier                   = "${local.cluster_identifier}-instance-${count.index}"
  cluster_identifier           = aws_rds_cluster.rds_aurora_cluster.id
  engine                       = "aurora-postgresql"
  engine_version               = "16.2"
  instance_class               = var.db_instance_class
  performance_insights_enabled = false
}

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${local.cluster_identifier}-rds-aurora"
  subnet_ids = aws_db_subnet_group.db_subnet.subnet_ids

  tags = {
    "layer"       = "data"
    "application" = local.application_name
    "Name"        = "${local.cluster_identifier}"
    "env"         = var.environment_name
  }
}

data "aws_region" "current" {}

resource "aws_security_group" "rds_security_group" {
  description = "${var.environment_name}-${local.application_name}-rds-security-group"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = var.security_group_ids
    content {
      description     = ""
      from_port       = local.db_port
      to_port         = local.db_port
      protocol        = "tcp"
      security_groups = [ingress.value]
      self            = true
    }
  }

  ingress {
    description = ""
    from_port   = local.db_port
    to_port     = local.db_port
    protocol    = "tcp"
  }

  name_prefix = "${local.cluster_identifier}-rds-security-group"

  tags = {
    "layer"       = "data"
    "application" = local.application_name
    "Name"        = "${local.cluster_identifier}-rds"
    "env"         = var.environment_name
  }

  vpc_id = aws_vpc.vpc.id

  lifecycle {
    create_before_destroy = true
  }
}

