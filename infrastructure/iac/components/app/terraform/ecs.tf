
# ECS Cluster
resource "aws_ecs_cluster" "app_cluster" {
  name = "${var.environment_name}-${local.application_name}-ecs-cluster"
}

# IAM Role for ECS
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
        containerPort = 80
        hostPort      = 80
        protocol      = "tcp"
      }
    ]
    environment = [
      { name = "DB_HOST", value = aws_rds_cluster.rds_aurora_cluster.endpoint }
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
  }])
}

# Application Load Balancer (ALB)
resource "aws_lb" "api_alb" {
  name               = "${var.environment_name}-${local.application_name}-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web_sg.id]
  subnets            = aws_subnet.web_subnets[*].id
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
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.vpc.id
  target_type = "ip"

  health_check {
    healthy_threshold   = 3  # Mark healthy after 3 successful checks
    interval            = 30 # Check every 30 seconds
    protocol            = "HTTP"
    matcher             = "200"        # Look for HTTP 200 responses
    timeout             = 3            # Timeout after 3 seconds
    path                = "/v1/status" # Health check endpoint
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
    subnets         = aws_subnet.web_subnets[*].id   # Deploy tasks in public subnets
    security_groups = [aws_security_group.web_sg.id] # Attach security group
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_target_group.arn # Forward traffic to the target group
    container_name   = "${local.application_name}-api"
    container_port   = 80
  }

  desired_count = 1 # Number of tasks to run
}