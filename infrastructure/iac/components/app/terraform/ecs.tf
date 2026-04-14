# ECS Cluster
resource "aws_ecs_cluster" "app_cluster" {
  name = "${var.environment_name}-${local.application_name}-ecs-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# CloudWatch Log Group for API container logs
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/ecs/${local.application_name}/${var.environment_name}/api"
  retention_in_days = 30
}

# CloudWatch Log Group for ADOT EMF metrics (explicit retention; avoids auto-created group with no expiry)
resource "aws_cloudwatch_log_group" "api_metrics" {
  name              = "/ecs/${local.application_name}/${var.environment_name}/api/metrics"
  retention_in_days = 30
}

# IAM Role for ECS
# task execution role (image pull + log delivery)
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.environment_name}-${local.application_name}-ecs-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# Attach AWS-managed policy so ECS can pull from ECR and write to CloudWatch Logs
resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow the execution role to read DB credentials from Secrets Manager and ADOT config from SSM
resource "aws_iam_policy" "ecs_secrets_policy" {
  name        = "${var.environment_name}-ecs-secrets-policy"
  description = "Allow ECS Task to read DB secrets and ADOT config"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.db_credentials.arn
      },
      {
        Effect   = "Allow"
        Action   = "ssm:GetParameters"
        Resource = aws_ssm_parameter.adot_config.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_secrets_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_secrets_policy.arn
}

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

# ADOT collector config stored in SSM; loaded at container startup via --config=ssm:<name>
resource "aws_ssm_parameter" "adot_config" {
  name = "/${var.environment_name}/${local.application_name}/adot-config"
  type = "String"
  value = templatefile("${path.module}/adot-config.yaml", {
    environment = var.environment_name
  })
}

# ECS Task Definition for the API
resource "aws_ecs_task_definition" "api_task" {
  family                   = "${var.environment_name}-${local.application_name}-api-task" # Task family name
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn                     # Use the execution role
  task_role_arn            = aws_iam_role.ecs_task_role.arn                               # Used by ADOT for X-Ray/CloudWatch/SSM
  requires_compatibilities = ["FARGATE"]                                                  # Use Fargate for serverless compute
  network_mode             = "awsvpc"                                                     # Assign dedicated network interfaces
  cpu                      = "512"                                                        # Bumped from 256 to accommodate ADOT sidecar
  memory                   = "1024"                                                       # Bumped from 512 to accommodate ADOT sidecar

  container_definitions = jsonencode([
    {
      name      = "${local.application_name}-api"
      image     = "${var.repo_name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "DB_HOST", value = aws_rds_cluster.rds_aurora_cluster.endpoint },
        { name = "DB_PORT", value = tostring(local.db_port) },
        { name = "DB_NAME", value = local.db_name },
        { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379" },
        { name = "ENVIRONMENT", value = upper(var.environment_name) },
        { name = "LOG_LEVEL", value = "INFO" },
        { name = "OTEL_ENABLED", value = "true" },
      ]
      secrets = [
        {
          name      = "DB_USERNAME"
          valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:password::"
        }
      ]
      healthCheck = {
        # Use /live (not /ready) — liveness checks whether the process is alive,
        # not whether dependencies are reachable. Using /ready here causes ECS to
        # kill and restart tasks whenever DB/Redis is slow, creating restart loops
        # and slow deployments. The ALB /ready check gates traffic separately.
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/live')\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      # Wait for ADOT to be accepting connections before the app starts sending spans
      dependsOn = [{ containerName = "adot-collector", condition = "START" }]
    },
    {
      # ADOT sidecar: config injected via AOT_CONFIG_CONTENT env var (ECS fetches SSM value at startup).
      # --config=ssm: scheme is unsupported in v0.43.2; AOT_CONFIG_CONTENT is the documented ECS approach.
      name      = "adot-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:v0.43.2"
      essential = false
      secrets   = [{ name = "AOT_CONFIG_CONTENT", valueFrom = aws_ssm_parameter.adot_config.arn }]
      portMappings = [
        { containerPort = 4317, hostPort = 4317, protocol = "tcp" }, # OTLP gRPC
        { containerPort = 4318, hostPort = 4318, protocol = "tcp" }, # OTLP HTTP
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

# Application Load Balancer (ALB)
resource "aws_lb" "api_alb" {
  name               = "${var.environment_name}-${local.application_name}-api-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = data.terraform_remote_state.network.outputs.private_subnet_ids
}

resource "aws_lb_listener" "api_listener" {
  load_balancer_arn = aws_lb.api_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_target_group.arn
  }
}

resource "aws_lb_target_group" "api_target_group" {
  name        = "${var.environment_name}-${local.application_name}-api-target-group"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id
  target_type = "ip"

  health_check {
    healthy_threshold   = 3  # Mark healthy after 3 successful checks
    interval            = 30 # Check every 30 seconds
    protocol            = "HTTP"
    matcher             = "200"               # Look for HTTP 200 responses
    timeout             = 3                   # Timeout after 3 seconds
    path                = "/api/health/ready" # Health check endpoint
    unhealthy_threshold = 2                   # Mark unhealthy after 2 failed checks
  }
}

# ECS Service for deploying the API
resource "aws_ecs_service" "api_service" {
  name            = "${var.environment_name}-${local.application_name}-api-service" # ECS service name
  cluster         = aws_ecs_cluster.app_cluster.id                                  # Associate with the ECS cluster
  task_definition = aws_ecs_task_definition.api_task.arn                            # Use the task definition
  launch_type     = "FARGATE"                                                       # Use Fargate for serverless compute

  network_configuration {
    subnets          = data.terraform_remote_state.network.outputs.private_subnet_ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_target_group.arn # Forward traffic to the target group
    container_name   = "${local.application_name}-api"
    container_port   = 8000
  }

  desired_count = 1 # Initial count; managed by auto-scaling after first deploy

  lifecycle {
    # CI/CD deploys new task definition revisions (new image tags) independently of terraform.
    # Without this, every `terraform apply` would revert the service to the revision terraform
    # last created, undoing CI deployments. Terraform still manages the task definition config
    # (env vars, health check, etc.) — it just doesn't pin the service to a specific revision.
    #
    # desired_count is ignored so that auto-scaling adjustments are not reverted on next apply.
    ignore_changes = [task_definition, desired_count]
  }
}

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
    scale_in_cooldown  = 300 # wait 5 min before scaling back in
    scale_out_cooldown = 60  # allow rapid scale-out
  }
}
