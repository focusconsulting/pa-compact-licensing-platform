# CloudFront Function that returns 403 — used to block paths at the CDN edge
# before requests reach the VPC. Runs on viewer-request so no origin is contacted.
resource "aws_cloudfront_function" "block_403" {
  name    = "${var.environment_name}-${local.application_name}-block-403"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOF
    function handler(event) {
      return { statusCode: 403, statusDescription: "Forbidden" };
    }
  EOF
}

# CloudFront VPC Origin — wraps the internal ALB so CloudFront can reach it
# without making the ALB internet-facing. CloudFront injects ENIs into the VPC;
# traffic arrives from within the VPC CIDR, which the ALB SG already allows.
resource "aws_cloudfront_vpc_origin" "alb_origin" {
  vpc_origin_endpoint_config {
    name                   = "${var.environment_name}-${local.application_name}-alb-origin"
    arn                    = aws_lb.api_alb.arn
    http_port              = 80
    https_port             = 443
    origin_protocol_policy = "https-only"

    origin_ssl_protocols {
      items    = ["TLSv1.2"]
      quantity = 1
    }
  }
}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

# CloudFront VPC Origins automatically creates and manages a security group in the account.
# We make it available as a data source for other resources
data "aws_security_group" "cloudfront_vpc_origin" {
  name       = "CloudFront-VPCOrigins-Service-SG"
  depends_on = [aws_cloudfront_vpc_origin.alb_origin]
}

# S3 Bucket for Front-End Client Assets
resource "aws_s3_bucket" "client_assets" {
  bucket = "${var.environment_name}-${local.application_name}-client-assets"
}

# Block all public S3 access — CloudFront OAI is the only read path
resource "aws_s3_bucket_public_access_block" "client_assets" {
  bucket                  = aws_s3_bucket.client_assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# A deploy replaces every file (`aws s3 sync --delete`); the previous deploy's versions
# are kept for 30 days, then expire.
resource "aws_s3_bucket_versioning" "client_assets" {
  bucket = aws_s3_bucket.client_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "client_assets" {
  bucket = aws_s3_bucket.client_assets.id

  rule {
    id     = "expire-previous-deploys"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    expiration {
      expired_object_delete_marker = true
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.client_assets]
}

resource "aws_cloudfront_origin_access_identity" "frontend_oai" {
  comment = "OAI for accessing S3 bucket for client assets"
}

resource "aws_s3_bucket_policy" "client_assets_policy" {
  bucket = aws_s3_bucket.client_assets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.frontend_oai.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.client_assets.arn}/*"
      }
    ]
  })
}

# CloudFront Distribution for S3 Bucket
# - Default origin: S3 (Next.js static export)
# - /api/* origin: internal ALB (Python FastAPI)
resource "aws_cloudfront_distribution" "frontend_distribution" {
  # S3 origin for static frontend assets
  origin {
    domain_name = aws_s3_bucket.client_assets.bucket_regional_domain_name
    origin_id   = "S3-Origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.frontend_oai.cloudfront_access_identity_path
    }
  }

  # Internal ALB origin for API requests via CloudFront VPC Origin.
  # VPC Origins allow CloudFront to reach private ALBs without making them internet-facing —
  # CloudFront injects ENIs into the VPC so traffic arrives from within the VPC CIDR.
  origin {
    domain_name = aws_lb.api_alb.dns_name
    origin_id   = "ALB-Origin"

    vpc_origin_config {
      vpc_origin_id            = aws_cloudfront_vpc_origin.alb_origin.id
      origin_read_timeout      = 30
      origin_keepalive_timeout = 5
    }
  }

  enabled             = true
  default_root_object = "index.html"
  web_acl_id          = aws_wafv2_web_acl.cloudfront.arn

  logging_config {
    bucket = aws_s3_bucket.logs.bucket_domain_name
    prefix = "cloudfront/"
  }
  aliases = [var.dns_name]

  # Default cache behavior — serves the Next.js frontend from S3
  default_cache_behavior {
    target_origin_id           = "S3-Origin"
    viewer_protocol_policy     = "redirect-to-https"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # Block Swagger/OpenAPI docs at the CDN edge — 403 returned before origin is contacted.
  # Matches /api/docs*, /api/redoc*, /api/openapi.json as forwarded by CloudFront.
  ordered_cache_behavior {
    path_pattern               = "/api/docs*"
    target_origin_id           = "ALB-Origin"
    viewer_protocol_policy     = "redirect-to-https"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.block_403.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/api/redoc*"
    target_origin_id           = "ALB-Origin"
    viewer_protocol_policy     = "redirect-to-https"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.block_403.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/api/openapi.json"
    target_origin_id           = "ALB-Origin"
    viewer_protocol_policy     = "redirect-to-https"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.block_403.arn
    }
  }

  # API cache behavior — forwards all requests to the internal ALB uncached
  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "ALB-Origin"
    viewer_protocol_policy     = "redirect-to-https"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    allowed_methods            = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods             = ["GET", "HEAD"]

    cache_policy_id = data.aws_cloudfront_cache_policy.caching_disabled.id
    # Forwards the viewer's Host header, which is what makes the load balancer's
    # certificate (for dns_name) match: CloudFront checks an origin's certificate
    # against the origin domain or the forwarded Host.
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer.id
  }

  # Return index.html for 404s so Next.js client-side routing works on direct URL navigation
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US"]
    }
  }

  viewer_certificate {
    acm_certificate_arn      = data.aws_acm_certificate.wildcard.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}
