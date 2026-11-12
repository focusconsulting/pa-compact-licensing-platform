# Web firewalls (SCRUM-84). Two, because there are two front doors: CloudFront, for the
# client and the API, and the Cognito user pool, which the browser signs in against
# directly and so never passes through CloudFront. Each allows by default and limits
# how fast one address may call; CloudFront's also applies AWS's managed rule groups.
# The user pool's has none: Cognito validates its own requests and locks out repeated
# failures, and the account-takeover group cannot be attached to a user pool.

locals {
  waf_name = "${var.environment_name}-${local.application_name}"

  # Requests per five minutes from one IP address. SCRUM-139 tunes the public limit
  # against the verification page, the first route under /api/public/.
  waf_cloudfront_rate_rules = {
    public = { priority = 0, path = "/api/public/", limit = 300 }
    api    = { priority = 1, path = "/api/", limit = 2000 }
  }
  waf_sign_in_rate_limit = 200

  # Evaluated in this order, after the rate rules. AWSManagedRulesKnownBadInputsRuleSet
  # follows them as a rule of its own in the web ACL.
  waf_cloudfront_managed_groups = [
    "AWSManagedRulesAmazonIpReputationList",
    "AWSManagedRulesCommonRuleSet",
    "AWSManagedRulesSQLiRuleSet",
  ]
  # Rules inside a managed group that count instead of block. The common rule set's body
  # limit is 8 KB, which real API requests exceed.
  waf_counted_rules = {
    AWSManagedRulesCommonRuleSet = ["SizeRestrictions_BODY"]
  }

  # WAF logs carry every request header, so the ones that hold a session are blanked.
  waf_redacted_headers = ["authorization", "cookie"]
}

resource "aws_wafv2_web_acl" "cloudfront" {
  # A web ACL for CloudFront lives in us-east-1 whatever the environment's region.
  provider = aws.us_east_1

  name  = "${local.waf_name}-cloudfront"
  scope = "CLOUDFRONT"

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = local.waf_cloudfront_rate_rules
    content {
      name     = "rate-${rule.key}"
      priority = rule.value.priority

      action {
        block {}
      }

      statement {
        rate_based_statement {
          limit                 = rule.value.limit
          aggregate_key_type    = "IP"
          evaluation_window_sec = 300

          scope_down_statement {
            byte_match_statement {
              search_string         = rule.value.path
              positional_constraint = "STARTS_WITH"

              field_to_match {
                uri_path {}
              }

              text_transformation {
                priority = 0
                type     = "NONE"
              }
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.waf_name}-cloudfront-rate-${rule.key}"
        sampled_requests_enabled   = true
      }
    }
  }

  dynamic "rule" {
    for_each = local.waf_cloudfront_managed_groups
    content {
      name     = rule.value
      priority = 10 + rule.key

      override_action {
        none {}
      }

      statement {
        managed_rule_group_statement {
          name        = rule.value
          vendor_name = "AWS"

          dynamic "rule_action_override" {
            for_each = lookup(local.waf_counted_rules, rule.value, [])
            content {
              name = rule_action_override.value

              action_to_use {
                count {}
              }
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.waf_name}-cloudfront-${rule.value}"
        sampled_requests_enabled   = true
      }
    }
  }

  # Written out, not in the list above: Checkov's Log4j checks look for the group by
  # name and cannot see inside a dynamic block.
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 20

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.waf_name}-cloudfront-AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.waf_name}-cloudfront"
    sampled_requests_enabled   = true
  }
}

resource "aws_wafv2_web_acl" "cognito" {
  #checkov:skip=CKV_AWS_192:The Log4j group guards the server behind the firewall, and here that is Cognito's own API, which AWS runs.
  name  = "${local.waf_name}-cognito"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-sign-in"
    priority = 0

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit                 = local.waf_sign_in_rate_limit
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.waf_name}-cognito-rate-sign-in"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.waf_name}-cognito"
    sampled_requests_enabled   = true
  }
}

resource "aws_wafv2_web_acl_association" "cognito" {
  resource_arn = aws_cognito_user_pool.main.arn
  web_acl_arn  = aws_wafv2_web_acl.cognito.arn
}

