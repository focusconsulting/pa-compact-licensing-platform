# One customer-managed key per environment for what the system stores outside the
# documents bucket, which has its own (documents.tf): the database and its backups,
# secrets, logs, and alerts (SCRUM-84).

locals {
  # The log groups CloudWatch Logs may encrypt with the key: this environment's only.
  log_group_arn_prefix = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group"
  encrypted_log_group_patterns = [
    "${local.log_group_arn_prefix}:/ecs/${local.application_name}/${var.environment_name}/*",
    "${local.log_group_arn_prefix}:/aws/rds/cluster/${local.cluster_identifier}/*",
    "${local.log_group_arn_prefix}:aws-waf-logs-${local.waf_name}-*",
  ]
}

resource "aws_kms_key" "data" {
  description         = "${var.environment_name} ${local.application_name} database, secrets, logs, and alerts"
  enable_key_rotation = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Who may use the key is granted by IAM policies on the roles in this module.
        Sid       = "AccountAdministersAndIamGrants"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "CloudWatchLogsEncryptsThisEnvironmentsLogGroups"
        Effect    = "Allow"
        Principal = { Service = "logs.${var.aws_region}.amazonaws.com" }
        Action    = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"]
        Resource  = "*"
        Condition = {
          ArnLike = { "kms:EncryptionContext:aws:logs:arn" = local.encrypted_log_group_patterns }
        }
      },
      {
        # An alarm cannot publish to an encrypted topic unless CloudWatch may use its key.
        Sid       = "CloudWatchAlarmsPublishToTheAlertsTopic"
        Effect    = "Allow"
        Principal = { Service = "cloudwatch.amazonaws.com" }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey*"]
        Resource  = "*"
        Condition = {
          StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        }
      },
    ]
  })
}

resource "aws_kms_alias" "data" {
  name          = "alias/${var.environment_name}-${local.application_name}-data"
  target_key_id = aws_kms_key.data.key_id
}
