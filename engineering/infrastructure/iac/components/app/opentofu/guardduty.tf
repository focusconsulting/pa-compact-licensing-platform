# GuardDuty Malware Protection for S3 on the documents bucket (backlog D9, F-12). It scans
# each new object version and tags it GuardDutyMalwareScanStatus; the Worker reads the tag
# (licensing_api/scans.py). It needs no GuardDuty detector. The role's policy is the one
# AWS documents for a protected bucket encrypted with a customer-managed key.

resource "aws_iam_role" "guardduty_malware_protection" {
  name = "${var.environment_name}-${local.application_name}-guardduty-malware-protection"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "malware-protection-plan.guardduty.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnLike = {
          "aws:SourceArn" = "arn:aws:guardduty:${var.aws_region}:${data.aws_caller_identity.current.account_id}:malware-protection-plan/*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "guardduty_malware_protection" {
  name = "${var.environment_name}-${local.application_name}-guardduty-malware-protection"
  role = aws_iam_role.guardduty_malware_protection.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ManageItsEventBridgeRule"
        Effect = "Allow"
        Action = ["events:PutRule", "events:DeleteRule", "events:PutTargets", "events:RemoveTargets"]
        Resource = [
          "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/DO-NOT-DELETE-AmazonGuardDutyMalwareProtectionS3*"
        ]
        Condition = {
          StringLike = { "events:ManagedBy" = "malware-protection-plan.guardduty.amazonaws.com" }
        }
      },
      {
        Sid    = "WatchItsEventBridgeRule"
        Effect = "Allow"
        Action = ["events:DescribeRule", "events:ListTargetsByRule"]
        Resource = [
          "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/DO-NOT-DELETE-AmazonGuardDutyMalwareProtectionS3*"
        ]
      },
      {
        Sid    = "TagScannedVersions"
        Effect = "Allow"
        Action = [
          "s3:PutObjectTagging",
          "s3:GetObjectTagging",
          "s3:PutObjectVersionTagging",
          "s3:GetObjectVersionTagging",
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Sid      = "SendBucketEvents"
        Effect   = "Allow"
        Action   = ["s3:PutBucketNotification", "s3:GetBucketNotification"]
        Resource = aws_s3_bucket.documents.arn
      },
      {
        Sid      = "ValidateTheBucket"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.documents.arn}/malware-protection-resource-validation-object"
      },
      {
        Sid      = "CheckBucketOwnership"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.documents.arn
      },
      {
        Sid      = "ReadToScan"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Sid      = "DecryptToScan"
        Effect   = "Allow"
        Action   = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = aws_kms_key.documents.arn
        Condition = {
          StringLike = { "kms:ViaService" = "s3.*.amazonaws.com" }
        }
      },
    ]
  })
}

resource "aws_guardduty_malware_protection_plan" "documents" {
  role = aws_iam_role.guardduty_malware_protection.arn

  protected_resource {
    s3_bucket {
      bucket_name     = aws_s3_bucket.documents.id
      object_prefixes = ["documents/"]
    }
  }

  actions {
    tagging {
      status = "ENABLED"
    }
  }

  depends_on = [aws_iam_role_policy.guardduty_malware_protection]
}
