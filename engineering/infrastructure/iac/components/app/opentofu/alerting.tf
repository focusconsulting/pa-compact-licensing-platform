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

# Slack credentials stored in secrets manager in <env>-slack-tfvar secret.
# Secret contains JSON with keys: slack_team_id, slack_channel_id
data "aws_secretsmanager_secret_version" "slack" {
  secret_id = "${var.environment_name}-slack-tfvar"
}

locals {
  slack = jsondecode(data.aws_secretsmanager_secret_version.slack.secret_string)
}

# IAM role that AWS Chatbot assumes to read CloudWatch data
resource "aws_iam_role" "chatbot" {
  name = "${var.environment_name}-${local.application_name}-chatbot-role"
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
  role       = aws_iam_role.chatbot.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

# Delivers SNS alert messages to the configured Slack channel
resource "aws_chatbot_slack_channel_configuration" "api_alerts" {
  configuration_name = "${var.environment_name}-${local.application_name}-alerts"
  iam_role_arn       = aws_iam_role.chatbot.arn
  slack_team_id      = local.slack["slack_team_id"]
  slack_channel_id   = local.slack["slack_channel_id"]
  sns_topic_arns     = [aws_sns_topic.api_alerts.arn]
}

# ---------------------------------------------------------------------------
# The Worker and scheduled jobs (backlog D8). Each alarm reads the structured
# fields the code logs (outcome, logger, job), not message text.
# ---------------------------------------------------------------------------

locals {
  worker_metrics_namespace = "${local.application_name}/${var.environment_name}/worker"

  # name => log group, filter pattern, and the alarm's description
  worker_log_alarms = {
    EventsDeadLettered = {
      log_group   = aws_cloudwatch_log_group.worker_logs.name
      pattern     = "{ $.outcome = \"dead_lettered\" }"
      description = "An event delivery was dead-lettered after five failed attempts (ADR-0012); replay it once fixed"
    }
    NotificationsFailed = {
      log_group   = aws_cloudwatch_log_group.worker_logs.name
      pattern     = "{ $.logger = \"licensing_api.notifications.sender\" && $.outcome = \"failed\" }"
      description = "An email failed five times and will not be retried (ADR-0014); last_error on the notifications row says why"
    }
    JobsFailed = {
      log_group   = aws_cloudwatch_log_group.jobs_logs.name
      pattern     = "{ $.logger = \"licensing_api.jobs\" && $.outcome = \"failed\" }"
      description = "A scheduled job failed; its job_runs row and log say why"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "worker" {
  for_each = local.worker_log_alarms

  name           = "${var.environment_name}-${local.application_name}-${each.key}"
  log_group_name = each.value.log_group
  pattern        = each.value.pattern

  metric_transformation {
    name      = each.key
    namespace = local.worker_metrics_namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "worker" {
  for_each = local.worker_log_alarms

  alarm_name          = "${var.environment_name}-${local.application_name}-${each.key}"
  alarm_description   = each.value.description
  namespace           = local.worker_metrics_namespace
  metric_name         = aws_cloudwatch_log_metric_filter.worker[each.key].metric_transformation[0].name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.api_alerts.arn]
  ok_actions          = [aws_sns_topic.api_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "worker_not_running" {
  alarm_name          = "${var.environment_name}-${local.application_name}-worker-not-running"
  alarm_description   = "No Worker task has run for two minutes: events are not delivered and no email is sent"
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"
  dimensions          = { ClusterName = aws_ecs_cluster.app_cluster.name, ServiceName = aws_ecs_service.worker_service.name }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  # Container Insights reports nothing for a service with no tasks.
  treat_missing_data = "breaching"
  alarm_actions      = [aws_sns_topic.api_alerts.arn]
  ok_actions         = [aws_sns_topic.api_alerts.arn]
}

resource "aws_cloudwatch_log_metric_filter" "heartbeat" {
  name           = "${var.environment_name}-${local.application_name}-HeartbeatSucceeded"
  log_group_name = aws_cloudwatch_log_group.jobs_logs.name
  pattern        = "{ $.job = \"heartbeat\" && $.outcome = \"succeeded\" }"

  metric_transformation {
    name      = "HeartbeatSucceeded"
    namespace = local.worker_metrics_namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "jobs_not_running" {
  alarm_name          = "${var.environment_name}-${local.application_name}-jobs-not-running"
  alarm_description   = "The hourly heartbeat job has not succeeded for two hours: the scheduler is not starting jobs"
  namespace           = local.worker_metrics_namespace
  metric_name         = aws_cloudwatch_log_metric_filter.heartbeat.metric_transformation[0].name
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 2
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.api_alerts.arn]
  ok_actions          = [aws_sns_topic.api_alerts.arn]
}
