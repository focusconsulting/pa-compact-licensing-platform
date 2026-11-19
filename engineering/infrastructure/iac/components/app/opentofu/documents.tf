# The documents bucket (backlog D9, F-12; engineering/docs/documents.md). Browsers upload
# and download through presigned links the API signs; GuardDuty scans each version
# (guardduty.tf), and the bucket refuses to serve any version not tagged clean.

data "aws_caller_identity" "current" {}

locals {
  documents_bucket_name = "${var.environment_name}-${local.application_name}-documents"
  # The tag GuardDuty Malware Protection writes on each object version it scans.
  scan_tag = "GuardDutyMalwareScanStatus"
}

resource "aws_kms_key" "documents" {
  description         = "${var.environment_name} ${local.application_name} documents bucket"
  enable_key_rotation = true
  # Who may use the key is granted by IAM policies (the task role, GuardDuty's role).
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AccountAdministersAndIamGrants"
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
      Action    = "kms:*"
      Resource  = "*"
    }]
  })
}

resource "aws_kms_alias" "documents" {
  name          = "alias/${local.documents_bucket_name}"
  target_key_id = aws_kms_key.documents.key_id
}

resource "aws_s3_bucket" "documents" {
  bucket = local.documents_bucket_name
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Versioned: an upload form can be posted again until it expires, so downloads serve only
# the version the Worker saw scanned. The UI never reuses a key; each file is a new document.
resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.documents.arn
    }
    bucket_key_enabled = true
  }
}

# How long a document is kept is a records decision, not made here: nothing expires.
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# The browser posts the upload form straight to the bucket from the client's origin.
resource "aws_s3_bucket_cors_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  cors_rule {
    allowed_methods = ["POST"]
    allowed_origins = ["https://${var.dns_name}"]
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "TlsOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.documents.arn, "${aws_s3_bucket.documents.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        # A second wall behind the API's own check: no one but the scanner reads a version
        # GuardDuty has not found clean, so a bug in the API cannot serve malware.
        Sid       = "OnlyCleanVersionsAreRead"
        Effect    = "Deny"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource  = "${aws_s3_bucket.documents.arn}/*"
        Condition = {
          StringNotEquals = { "s3:ExistingObjectTag/${local.scan_tag}" = "NO_THREATS_FOUND" }
          ArnNotEquals    = { "aws:PrincipalArn" = aws_iam_role.guardduty_malware_protection.arn }
        }
      },
      {
        # Otherwise anyone allowed to tag, such as an account administrator, could mark an
        # infected version clean and make it readable.
        Sid       = "OnlyGuardDutyTags"
        Effect    = "Deny"
        Principal = "*"
        Action = [
          "s3:PutObjectTagging",
          "s3:PutObjectVersionTagging",
          "s3:DeleteObjectTagging",
          "s3:DeleteObjectVersionTagging",
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
        Condition = {
          ArnNotEquals = { "aws:PrincipalArn" = aws_iam_role.guardduty_malware_protection.arn }
        }
      },
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.documents]
}

# The API signs uploads and downloads, and the Worker reads scan tags and a clean file's first
# bytes; all three run as the task role.
resource "aws_iam_role_policy" "ecs_task_documents" {
  name = "${var.environment_name}-${local.application_name}-documents-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DocumentObjects"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:GetObjectTagging",
        ]
        Resource = "${aws_s3_bucket.documents.arn}/documents/*"
      },
      {
        # So a missing object answers 404, not 403.
        Sid      = "ListDocuments"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.documents.arn
      },
      {
        Sid      = "DocumentsKey"
        Effect   = "Allow"
        Action   = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = aws_kms_key.documents.arn
      },
    ]
  })
}
