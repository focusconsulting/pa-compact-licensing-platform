# The Worker and scheduled jobs (backlog D8): the API's image with another command.
# The Worker delivers events and sends email; each job is a one-off task EventBridge
# Scheduler starts (scheduler.tf).

locals {
  worker_container_name = "${local.application_name}-worker"
  jobs_container_name   = "${local.application_name}-jobs"

  worker_environment = [
    { name = "DB_HOST", value = aws_rds_cluster.rds_aurora_cluster.endpoint },
    { name = "DB_PORT", value = tostring(local.db_port) },
    { name = "DB_NAME", value = local.db_name },
    { name = "ENVIRONMENT", value = upper(var.environment_name) },
    { name = "LOG_LEVEL", value = var.log_level },
    { name = "SMTP_HOST", value = "email-smtp.${var.aws_region}.amazonaws.com" },
    { name = "SMTP_PORT", value = "587" },
    { name = "SMTP_STARTTLS", value = "true" },
    { name = "EMAIL_FROM_ADDRESS", value = "no-reply@${local.email_domain}" },
    { name = "CLIENT_BASE_URL", value = "https://${var.dns_name}" },
    { name = "COMMISSION_OPS_EMAIL", value = var.commission_ops_email },
  ]

  worker_secrets = [
    { name = "DB_USER", valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:username::" },
    { name = "DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:password::" },
    { name = "SMTP_USERNAME", valueFrom = "${aws_secretsmanager_secret.ses_smtp.arn}:username::" },
    { name = "SMTP_PASSWORD", valueFrom = "${aws_secretsmanager_secret.ses_smtp.arn}:password::" },
  ]
}

resource "aws_cloudwatch_log_group" "worker_logs" {
  name              = "/ecs/${local.application_name}/${var.environment_name}/worker"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "jobs_logs" {
  name              = "/ecs/${local.application_name}/${var.environment_name}/jobs"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "worker_task" {
  family                   = "${var.environment_name}-${local.application_name}-worker-task"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name        = local.worker_container_name
      image       = "${var.repo_name}:${var.image_tag}"
      essential   = true
      command     = ["python", "-m", "licensing_api.worker"]
      environment = local.worker_environment
      secrets     = local.worker_secrets
      # ECS sends SIGTERM, then SIGKILL after this; the Worker finishes the delivery in hand first.
      stopTimeout = 60
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
  ])
}

resource "aws_ecs_task_definition" "jobs_task" {
  family                   = "${var.environment_name}-${local.application_name}-jobs-task"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name      = local.jobs_container_name
      image     = "${var.repo_name}:${var.image_tag}"
      essential = true
      # Each schedule overrides the command with `run <job>`; on its own this lists the jobs.
      command     = ["python", "-m", "licensing_api.jobs", "--help"]
      environment = local.worker_environment
      secrets     = local.worker_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.jobs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
  ])
}

resource "aws_ecs_service" "worker_service" {
  name            = "${var.environment_name}-${local.application_name}-worker-service"
  cluster         = aws_ecs_cluster.app_cluster.id
  task_definition = aws_ecs_task_definition.worker_task.arn
  launch_type     = "FARGATE"
  # Two Workers are safe (SKIP LOCKED); one carries the pilot's volume with room to spare.
  desired_count = 1

  network_configuration {
    subnets          = data.terraform_remote_state.network.outputs.private_subnet_ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }
}
