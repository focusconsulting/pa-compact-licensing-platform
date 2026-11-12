resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${local.cluster_identifier}-rds-aurora"
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  tags = {
    "layer"       = "data"
    "application" = local.application_name
    "Name"        = local.cluster_identifier
    "env"         = var.environment_name
  }
}

resource "aws_rds_cluster_parameter_group" "cluster" {
  name   = local.cluster_identifier
  family = "aurora-postgresql16"

  # DDL and statements slower than a second are logged, never with their bound values,
  # which may be PII. Written out, not in local.cluster_parameters with the rest, so
  # Checkov's query-logging check (CKV2_AWS_27) can see them.
  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_parameter_max_length"
    value = "0"
  }

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
  engine_version                      = "16.13"
  db_subnet_group_name                = aws_db_subnet_group.rds_subnet_group.name
  database_name                       = local.db_name
  master_username                     = var.db_username
  master_password                     = random_password.db_master.result
  iam_database_authentication_enabled = false
  port                                = local.db_port
  db_cluster_parameter_group_name     = aws_rds_cluster_parameter_group.cluster.id
  storage_encrypted                   = true
  kms_key_id                          = aws_kms_key.data.arn
  vpc_security_group_ids              = [aws_security_group.rds_sg.id]
  backup_retention_period             = var.backup_retention_period
  copy_tags_to_snapshot               = true
  enabled_cloudwatch_logs_exports     = ["postgresql"]

  # An environment that is torn down keeps neither; anywhere data must survive keeps both.
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = !var.deletion_protection
  final_snapshot_identifier = var.deletion_protection ? "${local.cluster_identifier}-final" : null

  # The log group must exist, encrypted, before the cluster starts writing to it.
  depends_on = [aws_cloudwatch_log_group.postgresql]

  tags = {
    "layer"       = "data"
    "application" = local.application_name
    "Name"        = local.cluster_identifier
  }
}

# Have to define engine and engine_version in the cluster instance resource too
# Else the instance will default to a mismatched version
# https://github.com/terraform-providers/terraform-provider-aws/issues/4779
resource "aws_rds_cluster_instance" "cluster_instances" {
  count                      = var.instance_count
  identifier                 = "${local.cluster_identifier}-instance-${count.index}"
  cluster_identifier         = aws_rds_cluster.rds_aurora_cluster.id
  engine                     = "aurora-postgresql"
  engine_version             = "16.13"
  instance_class             = var.db_instance_class
  auto_minor_version_upgrade = true

  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.data.arn

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
}

# RDS would create this group itself, unencrypted and kept forever, on the first export.
resource "aws_cloudwatch_log_group" "postgresql" {
  name              = "/aws/rds/cluster/${local.cluster_identifier}/postgresql"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.data.arn
}

# Enhanced monitoring: operating-system metrics from the instance every minute.
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.environment_name}-${local.application_name}-rds-monitoring"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

data "aws_region" "current" {}
