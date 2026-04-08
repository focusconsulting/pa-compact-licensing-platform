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

  # Internal ALB origin for API requests
  origin {
    domain_name = aws_lb.api_alb.dns_name
    origin_id   = "ALB-Origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  default_root_object = "index.html"

  # Default cache behavior — serves the Next.js frontend from S3
  default_cache_behavior {
    target_origin_id       = "S3-Origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # API cache behavior — forwards all requests to the internal ALB uncached
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "ALB-Origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept", "Content-Type"]
      cookies {
        forward = "all"
      }
    }

    # Disable caching for API responses
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
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
    cloudfront_default_certificate = true
  }
}
