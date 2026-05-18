# Metrics and Alerting Implementation Plan

## Overview

Add observability and operational resilience to the platform across three areas:
ALB error-rate alerting via Slack, OpenTelemetry instrumentation for endpoint
metrics and distributed traces in the FastAPI backend, and ECS auto-scaling with
CloudWatch Container Insights.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-p42
- ADRs: N/A
- **Area**: cross-cutting (IaC + API)

## Current State Analysis

- ECS Fargate service runs a fixed `desired_count=1` (256 CPU / 512 MB), no
  auto-scaling, no Container Insights.
- ALB publishes metrics to CloudWatch automatically but no alarms exist.
- Only CloudWatch resource is the log group `/ecs/licensing/{env}/api`.
- FastAPI app has hand-rolled JSON logging, no middleware, no OTel or Prometheus.
- No ECS task role (only an execution role); task role is needed for ADOT.

### Key Discoveries

- `infrastructure/iac/components/app/terraform/ecs.tf:2` — cluster has no
  `setting` block; Container Insights is off.
- `infrastructure/iac/components/app/terraform/ecs.tf:160` — `desired_count = 1`
  hard-coded; no `aws_appautoscaling_*` resources anywhere.
- `infrastructure/iac/components/app/terraform/ecs.tf:55-61` — task definition
  has only an `execution_role_arn`, no `task_role_arn`.
- `api/licensing_api/__main__.py:91-98` — FastAPI app instantiated directly, no
  OTel middleware.
- `api/licensing_api/config.py:6-23` — pydantic-settings `Settings` class;
  add `otel_enabled: bool` here to gate OTel in non-ECS environments.

## Desired End State

- A CloudWatch alarm fires and posts to Slack when ALB (4xx+5xx)/total > 1%.
- ECS service auto-scales between 1 and 2 tasks (dev) based on CPU utilization,
  targeting 70%.
- Container Insights enabled on the cluster for enhanced per-task metrics.
- FastAPI sends traces to X-Ray and metrics to CloudWatch EMF via an ADOT
  sidecar in the same ECS task.

### Verification

- Trigger a burst of 4xx errors with curl; Slack alert arrives within ~5 minutes.
- Manually set CPU to spike (or via load test); ECS desired count increases to 2.
- X-Ray console shows traces with per-endpoint latency breakdown.
- CloudWatch Metrics → `LicensingAPI` namespace shows request count and latency.

## What We're NOT Doing

- HTTPS on the ALB listener (variable exists but is not wired; out of scope).
- Third-party observability backends (Datadog, Grafana Cloud).
- Custom CloudWatch dashboards (can be added once metrics are flowing).
- Alerting on memory utilization (Container Insights provides this; can add later).
- Redis OTel instrumentation (can be added in a follow-up; not blocking).

---

## Phase 1: ALB Error-Rate Alerting → Slack

### Overview

Create an SNS topic, a CloudWatch Metric Math alarm on the ALB, and wire it to
a Slack channel via AWS Chatbot. AWS Chatbot requires a one-time manual OAuth
authorization in the AWS Console before Terraform can manage the channel
configuration.

### Manual Prerequisites (before applying Terraform)

> **Note**: AWS Chatbot was rebranded to **Amazon Q Developer in Chat Applications**.
> The AWS Console redirects to Amazon Q Developer; the Terraform resource
> (`aws_chatbot_slack_channel_configuration`) is unchanged.

1. Open the Amazon Q Developer console → **Chat applications** (left sidebar).
2. Click **Configure Slack client** → complete the OAuth flow to authorize the
   **Amazon Q** app into your Slack workspace.
3. Note the **Workspace ID** shown after authorization (format: `TXXXXXXXXX`).
   This is your `slack_team_id` tfvar value.
4. In Slack, invite the bot to your target channel: `/invite @amazon-q`
5. Note the **Channel ID** (right-click channel → **Copy link**; the ID is the
   last path segment, format: `CXXXXXXXXX`). This is your `slack_channel_id`.

### Changes Required

#### 1. New file: `infrastructure/iac/components/app/terraform/alerting.tf`

