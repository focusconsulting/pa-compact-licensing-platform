# ECS Cluster
resource "aws_ecs_cluster" "app_cluster" {
  name = "${var.environment_name}-${local.application_name}-ecs-cluster"
}

# CloudWatch Log Group for API container logs
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/ecs/${local.application_name}/${var.environment_name}/api"
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

# Allow the execution role to read DB credentials from Secrets Manager
resource "aws_iam_policy" "ecs_secrets_policy" {
  name        = "${var.environment_name}-ecs-secrets-policy"
  description = "Allow ECS Task to read DB secrets"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_secrets_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_secrets_policy.arn
}


# ECS Task Definition for the API
resource "aws_ecs_task_definition" "api_task" {
  family                   = "${var.environment_name}-${local.application_name}-api-task" # Task family name
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn                     # Use the execution role
  requires_compatibilities = ["FARGATE"]                                                  # Use Fargate for serverless compute
  network_mode             = "awsvpc"                                                     # Assign dedicated network interfaces
  cpu                      = "256"                                                        # CPU allocation
  memory                   = "512"                                                        # Memory allocation

  container_definitions = jsonencode([{
    name      = "${local.application_name}-api"                                       # Container name
    image     = "${var.repo_name}:latest" # Replace with the container image URL
    essential = true
    portMappings = [
      {
        containerPort = 8000
        hostPort      = 8000
        protocol      = "tcp"
      }
    ]
    environment = [
      { name = "DB_HOST",     value = aws_rds_cluster.rds_aurora_cluster.endpoint },
      { name = "DB_PORT",     value = tostring(local.db_port) },
      { name = "DB_NAME",     value = local.db_name },
      { name = "REDIS_URL",   value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379" },
      { name = "ENVIRONMENT", value = upper(var.environment_name) },
      { name = "LOG_LEVEL",   value = "INFO" },
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
  }])
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
    matcher             = "200"        # Look for HTTP 200 responses
    timeout             = 3            # Timeout after 3 seconds
    path                = "/api/health/ready" # Health check endpoint
    unhealthy_threshold = 2            # Mark unhealthy after 2 failed checks
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

  desired_count = 1 # Number of tasks to run

  lifecycle {
    # CI/CD deploys new task definition revisions (new image tags) independently of terraform.
    # Without this, every `terraform apply` would revert the service to the revision terraform
    # last created, undoing CI deployments. Terraform still manages the task definition config
    # (env vars, health check, etc.) — it just doesn't pin the service to a specific revision.
    ignore_changes = [task_definition]
  }
}