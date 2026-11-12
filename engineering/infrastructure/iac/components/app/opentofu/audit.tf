# The account's audit trail (SCRUM-84): who called which AWS API, and every read and
# write of an uploaded document, recorded outside the application as well as in it
# (Rule 4 §4.5).

resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "/aws/cloudtrail/${local.trail_name}"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.data.arn
}

resource "aws_iam_role" "cloudtrail_logs" {
  name = "${local.trail_name}-cloudtrail-logs"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "cloudtrail_logs" {
  name = "${local.trail_name}-cloudtrail-logs"
  role = aws_iam_role.cloudtrail_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
    }]
  })
}

resource "aws_cloudtrail" "account" {
  name                          = local.trail_name
  s3_bucket_name                = aws_s3_bucket.logs.id
  s3_key_prefix                 = "cloudtrail"
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.data.arn
  cloud_watch_logs_group_arn    = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn     = aws_iam_role.cloudtrail_logs.arn

  # Off where another trail already records the account's management events: a second
  # copy is charged per event.
  dynamic "advanced_event_selector" {
    for_each = var.cloudtrail_management_events ? [1] : []
    content {
      name = "Management events"

      field_selector {
        field  = "eventCategory"
        equals = ["Management"]
      }
    }
  }

  advanced_event_selector {
    name = "Reads and writes of uploaded documents"

    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }

    field_selector {
      field  = "resources.type"
      equals = ["AWS::S3::Object"]
    }

    field_selector {
      field       = "resources.ARN"
      starts_with = ["${aws_s3_bucket.documents.arn}/"]
    }
  }

  depends_on = [aws_s3_bucket_policy.logs]
}