# WAF writes only to log groups whose names start aws-waf-logs-, and CloudFront's web
# ACL only to one in us-east-1.
resource "aws_cloudwatch_log_group" "waf_cloudfront" {
  provider = aws.us_east_1

  name              = "aws-waf-logs-${local.waf_name}-cloudfront"
  retention_in_days = 365
  # A log group can use only a key from its own region, and this one is always in
  # us-east-1. Elsewhere it holds request metadata, session headers redacted, under
  # the service's own key.
  kms_key_id = var.aws_region == "us-east-1" ? aws_kms_key.data.arn : null
}

resource "aws_cloudwatch_log_group" "waf_cognito" {
  name              = "aws-waf-logs-${local.waf_name}-cognito"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.data.arn
}

data "aws_iam_policy_document" "waf_log_delivery" {
  for_each = {
    cloudfront = aws_cloudwatch_log_group.waf_cloudfront.arn
    cognito    = aws_cloudwatch_log_group.waf_cognito.arn
  }

  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${each.value}:*"]

    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "waf_cloudfront" {
  provider = aws.us_east_1

  policy_name     = "${local.waf_name}-waf-logs-cloudfront"
  policy_document = data.aws_iam_policy_document.waf_log_delivery["cloudfront"].json
}

resource "aws_cloudwatch_log_resource_policy" "waf_cognito" {
  policy_name     = "${local.waf_name}-waf-logs-cognito"
  policy_document = data.aws_iam_policy_document.waf_log_delivery["cognito"].json
}

resource "aws_wafv2_web_acl_logging_configuration" "cloudfront" {
  provider = aws.us_east_1

  resource_arn            = aws_wafv2_web_acl.cloudfront.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf_cloudfront.arn]

  dynamic "redacted_fields" {
    for_each = local.waf_redacted_headers
    content {
      single_header {
        name = redacted_fields.value
      }
    }
  }

  depends_on = [aws_cloudwatch_log_resource_policy.waf_cloudfront]
}

resource "aws_wafv2_web_acl_logging_configuration" "cognito" {
  resource_arn            = aws_wafv2_web_acl.cognito.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf_cognito.arn]

  dynamic "redacted_fields" {
    for_each = local.waf_redacted_headers
    content {
      single_header {
        name = redacted_fields.value
      }
    }
  }

  depends_on = [aws_cloudwatch_log_resource_policy.waf_cognito]
}

# A rate rule that is blocking means someone is hammering the site or sign-in, or a
# limit is too low for real use; either way a person should look.
resource "aws_cloudwatch_metric_alarm" "waf_cognito_rate_limited" {
  alarm_name        = "${local.waf_name}-waf-sign-in-rate-limited"
  alarm_description = "The sign-in rate limit blocked 100 or more requests in five minutes; the Cognito web ACL's log says from where"
  namespace         = "AWS/WAFV2"
  metric_name       = "BlockedRequests"
  dimensions = {
    WebACL = "${local.waf_name}-cognito"
    Rule   = "${local.waf_name}-cognito-rate-sign-in"
    Region = var.aws_region
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 100
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.api_alerts.arn]
  ok_actions          = [aws_sns_topic.api_alerts.arn]
}

# CloudFront's web ACL reports its metrics only in us-east-1, and an alarm can notify
# only a topic in its own region, so these exist only where the alerts topic is there too.
resource "aws_cloudwatch_metric_alarm" "waf_cloudfront_rate_limited" {
  for_each = var.aws_region == "us-east-1" ? local.waf_cloudfront_rate_rules : {}

  alarm_name        = "${local.waf_name}-waf-${each.key}-rate-limited"
  alarm_description = "The rate limit on ${each.value.path} blocked 100 or more requests in five minutes; the CloudFront web ACL's log says from where"
  namespace         = "AWS/WAFV2"
  metric_name       = "BlockedRequests"
  dimensions = {
    WebACL = "${local.waf_name}-cloudfront"
    Rule   = "${local.waf_name}-cloudfront-rate-${each.key}"
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 100
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.api_alerts.arn]
  ok_actions          = [aws_sns_topic.api_alerts.arn]
}