```hcl
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
  evaluation_periods  = 5       # must breach 5 of last 5 one-minute periods
  threshold           = 1       # 1%
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
  slack_team_id = var.slack_team_id
  slack_channel_id   = var.slack_channel_id
  sns_topic_arns     = [aws_sns_topic.api_alerts.arn]
}
```

#### 2. Add to `infrastructure/iac/components/app/terraform/variables.tf`

```hcl
variable "slack_team_id" {
  type        = string
  description = "Slack workspace ID for AWS Chatbot (authorize workspace in Chatbot console first; format: TXXXXXXXXX)"
  default     = null
}

variable "slack_channel_id" {
  type        = string
  description = "Slack channel ID to receive API alerts (format: CXXXXXXXXX)"
  default     = null
}
```

#### 3. Add to `infrastructure/iac/environments/dev/us-east-1/app.tfvars`

```hcl
slack_team_id = "TXXXXXXXXX"   # replace with actual workspace ID
slack_channel_id   = "CXXXXXXXXX"   # replace with actual channel ID
```

### Success Criteria

#### Automated Verification

- [ ] Terraform validates: `cd infrastructure/iac/components/app/terraform && terraform validate`
- [ ] Terraform plan shows only additive changes (new SNS topic, alarm, Chatbot config)
- [ ] Terraform apply succeeds

#### Manual Verification

