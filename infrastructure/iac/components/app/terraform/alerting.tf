# SNS topic that aggregates all API operational alerts
resource "aws_sns_topic" "api_alerts" {
  name = "${var.environment_name}-${local.application_name}-api-alerts"
}

# CloudWatch Metric Math alarm: (target 4xx + target 5xx + elb 5xx) / total requests > 1%
# Includes ELB-originated 5xx (502/503/504 when backend is down) in addition to target errors.
# Uses IF() to avoid division-by-zero when RequestCount is 0.
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "${var.environment_name}-${local.application_name}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  threshold           = 1
  alarm_description   = "API error rate (HTTP 4xx+5xx including ALB-originated) exceeded 1% of requests over 5 minutes"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.api_alerts.arn]
  ok_actions          = [aws_sns_topic.api_alerts.arn]

  metric_query {
    id          = "error_rate"
    expression  = "IF(m1 > 0, (m2 + m3 + m4) / m1 * 100, 0)"
    label       = "Error Rate %"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      period      = 60
      stat        = "Sum"
      dimensions  = { LoadBalancer = aws_lb.api_alb.arn_suffix }
    }
  }

  metric_query {
    id = "m2"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_4XX_Count"
      period      = 60
      stat        = "Sum"
      dimensions  = { LoadBalancer = aws_lb.api_alb.arn_suffix }
    }
  }

  metric_query {
    id = "m3"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      period      = 60
      stat        = "Sum"
      dimensions  = { LoadBalancer = aws_lb.api_alb.arn_suffix }
    }
  }

  metric_query {
    id = "m4"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_ELB_5XX_Count"
      period      = 60
      stat        = "Sum"
      dimensions  = { LoadBalancer = aws_lb.api_alb.arn_suffix }
    }
  }
}

# IAM role that AWS Chatbot assumes to read CloudWatch data
resource "aws_iam_role" "chatbot" {
  count = var.slack_team_id != null ? 1 : 0
  name  = "${var.environment_name}-${local.application_name}-chatbot-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "chatbot.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "chatbot_cloudwatch" {
  count      = var.slack_team_id != null ? 1 : 0
  role       = aws_iam_role.chatbot[0].name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

# Delivers SNS alert messages to the configured Slack channel
resource "aws_chatbot_slack_channel_configuration" "api_alerts" {
  count              = var.slack_team_id != null ? 1 : 0
  configuration_name = "${var.environment_name}-${local.application_name}-alerts"
  iam_role_arn       = aws_iam_role.chatbot[0].arn
  slack_team_id      = var.slack_team_id
  slack_channel_id   = var.slack_channel_id
  sns_topic_arns     = [aws_sns_topic.api_alerts.arn]
}
