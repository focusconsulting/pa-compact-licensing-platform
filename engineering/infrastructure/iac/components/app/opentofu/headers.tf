# The security headers CloudFront adds to every response, from the client bucket and the
# API alike (SCRUM-84). The API's policy also forbids storing its responses.

locals {
  # Presigned upload and download links name the bucket's regional host, except in
  # us-east-1, where boto3 signs for the global one.
  documents_origins = [
    "https://${local.documents_bucket_name}.s3.amazonaws.com",
    "https://${local.documents_bucket_name}.s3.${var.aws_region}.amazonaws.com",
  ]

  content_security_policy = join("; ", [
    "default-src 'self'",
    # 'unsafe-inline': Next's static export writes inline scripts into every page, and
    # with no server there is nothing to issue a nonce (decided 2026-11-12).
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self'",
    # USWDS's stylesheet embeds some icons as data: URLs.
    "img-src 'self' data:",
    "font-src 'self'",
    # The browser signs in against Cognito and posts uploads straight to the documents bucket.
    "connect-src ${join(" ", concat(["'self'", "https://cognito-idp.${var.aws_region}.amazonaws.com"], local.documents_origins))}",
    "form-action ${join(" ", concat(["'self'"], local.documents_origins))}",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "object-src 'none'",
  ])
}

moved {
  from = aws_cloudfront_response_headers_policy.security
  to   = aws_cloudfront_response_headers_policy.security["client"]
}

resource "aws_cloudfront_response_headers_policy" "security" {
  for_each = {
    client = "security-headers"
    api    = "api-security-headers"
  }

  name = "${var.environment_name}-${local.application_name}-${each.value}"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 63072000 # two years
      include_subdomains         = true
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    content_security_policy {
      content_security_policy = local.content_security_policy
      override                = true
    }
  }

  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "camera=(), microphone=(), geolocation=(), payment=()"
      override = true
    }

    items {
      header   = "Cross-Origin-Opener-Policy"
      value    = "same-origin"
      override = true
    }

    items {
      header   = "Cross-Origin-Resource-Policy"
      value    = "same-origin"
      override = true
    }

    # Caching is off at CloudFront already; this keeps browsers and proxies from
    # storing API responses, which carry personal data.
    dynamic "items" {
      for_each = each.key == "api" ? ["no-store"] : []

      content {
        header   = "Cache-Control"
        value    = items.value
        override = true
      }
    }
  }

  # S3 and the load balancer name themselves in it.
  remove_headers_config {
    items {
      header = "Server"
    }
  }
}