- [ ] CloudWatch alarm `{env}-licensing-api-error-rate` exists and is in OK state
- [ ] Trigger test: sustain 4xx errors across 6+ consecutive minutes so all 5 evaluation periods breach the threshold (a single burst only hits 1 period and won't fire):

  Install with `brew install hey watch`. Monitor alarm state while the test runs:

  ```bash
  # 1 worker × 5 q/s for ~7 min; -q is per-worker so use -c 1 to get 5 req/sec total
  # Requests hit a non-existent path → 100% 4xx rate per period (CloudFront may return 200
  # to the client but the ALB correctly records these as HTTPCode_Target_4XX_Count)
  hey -n 2100 -c 1 -q 5 https://<cloudfront-domain>/api/this-path-does-not-exist

  watch -n 30 'aws cloudwatch describe-alarms --alarm-names "dev-licensing-error-rate" --query "MetricAlarms[0].{State:StateValue,Reason:StateReason}" --output json'
  ```
- [ ] Alarm flips to ALARM state and Slack notification arrives (~minute 5-6 of the test)
- [ ] OK notification arrives in Slack once error rate drops below 1%

**Pause here for manual confirmation before proceeding to Phase 2.**

---

## Phase 2: Container Insights + ECS Auto-scaling

### Overview

Enable CloudWatch Container Insights on the ECS cluster (enhanced per-task
metrics) and attach a target-tracking auto-scaling policy so the service scales
between 1 and `ecs_max_capacity` tasks based on average CPU utilization,
targeting 70%. Scale-in cooldown is 300 s; AWS manages the inverse threshold
automatically under target tracking.

### Changes Required

#### 1. Modify `infrastructure/iac/components/app/terraform/ecs.tf`

**Enable Container Insights on the cluster** (`ecs.tf:2-4`):

```hcl
resource "aws_ecs_cluster" "app_cluster" {
  name = "${var.environment_name}-${local.application_name}-ecs-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

**Prevent Terraform from fighting the auto-scaler** — add to `aws_ecs_service.api_service`
(`ecs.tf:142-161`):

```hcl
  lifecycle {
    ignore_changes = [desired_count]
  }
```

This prevents `terraform apply` from resetting the count after the auto-scaler
adjusts it.

**Add auto-scaling resources** (append to end of `ecs.tf`):

```hcl
# Registers the ECS service as a scalable target
resource "aws_appautoscaling_target" "api_service" {
  max_capacity       = var.ecs_max_capacity
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.app_cluster.name}/${aws_ecs_service.api_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Target-tracking policy: scale out when average CPU > 70%, scale in automatically
resource "aws_appautoscaling_policy" "api_cpu_scaling" {
  name               = "${var.environment_name}-${local.application_name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api_service.resource_id
  scalable_dimension = aws_appautoscaling_target.api_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300  # wait 5 min before scaling back in
    scale_out_cooldown = 60   # allow rapid scale-out
  }
}
```

#### 2. Add to `infrastructure/iac/components/app/terraform/variables.tf`

```hcl
variable "ecs_max_capacity" {
  type        = number
  description = "Maximum number of ECS Fargate tasks to scale to"
  default     = 2
}
```

No changes needed in `app.tfvars` — the variable defaults to `2` which is the
dev target. Override only for environments that need a different max.

### Success Criteria

#### Automated Verification

- [ ] Terraform validates and plan shows in-place update to cluster + two new scaling resources
- [ ] Terraform apply succeeds
- [ ] `aws ecs describe-clusters --clusters {env}-licensing-ecs-cluster --include SETTINGS` shows `containerInsights: enabled`
- [ ] `aws application-autoscaling describe-scaling-policies --service-namespace ecs` lists the new policy

#### Manual Verification

- [ ] Container Insights metrics visible in CloudWatch → Insights → Container Insights → ECS (per cluster/service/task views)
- [ ] Load test to verify auto-scaling fires:
  1. Temporarily lower the scaling target to 20% (idle CPU is ~7%, so a moderate load will cross it):
     ```bash
     aws application-autoscaling put-scaling-policy \
       --service-namespace ecs \
       --resource-id "service/{env}-licensing-ecs-cluster/{env}-licensing-api-service" \
       --scalable-dimension ecs:service:DesiredCount \
       --policy-name {env}-licensing-cpu-scaling \
       --policy-type TargetTrackingScaling \
       --target-tracking-scaling-policy-configuration '{
         "TargetValue": 20.0,
         "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"},
         "ScaleInCooldown": 300,
         "ScaleOutCooldown": 60
       }'
     ```
  2. Run load test — use `/live` not `/ready` (`/ready` hits Postgres+Redis, is I/O bound and generates little CPU):
     ```bash
     # 50 workers × 6 q/s = 300 req/s for ~5 min; Cache-Control bypasses CloudFront edge cache
     hey -n 90000 -c 50 -q 6 \
       -H "Cache-Control: no-cache" \
       https://<cloudfront-domain>/api/health/live
     ```
  3. Watch desired count flip to 2 (~3-4 min in due to 3-period alarm evaluation window + ~2 min CloudWatch lag):
     ```bash
     watch -n 10 'aws ecs describe-services --cluster {env}-licensing-ecs-cluster --services {env}-licensing-api-service --query "services[0].{desired:desiredCount,running:runningCount}" --output json'
     ```
  4. After verification, restore target to 70%:
     ```bash
     aws application-autoscaling put-scaling-policy \
       --service-namespace ecs \
       --resource-id "service/{env}-licensing-ecs-cluster/{env}-licensing-api-service" \
       --scalable-dimension ecs:service:DesiredCount \
       --policy-name {env}-licensing-cpu-scaling \
       --policy-type TargetTrackingScaling \
       --target-tracking-scaling-policy-configuration '{
         "TargetValue": 70.0,
         "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"},
         "ScaleInCooldown": 300,
         "ScaleOutCooldown": 60
       }'
     ```

**Pause here for manual confirmation before proceeding to Phase 3.**

---

## Phase 3: OpenTelemetry — ADOT Sidecar + FastAPI Instrumentation

### Overview

Run the AWS Distro for OpenTelemetry (ADOT) collector as a sidecar in the ECS
task. The FastAPI app sends OTLP data over localhost gRPC (port 4317) to the
sidecar, which fans out traces to X-Ray and metrics to CloudWatch EMF. A new
ECS task role grants the sidecar the required X-Ray and CloudWatch permissions.
The ADOT config is stored in SSM Parameter Store and loaded at container startup.

The ECS task CPU/memory is bumped from 256/512 to 512/1024 to accommodate the
sidecar.

### Changes Required

#### 1. Add OTel setting to `api/licensing_api/config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...
    otel_enabled: bool = False
    otel_collector_endpoint: str = 'http://localhost:4317'
