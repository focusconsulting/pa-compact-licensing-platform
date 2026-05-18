# Look up the pre-existing Route 53 hosted zone for this environment
data "aws_route53_zone" "main" {
  name         = local.hosted_zone_name
  private_zone = false
}

# Look up the pre-existing wildcard ACM certificate.
# Must use the us_east_1 provider — CloudFront requires certificates in us-east-1.
data "aws_acm_certificate" "wildcard" {
  provider = aws.us_east_1
  domain   = "*.${local.hosted_zone_name}"
  statuses = ["ISSUED"]
}

# DNS A-record alias pointing the site FQDN at the CloudFront distribution
resource "aws_route53_record" "site" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.dns_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend_distribution.domain_name
    zone_id                = aws_cloudfront_distribution.frontend_distribution.hosted_zone_id
    evaluate_target_health = false
  }
}