```

#### 2. Add OTel dependencies to `api/pyproject.toml`

Add to the `dependencies` list:

```toml
"opentelemetry-api>=1.28.0",
"opentelemetry-sdk>=1.28.0",
"opentelemetry-instrumentation-fastapi>=0.49b0",
"opentelemetry-instrumentation-asyncpg>=0.49b0",
"opentelemetry-exporter-otlp-proto-grpc>=1.28.0",
```

Run `uv lock` after editing to regenerate the lockfile.

#### 3. Add OTel initialization to `api/licensing_api/__main__.py`

Add a `_configure_otel()` function after the existing `_mask_sensitive()`.
OTel imports are lazy (inside the function) so local dev and tests don't pay the
import cost when `otel_enabled=False`:

```python
def _configure_otel() -> None:
    """Configure OpenTelemetry SDK to export traces and metrics to the ADOT sidecar."""
    from opentelemetry import metrics as otel_metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({
        'service.name': 'licensing-api',
        'deployment.environment': settings.environment.lower(),
    })

    # Traces → ADOT → X-Ray
    trace_exporter = OTLPSpanExporter(
        endpoint=settings.otel_collector_endpoint,
        insecure=True,
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics → ADOT → CloudWatch EMF (namespace: LicensingAPI)
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.otel_collector_endpoint,
        insecure=True,
    )
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60_000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    otel_metrics.set_meter_provider(meter_provider)

    # Auto-instrument asyncpg (DB query tracing)
    AsyncPGInstrumentor().instrument()

    # Auto-instrument FastAPI (called after app creation, see below)
    logger.info('OpenTelemetry configured', extra={'endpoint': settings.otel_collector_endpoint})

    return FastAPIInstrumentor
```

Call `_configure_otel()` conditionally just before the `app = FastAPI(...)` block,
then instrument the app after router inclusion:

```python
_fastapi_instrumentor = _configure_otel() if settings.otel_enabled else None

app = FastAPI(...)
app.include_router(router)

if _fastapi_instrumentor is not None:
    _fastapi_instrumentor.instrument_app(app)
```

#### 4. New file: `infrastructure/iac/components/app/terraform/adot-config.yaml`

```yaml
extensions:
  health_check:

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch/traces:
    timeout: 1s
    send_batch_size: 50
  batch/metrics:
    timeout: 60s

exporters:
  awsxray: {}
  awsemf:
    namespace: LicensingAPI
    log_group_name: /ecs/licensing/${environment}/api/metrics

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch/traces]
      exporters: [awsxray]
    metrics:
      receivers: [otlp]
      processors: [batch/metrics]
      exporters: [awsemf]
  extensions: [health_check]
```

#### 5. Modify `infrastructure/iac/components/app/terraform/ecs.tf`

**Add ECS task role** (insert after the existing execution role block, ~`ecs.tf:51`):

```hcl
# Task role: assumed by the running container process (needed for ADOT to call X-Ray, CloudWatch, SSM)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.environment_name}-${local.application_name}-ecs-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_otel" {
  name = "${var.environment_name}-${local.application_name}-otel-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "XRay"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries",
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
        ]
        Resource = "*"
      },
      {
        Sid      = "AdotConfig"
        Effect   = "Allow"
        Action   = "ssm:GetParameters"
        Resource = aws_ssm_parameter.adot_config.arn
      },
    ]
  })
}

# Terraform-managed log group for ADOT EMF metrics (with explicit retention)
resource "aws_cloudwatch_log_group" "api_metrics" {
  name              = "/ecs/${local.application_name}/${var.environment_name}/api/metrics"
  retention_in_days = 30
}

resource "aws_ssm_parameter" "adot_config" {
  name  = "/${var.environment_name}/${local.application_name}/adot-config"
  type  = "String"
  value = templatefile("${path.module}/adot-config.yaml", {
    environment = var.environment_name
  })
}
```

**Update the task definition** (`ecs.tf:55-101`) — wire in the task role, bump
CPU/memory, and add the ADOT sidecar container:

```hcl
resource "aws_ecs_task_definition" "api_task" {
  family                   = "${var.environment_name}-${local.application_name}-api-task"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn   # NEW
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"    # bumped from 256 (ADOT sidecar needs headroom)
  memory                   = "1024"   # bumped from 512

  container_definitions = jsonencode([
    {
      # --- API container (unchanged except added OTEL_ENABLED env var) ---
      name      = "${local.application_name}-api"
      image     = "${var.repo_name}:latest"
      essential = true
      portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "DB_HOST",      value = aws_rds_cluster.rds_aurora_cluster.endpoint },
        { name = "DB_PORT",      value = tostring(local.db_port) },
        { name = "DB_NAME",      value = local.db_name },
        { name = "REDIS_URL",    value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379" },
        { name = "ENVIRONMENT",  value = upper(var.environment_name) },
        { name = "LOG_LEVEL",    value = "INFO" },
        { name = "OTEL_ENABLED", value = "true" },   # NEW
      ]
      secrets = [
        { name = "DB_USERNAME", valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:password::" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      dependsOn = [{ containerName = "adot-collector", condition = "START" }]  # NEW
    },
    {
      # --- ADOT sidecar (reads config from SSM, exports to X-Ray and CloudWatch EMF) ---
      name      = "adot-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:v0.43.2"
      essential = false
      command   = ["--config=ssm:${aws_ssm_parameter.adot_config.name}"]
      portMappings = [
        { containerPort = 4317, hostPort = 4317, protocol = "tcp" },  # OTLP gRPC
        { containerPort = 4318, hostPort = 4318, protocol = "tcp" },  # OTLP HTTP
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "adot"
        }
      }
    },
  ])
}
```

### Success Criteria

#### Automated Verification

- [ ] `cd api && uv run pyright` passes (no type errors from new OTel imports)
- [ ] `cd api && uv run ruff check .` passes
- [ ] `cd api && uv run pytest` passes (OTel is gated on `otel_enabled=False` by default, so tests are unaffected)
- [ ] Terraform validates and plan shows in-place update to task definition
- [ ] Terraform apply succeeds

#### Manual Verification

- [ ] ECS task starts successfully with both containers (`api` + `adot-collector` both healthy)
- [ ] ADOT container logs show `Everything is ready` without errors
- [ ] X-Ray console → Traces shows requests flowing through (make a few `/health/live` calls)
- [ ] CloudWatch Metrics → Custom Namespaces → `LicensingAPI` shows `http.server.duration` and `http.server.request.count`
- [ ] X-Ray trace map shows the `licensing-api` service node with latency distribution

---

## Testing Strategy

### Unit Tests

OTel initialization is gated on `settings.otel_enabled = False` in all existing
tests. No test changes required — the `_configure_otel()` function is not called
unless the env var is set.

To explicitly test OTel setup in isolation, set `OTEL_ENABLED=true` in a test
fixture and assert that `trace.get_tracer_provider()` is a `TracerProvider`
(not the no-op default).

### Integration Tests (ECS)

- Send requests through CloudFront → ALB → ECS after deploy.
- Verify traces appear in X-Ray within ~30 seconds.
- Verify CloudWatch EMF metrics appear within ~2 minutes (60 s export interval).

### Load Test (Auto-scaling)

```bash
# requires: brew install hey
hey -n 50000 -c 100 -q 500 https://<cloudfront-domain>/api/health/live
```

Watch ECS console for desired count changing from 1 → 2.

## Performance Considerations

- ADOT sidecar: ~100 MB RAM, ~50 m CPU at idle. Bumping task to 512 CPU / 1024
  MB gives each container sufficient headroom.
- OTel `BatchSpanProcessor` and `PeriodicExportingMetricReader` are async and
  non-blocking; they will not add latency to request handling.
- ADOT `batch/traces` processor flushes every second or 50 spans — fine for
  low-throughput dev.

## References

- ADOT ECS Fargate guide: https://aws-otel.github.io/docs/setup/ecs
- AWS Chatbot Terraform resource: `aws_chatbot_slack_channel_configuration`
- OTel FastAPI instrumentation: `opentelemetry-instrumentation-fastapi`
- `infrastructure/iac/components/app/terraform/ecs.tf` — ECS task definition
- `api/licensing_api/__main__.py` — FastAPI app entry point
- `api/licensing_api/config.py` — Settings (pydantic-settings)
